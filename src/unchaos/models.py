from typing import List, Optional, Sequence, Set
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Enum
from sqlalchemy.orm import Session

from .types import NoteMetadata, QueueTask
from .db import NoteEntityDB, NoteKeywordDB, NoteTagDB, get_db, NoteDB, SnippetDB, NoteTagDB, SnippetTagDB, NoteKeywordDB, SnippetKeywordDB, QueueDB, get_or_create_token
from .utils import containsTagsOnly, extract_tags_and_keywords, now_formatted

class Snippet(BaseModel):
    id: int = None
    content: str
    created_at: datetime = None
    updated_at: datetime = None
    tags: Set[str] = None
    keywords: Set[str] = None

    def persist(self, note_id: int, db: Session = None) -> None:
        """Creates a new snippet in DB."""
        db = db or next(get_db())
        new_snippet = SnippetDB(note_id=note_id, content=self.content)
        db.add(new_snippet)
        db.commit()
        db.refresh(new_snippet)

        # update the snippet with the new ID and timestamps
        self.id = new_snippet.id
        self.created_at = new_snippet.created_at
        self.updated_at = new_snippet.updated_at

        # Insert tags
        for tag in self.tags:
            token = get_or_create_token(tag, db=db)
            db.add(SnippetTagDB(snippet_id=new_snippet.id, token_id=token.id))

        # Insert keywords
        for keyword in self.keywords:
            token = get_or_create_token(keyword, db=db)
            db.add(SnippetKeywordDB(snippet_id=new_snippet.id, token_id=token.id))

        db.commit()

    @classmethod
    def fromDBobject(cls, snippet: SnippetDB) -> 'Snippet':
        """Create a snippet from a DB object."""
        return cls(
            id=snippet.id,
            content=snippet.content,
            created_at=snippet.created_at,
            updated_at=snippet.updated_at,
            tags={tag.tag for tag in snippet.tags},
            keywords={keyword.keyword for keyword in snippet.keywords},
        )
    
    @staticmethod
    def get(id: int, db: Session = None) -> 'Snippet':
        """Retrieves a snippet by ID."""
        db = db or next(get_db())
        snippet = db.query(SnippetDB).filter_by(id=id).first()
        if not snippet:
            raise ValueError(f"Snippet with ID={id} not found.")
        return Snippet.fromDBobject(snippet)


