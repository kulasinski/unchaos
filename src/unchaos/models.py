import json
import signal
import sys
from typing import Annotated, ClassVar, List, Optional, Sequence, Set, Union
from datetime import datetime

import click
from colorama import Fore, Style
from prompt_toolkit import prompt
import networkx as nx
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from .types import NoteMetadata, QueueTask
from .db import EdgeDB, NodeDB, NoteEntityDB, NoteKeywordDB, NoteNodeDB, NoteTagDB, NoteURLDB, get_session, NoteDB, SnippetDB, NoteTagDB, SnippetTagDB, NoteKeywordDB, SnippetKeywordDB, QueueDB, get_or_create_token
from .utils import clear_terminal, clear_terminal_line, containsTagsOnly, extract_tags_and_keywords, fwarn, now_formatted, fsys, split_location_to_nodes

class Snippet(BaseModel):
    id: int = None
    content: str
    created_at: datetime = None
    updated_at: datetime = None
    tags: Set[str] = set()
    keywords: Set[str] = set()

    def persist(self, note_id: int, db: Session = None) -> None:
        """Creates a new snippet in DB."""
        db = db or get_session()
        if not self.id:
            new_snippet = SnippetDB(note_id=note_id, content=self.content)
            db.add(new_snippet)
            db.commit()
            db.refresh(new_snippet)

            # update the snippet with the new ID and timestamps
            self.id = new_snippet.id
            self.created_at = new_snippet.created_at
            self.updated_at = new_snippet.updated_at
        else:
            existing_snippet = db.query(SnippetDB).filter_by(id=self.id).first()
            if not existing_snippet:
                raise ValueError(f"Snippet with ID={self.id} not found.")
            existing_snippet.content = self.content
            existing_snippet.updated_at = datetime.now()
            db.commit()
            db.refresh(existing_snippet)
            self.updated_at = existing_snippet.updated_at

        # Insert tags
        for tag in self.tags:
            token = get_or_create_token(tag, db=db)
            db.add(SnippetTagDB(snippet_id=new_snippet.id, token_id=token.id))

        # Insert keywords
        for keyword in self.keywords:
            token = get_or_create_token(keyword, db=db)
            db.add(SnippetKeywordDB(snippet_id=new_snippet.id, token_id=token.id))

        db.commit()

    def display(self, ord: int=None):
        snippet_content = self.content
        # Highlight tags and keywords
        for tag in self.tags:
            snippet_content = snippet_content.replace(f"#{tag}", f"{Fore.GREEN}#{tag}{Style.RESET_ALL}")
        for keyword in self.keywords:
            snippet_content = snippet_content.replace(f"@{keyword}", f"{Fore.MAGENTA}@{keyword}{Style.RESET_ALL}")
        # Display snippet
        print(f"{Fore.CYAN}[{ord}]{Style.RESET_ALL} {snippet_content}")

    @classmethod
    def fromDBobject(cls, snippet: SnippetDB) -> 'Snippet':
        """Create a snippet from a DB object."""
        return cls(
            id=snippet.id,
            content=snippet.content,
            created_at=snippet.created_at,
            updated_at=snippet.updated_at,
            tags={tag.tag.value for tag in snippet.tags},  # Extract the value from TokenDB
            keywords={keyword.keyword.value for keyword in snippet.keywords},  # Extract the value from TokenDB
        )
    
    @staticmethod
    def get(id: int, db: Session = None) -> 'Snippet':
        """Retrieves a snippet by ID."""
        db = db or get_session()
        snippet = db.query(SnippetDB).filter_by(id=id).first()
        if not snippet:
            raise ValueError(f"Snippet with ID={id} not found.")
        return Snippet.fromDBobject(snippet)


class Note(BaseModel):
    id: int = None
    title: str|None
    created_at: datetime = None
    updated_at: datetime = None
    custom_fields: dict|None = {}
    embedding: Sequence[float]|None = None
    active: bool = True
    snippets: List[Snippet] = []
    entities: Set[str] = set()
    urls: Set[str] = set()
    tags: Set[str] = set()     # own not snippets'
    keywords: Set[str] = set() # own not snippets'

    __token_fields = ["tags", "keywords", "entities", "urls"]

    # --- Token handling ---

    @property
    def tagsAll(self) -> List[str]:
        """ Return all tags from snippets and note """
        tags = self.tags.copy()
        for snippet in self.snippets:
            tags.update(snippet.tags)
        return list(tags)
    
    @property
    def keywordsAll(self) -> List[str]:
        """ Return all keywords from snippets and note """
        keywords = self.keywords.copy()
        for snippet in self.snippets:
            keywords.update(snippet.keywords)
        return list(keywords)
    
    def display(self, width: int = 80, footer: bool = True):
        """Displays the note in a formatted way."""
        print("\n"+"=" * width)
        print(f"{Fore.CYAN}Note title:{Style.RESET_ALL} {self.title}")
        print(f"{Fore.CYAN}Created at: {self.created_at.isoformat()}{Style.RESET_ALL}")
        print("-" * width)

        for i,snippet in enumerate(self.snippets):
            snippet.display(ord=i+1)
            
        if footer:
            print("-" * width)
            print(f"{Fore.CYAN}Keywords: {Fore.MAGENTA}{', '.join(['@'+kw for kw in self.keywordsAll])}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Tags: {Fore.GREEN}{', '.join(['#'+tag for tag in self.tagsAll])}{Style.RESET_ALL}")
            print("=" * width + "\n")

    # --- Input ---

    def input(self, db: Session = None):
        """Interactive input for note creation or update."""
        db = db or get_session()

        def handle_exit(sig, frame):
            clear_terminal_line()
            print(f"\n{Fore.CYAN}Finishing and saving note...{Style.RESET_ALL}")
            self.to_queue()
            print(f"{Fore.CYAN}✅ Note{Style.RESET_ALL} {self.id} {Fore.CYAN}added to the queue.{Style.RESET_ALL}")
            sys.exit(0)

        signal.signal(signal.SIGQUIT, handle_exit)

        # Loop to accept multiple snippets from the user
        marked_for_reinput = False # Flag to reinput the current snippet
        while True:
            try:
                content = click.prompt(f"{Fore.CYAN}>{Style.RESET_ALL} ", prompt_suffix="")
            except click.Abort:
                handle_exit(None, None)
            if not content.strip():
                continue

            # --- Check for special commands ---
            if content in ["/exit", "/quit", "/q"]:
                # --- Exit ---
                handle_exit(None, None)
            if content.startswith("/delete ") or content.startswith("/d ") or content.startswith("/del "):
                # --- Delete snippet ---
                snippet_ord = int(content.split()[1])
                self.handle_snippet_delete(snippet_ord=snippet_ord, db=db)
                # Reinput the current snippet and exit the current loop
                marked_for_reinput = True
                break
            if content.startswith("/archive"):
                self.archive(db=db)
                break
            if content.startswith("/edit") or content.startswith("/e"):
                # --- Edit snippet ---
                snippet_ord = int(content.split()[1])
                snippet = self.snippets[snippet_ord-1]
                # Use `prompt` with a default value
                snippet.content = prompt(f"[{snippet_ord}] (edit): ", default=snippet.content)
                snippet.persist(note_id=self.id, db=db)
                marked_for_reinput = True
                break
            if content == "/title":
                # --- Edit title ---
                self.title = prompt("Title (edit): ", default=self.title)
                self.persist(db=db)
                marked_for_reinput = True
                break
            self.add_snippet(content, display=True, db=db)

        if marked_for_reinput:
            clear_terminal()
            self.display(footer=False)
            self.input()

    # --- CRUD Operations ---

    def persist(self, db: Session = None) -> None:
        """Creates or updates a note in DB."""
        db = db or get_session()

        if not self.title:
            self.title = f"untitled ({now_formatted()})"

        if not self.id: # Create new note
            note = NoteDB(
                title=self.title,
                custom_fields=json.dumps(self.custom_fields),
            )
            db.add(note)
            db.commit()
            db.refresh(note)
            self.id = note.id
            self.created_at = note.created_at
            self.updated_at = note.updated_at
            return
        
        # Update existing note
        note = db.query(NoteDB).filter_by(id=self.id).first()
        if not note:
            raise ValueError(f"Note with ID={self.id} not found.")
        note.title = self.title
        note.custom_fields = json.dumps(self.custom_fields)
        note.embedding = self.embedding
        note.active = self.active
        note.updated_at = datetime.now()

        note.tags = [
            NoteTagDB(tag=get_or_create_token(tag, db=db), note_id=note.id)
            for tag in self.tags
        ]
        note.keywords = [
            NoteKeywordDB(keyword=get_or_create_token(kw, db=db), note_id=note.id)
            for kw in self.keywords
        ]
        note.entities = [
            NoteEntityDB(entity=get_or_create_token(entity, db=db), note_id=note.id)
            for entity in self.entities
        ]
        note.urls = [
            NoteURLDB(url=get_or_create_token(url, db=db), note_id=note.id)
            for url in self.urls
        ]

        db.commit()
        db.refresh(note)

        self.created_at = note.created_at
        self.updated_at = note.updated_at

        return
    
    def archive(self, db: Session = None) -> None:
        """ Archives note (soft delete)."""
        db = db or get_session()
        note = db.query(NoteDB).filter_by(id=self.id).first()
        if note:
            note.active = False
            db.commit()
        self.active = False

    def handle_snippet_delete(self, snippet_ord: int, db: Session = None) -> None:
        """Deletes a snippet from a note."""
        db = db or get_session()
        if snippet_ord < 1 or snippet_ord > len(self.snippets):
            print(f"{Fore.RED}Snippet with ord={snippet_ord} not found.")
            return
        snippet = self.snippets[snippet_ord-1]
        snippet_db = db.query(SnippetDB).filter_by(id=snippet.id).first()
        if not snippet_db:
            print(f"{Fore.RED}Snippet with ID={snippet.id} not found.")
            return
        db.delete(snippet_db)
        db.commit()
        self.snippets.pop(snippet_ord-1)
        print(f"{Fore.CYAN}✅ Snippet {snippet_ord} deleted from current note{Style.RESET_ALL}")

    @classmethod
    def fromDBobject(cls, note: NoteDB) -> 'Note':
        """ Create a note from a DB object """
        return cls(
            id=note.id,
            title=note.title,
            created_at=note.created_at,
            updated_at=note.updated_at,
            custom_fields=eval(note.custom_fields),
            embedding=note.embedding,
            active=note.active,
            snippets=[
                Snippet(
                    id=snippet.id,
                    content=snippet.content,
                    created_at=snippet.created_at,
                    updated_at=snippet.updated_at,
                    tags={tag.tag.value for tag in snippet.tags},
                    keywords={keyword.keyword.value for keyword in snippet.keywords},
                ) for snippet in note.snippets
            ],
            entities={entity.entity.value for entity in note.entities},
            urls={url.url.value for url in note.urls},
            tags={tag.tag.value for tag in note.tags},
            keywords={keyword.keyword.value for keyword in note.keywords},
        )

    @staticmethod
    def get(id: int, db: Session = None) -> 'Note':
        """ Retrieves a note by ID """
        db = db or get_session()
        note = db.query(NoteDB).filter_by(id=id).first()
        if not note:
            print(f"{Fore.RED}Note with ID {id} not found.")
            return None
        return Note.fromDBobject(note)

    @staticmethod
    def getAll(db: Session = None) -> List['Note']:
        """Retrieves all active notes from the DB."""
        db = db or get_session()
        note_dbs = db.query(NoteDB).filter(NoteDB.active == True).all()
        return [Note.fromDBobject(note) for note in note_dbs]

    def delete(self, confirm: bool = True, db: Session = None) -> None:
        """Permanently deletes a note."""
        db = db or get_session()
        note = db.query(NoteDB).filter(NoteDB.id == self.id).first()
        if not note:
            raise ValueError(f"Note with ID={self.id} not found.")
        
        if confirm:
            confirmation = input(fwarn("Are you sure you want to delete note ID")+str(self.id)+fwarn("? (y/n): "))
            if confirmation.lower() not in ["y", "yes"]:
                return None

        db.delete(note)
        db.commit()

    @staticmethod
    def deleteAll(id: int, title: str = None, confirm: bool = True, db: Session = None) -> int:
        """ Permanently deletes multiple notes."""
        db = db or get_session()
        if id:
            notes = db.query(NoteDB).filter(NoteDB.id == id).all()
        elif title:
            if '*' in title:
                notes = db.query(NoteDB).filter(NoteDB.title.like(title.replace('*', '%'))).all()
            else:
                notes = db.query(NoteDB).filter(NoteDB.title == title).all()
        else:
            raise ValueError("Please provide either an ID or title to delete notes.")
        
        if not notes:
            return 0
        
        """ Confirm deletion of notes """
        if confirm:
            confirmation = input(fwarn(f"Are you sure you want to delete {len(notes)} note(s)? (y/n): "))
            if confirmation.lower() not in ["y", "yes"]:
                return None

        for note in notes:
            db.delete(note)
        db.commit()
        return len(notes)

    @staticmethod
    def search(filters: List[str], db: Session = None) -> List['Note']:
        """Search for notes based on tag, keyword, or content filters."""
        db = db or get_session()

        if filters:
            raise NotImplementedError("Filtering notes is not yet implemented?")

        query = db.query(NoteDB) #.join(SnippetDB).outerjoin(SnippetTagDB).outerjoin(SnippetKeywordDB)

        for filter_str in filters:
            if filter_str.startswith("#"):
                query = query.filter(SnippetTagDB.tag == filter_str[1:])
            elif filter_str.startswith("@"):
                query = query.filter(SnippetKeywordDB.keyword == filter_str[1:])
            else:
                query = query.filter(SnippetDB.content.ilike(f"%{filter_str}%"))

        notes_db = query.distinct().all()
        return [Note.fromDBobject(note) for note in notes_db]
    
    # --- Snippets Handling ---)

    def add_snippet(self, content: str, display: bool=False, db: Session = None) -> SnippetDB:
        """Adds a snippet to a note and DB and extracts tags/keywords."""
        db = db or get_session()

        # Extract tags and keywords
        tags, keywords = extract_tags_and_keywords(content)

        # check if snippet is composed of tags only. If so, do not add a snippet, instead add tags to note
        if containsTagsOnly(content):
            if display:
                clear_terminal_line()
            self.tags.update(tags)
            self.persist(db=db)
            print(f"{Fore.CYAN}✅ Tags {tags} added to current note{Style.RESET_ALL}")
            return None

        # Create snippet object
        snippet = Snippet(
            content=content,
            tags=tags,
            keywords=keywords,
        )

        if display:
            clear_terminal_line()
            snippet.display(ord=len(self.snippets)+1)

        # Persist snippet
        new_snippet = snippet.persist(note_id=self.id, db=db)

        # Add snippet to note
        self.snippets.append(snippet)

        return new_snippet

    # --- Queue Operations ---

    def to_queue(self, db: Session = None):
        """Adds a newly created note to the queue for further processing."""
        db = db or get_session()

        # first check if note is already in the queue
        queue_entry = db.query(QueueDB).filter_by(note_id=self.id).all()
        existing_tasks = [entry.task for entry in queue_entry]

        for task in [
            QueueTask.ASSIGN_METADATA,
            QueueTask.SUGGEST_NODES,
            QueueTask.EMBED,
        ]:
            if task in existing_tasks:
                continue
            queue_entry = QueueDB(
                note_id=self.id, 
                task=task,
            )
            db.add(queue_entry)

        db.commit()