class Note(BaseModel):
    id: int = None
    title: str|None
    created_at: datetime = None
    updated_at: datetime = None
    custom_fields: dict|None = None
    embedding: Sequence[float]|None = None
    active: bool = True
    snippets: List[Snippet] = []
    entities: Set[str] = None
    urls: Set[str] = None
    tags: Set[str] = None     # own not snippets'
    keywords: Set[str] = None # own not snippets'

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
    
    def addToken(self, tokenType: str, tokenCalue: str):
        """ Set a token field in the note """
        if tokenType not in self.__token_fields:
            raise ValueError(f"Invalid token type: {tokenType}")
        tokens: Set = getattr(self, tokenType)
        tokens.add(tokenCalue)
        setattr(self, tokenType, tokens)

    def removeToken(self, tokenType: str, tokenCalue: str):
        """ Remove a token field in the note """
        if tokenType not in self.__token_fields:
            raise ValueError(f"Invalid token type: {tokenType}")
        tokens: Set = getattr(self, tokenType)
        tokens.remove(tokenCalue)
        setattr(self, tokenType, tokens)

    # --- CRUD Operations ---

    def persist(self, db: Session = None) -> None:
        """ Creates a new note in DB """
        db = db or next(get_db())

        if not self.title:
            self.title = f"untitled ({now_formatted()})"

        new_note = NoteDB(title=self.title) 

        db.add(new_note)
        db.commit()
        db.refresh(new_note)

        # get ID
        self.id = new_note.id

        return new_note
    
    def archive(self, db: Session = None) -> None:
        """ Archives note (soft delete)."""
        db = db or next(get_db())
        note = db.query(NoteDB).filter_by(id=self.id).first()
        if note:
            note.active = False
            db.commit()
        self.active = False

    @classmethod
    def fromDBobject(cls, note: NoteDB) -> 'Note':
        """ Create a note from a DB object """
        return cls(
            id=note.id,
            title=note.title,
            created_at=note.created_at,
            updated_at=note.updated_at,
            custom_fields=note.custom_fields, # TODO parse dict
            embedding=note.embedding,
            active=note.active,
            snippets=[Snippet(
                id=snippet.id,
                content=snippet.content,
                created_at=snippet.created_at,
                tags={tag.tag for tag in snippet.tags},
                keywords={keyword.keyword for keyword in snippet.keywords},
            ) for snippet in note.snippets],
            entities={entity.entity for entity in note.entities},
            urls={url.url for url in note.urls},
            tags={tag.tag for tag in note.tags},
            keywords={keyword.keyword for keyword in note.keywords},
        )

    @staticmethod
    def get(id: int, db: Session = None) -> 'Note':
        """ Retrieves a note by ID """
        db = db or next(get_db())
        note = db.query(NoteDB).filter_by(id=id).first()
        if not note:
            raise ValueError(f"Note with ID={id} not found.")
        return Note.fromDBobject(note)

    @staticmethod
    def getAll(db: Session = None) -> List['Note']:
        """Retrieves all active notes from the DB."""
        db = db or next(get_db())
        note_dbs = db.query(NoteDB).filter(NoteDB.active == True).all()
        return [Note.fromDBobject(note) for note in note_dbs]

    def delete(self, confirm: bool = True, db: Session = None) -> None:
        """Permanently deletes a note."""
        db = db or next(get_db())
        note = db.query(NoteDB).filter(NoteDB.id == self.id).first()
        if not note:
            raise ValueError(f"Note with ID={self.id} not found.")
        
        if confirm:
            confirmation = input(f"Are you sure you want to delete note ID={self.id}? (y/n): ")
            if confirmation.lower() not in ["y", "yes"]:
                return None

        db.delete(note)
        db.commit()

    @staticmethod
    def deleteAll(id: int, title: str = None, confirm: bool = True, db: Session = None) -> int:
        """ Permanently deletes multiple notes."""
        db = db or next(get_db())
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
            confirmation = input(f"Are you sure you want to delete {len(notes)} note(s)? (y/n): ")
            if confirmation.lower() not in ["y", "yes"]:
                return None

        for note in notes:
            db.delete(note)
        db.commit()
        return len(notes)

    @staticmethod
    def search(filters: List[str], db: Session = None) -> List['Note']:
        """Search for notes based on tag, keyword, or content filters."""
        db = db or next(get_db())

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
    
    # --- Snippets Handling ---

    def add_snippet(self, content: str, db: Session = None) -> SnippetDB:
        """Adds a snippet to a note and DB and extracts tags/keywords."""
        db = db or next(get_db())

        # Extract tags and keywords
        tags, keywords = extract_tags_and_keywords(content)

        # check if snippet is composed of tags only. If so, do not add a snippet, instead add tags to note
        if containsTagsOnly(content):
            for tag in tags:
                self.addToken("tags", tag)
            self.persist(db=db)
            return None

        # Create snippet object
        snippet = Snippet(
            content=content,
            tags=tags,
            keywords=keywords,
        )

        # Persist snippet
        new_snippet = snippet.persist(note_id=self.id, db=db)

        # Add snippet to note
        self.snippets.append(snippet)

        return new_snippet

    # --- Queue Operations ---

    def to_queue(self, db: Session = None):
        """Adds a newly created note to the queue for further processing."""
        db = db or next(get_db())

        for task in [
            QueueTask.ASSIGN_METADATA,
            QueueTask.SUGGEST_NODES,
            QueueTask.EMBED,
        ]:
            queue_entry = QueueDB(
                note_id=self.id, 
                task=task,
            )
            db.add(queue_entry)

        db.commit()















def update_note_metadata(note: NoteDB, metadata: NoteMetadata, db: Session = None):
    """Updates the metadata of a note."""
    db = db or next(get_db())

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

def list_queue(db: Session) -> List[QueueDB]:
    """Lists all tasks in the queue."""
    return db.query(QueueDB).all()

def clear_queue(db: Session):
    """Clears all tasks in the queue."""
    db.query(QueueDB).delete()
    db.commit()