# --- other functions ---

def update_note_metadata(note: NoteDB, metadata: NoteMetadata, db: Session = None):
    """Updates the metadata of a note."""
    raise NotImplementedError("Update note metadata not implemented")
    db = db or get_session()

    # Clear existing relationships to avoid duplicates
    note.tags.clear()
    note.keywords.clear()
    note.entities.clear()

    # Add new relationships properly
    note.tags.extend([NoteTagDB(tag=tag, note_id=note.id) for tag in metadata.tags])
    note.keywords.extend([NoteKeywordDB(keyword=kw, note_id=note.id) for kw in metadata.keywords])
    note.entities.extend([NoteEntityDB(entity=entity, note_id=note.id) for entity in metadata.entities])

    db.add(note)  # Explicitly add the note to the session
    db.commit()
    db.refresh(note)  # Refresh to reflect new DB state

    print(f"✅ Updated metadata for note ID={note.id} with tags={metadata.tags}, keywords={metadata.keywords}, entities={metadata.entities}")


# QUEUE OPERATIONS

def list_queue(db: Session = None) -> List[QueueDB]:
    """Lists all tasks in the queue."""
    db = db or get_session()
    return db.query(QueueDB).all()

def clear_queue(db: Session = None):
    """Clears all tasks in the queue."""
    db = db or get_session()
    db.query(QueueDB).delete()
    db.commit()

# GRAPH OPERATIONS

class Graph(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    nx: nx.Graph
    ROOT: ClassVar[str] = "__ROOT__"

    @classmethod
    def initDB(cls, root_locations = [], db: Session = None) -> 'Graph':
        """Initializes the graph in the DB."""
        db = db or get_session()
        
        # create root node if it does not exist
        root_node = db.query(NodeDB).filter_by(name=cls.ROOT).first()
        if not root_node:
            db.add(NodeDB(name=cls.ROOT))
            db.commit()

        # load Graph from DB in the current state
        G = cls.fromDB(db=db)

        # add every root location
        for loc in root_locations:
            G.get_or_create_location(loc, db=db)

        return G

    @classmethod
    def fromDB(cls, db: Session = None) -> 'Graph':
        """Creates a graph from the DB."""
        db = db or get_session()
        nodes = db.query(NodeDB).all()
        edges = db.query(EdgeDB).all()
        # nodes_notes = db.query(NoteNodeDB).all()
        graph = nx.Graph()
        for node in nodes:
            graph.add_node(cls.ROOT if node.name==Graph.ROOT else node.id, nodeDB=node, note_ids=[note.note_id for note in node.note_links])
        for edge in edges:
            graph.add_edge(edge.from_node, edge.to_node, edgeDB=edge)
        return cls(nx=graph)
    
    def upsert_location(self, location: Union[str, List[str]], db: Session = None) -> None:
        """Upserts a location in the graph."""
        db = db or get_session()
        if isinstance(location, str):
            location: List[str] = split_location_to_nodes(location)

        # always start from root
        if not self.nx.nodes[self.ROOT]:
            self.nx.add_node(self.ROOT, note_ids=[])

        # every location implicitly starts from the root, 
        # so the first node is root's direct child, and so on
        curr_node = self.nx.nodes[self.ROOT]
        for node_name in enumerate(location):
            # check if node_name is in the current node's children.
            # if not, add it using the name as id (temporarily). look at the "name" attribute of the node
            if node_name not in self.nx.neighbors(curr_node):
                # add the node to the db, also the edge
                new_node = NodeDB(name=node_name)
                new_edge = EdgeDB(from_node=curr_node, to_node=new_node)
                # add the edge to the db
                db.add(new_edge)
                # add the node to the db
                db.add(new_node)
                db.commit()
                db.refresh(new_node)
                # add the node to the graph
                self.nx.add_node(new_node.id, name=new_node.name, note_ids=[])
                self.nx.add_edge(curr_node, new_node)
                curr_node = new_node

    def get_or_create_location(self, location: Union[str, List[str]], db: Session = None) -> NodeDB:
        """Retrieves or creates the given node location.
           E.g. if location is: "A > B > C", it will create nodes A, B, and C if they do not exist,
           then link them together as A > B and B > C.
           Returns the last node object.
        """
        db = db or get_session()

        if isinstance(location, str):
            location: List[str] = split_location_to_nodes(location)

        print(f"{Fore.CYAN}Adding location: {location}{Style.RESET_ALL}")

        # Start from the root node
        if self.ROOT not in self.nx:
            raise ValueError("Root node not found in graph. This should not happen.")

        curr_node_id = self.ROOT  # ✅ We assume self.ROOT was added as a node ID
        for node_name in location:
            # Check if the node exists as a neighbor with the given name
            matching_neighbors = [
                n for n in self.nx.neighbors(curr_node_id)
                if self.nx.nodes[n]["nodeDB"].name == node_name
            ]

            if len(matching_neighbors) > 1:
                raise ValueError(f"Multiple nodes named '{node_name}' found near '{curr_node_id}'")
            elif matching_neighbors:
                curr_node_id = matching_neighbors[0]
            else:
                # Create new node and edge
                new_node_db = NodeDB(name=node_name)
                db.add(new_node_db)
                db.commit()
                db.refresh(new_node_db)

                # DB edge
                db.add(EdgeDB(from_node=curr_node_id, to_node=new_node_db.id))
                db.commit()

                # Graph update
                self.nx.add_node(new_node_db.id, nodeDB=new_node_db, note_ids=[])
                self.nx.add_edge(curr_node_id, new_node_db.id)

                curr_node_id = new_node_db.id

        return self.nx.nodes[curr_node_id]["nodeDB"]