from sqlalchemy import Enum
from sqlalchemy.orm import Session

from .types import NoteMetadata
from .db import NoteEntityDB, NoteKeywordDB, NoteTagDB, QueueTask, get_db, NoteDB, SnippetDB, TokenDB, NoteTagDB, SnippetTagDB, NoteKeywordDB, SnippetKeywordDB, AIEntry, Edge, QueueDB
from datetime import datetime
from typing import List, Optional
import re

# Regex for extracting tags (#tag) and keywords (@keyword)
TAG_PATTERN = r"#([\w-]+|\"[^\"]+\")"
KEYWORD_PATTERN = r"@([\w-]+|\"[^\"]+\")"

# --- Helper Functions ---
def extract_tags_and_keywords(text: str):
    """Extracts tags and keywords from text."""
    tags = re.findall(TAG_PATTERN, text)
    keywords = re.findall(KEYWORD_PATTERN, text)
    return set(tags), set(keywords)

# --- CRUD Operations ---

def get_or_create_token(value: str, db: Session = None) -> TokenDB:
    """Retrieves or creates a token by value."""
    db = db or next(get_db())
    token = db.query(TokenDB).filter_by(value=value).first()
    if not token:
        token = TokenDB(value=value)
        db.add(token)
        db.commit()  # Commit to ensure the token ID is generated
    return token

def create_note(title: str = "untitled", db: Session = None) -> NoteDB:
    """Creates a new note with a title."""
    db = db or next(get_db())
    new_note = NoteDB(title=title)
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

def add_snippet(note_id: int, content: str, db: Session = None) -> SnippetDB:
    """Adds a snippet to a note and extracts tags/keywords."""
    db = db or next(get_db())
    
    new_snippet = SnippetDB(note_id=note_id, content=content)
    db.add(new_snippet)
    db.commit()
    db.refresh(new_snippet)

    # Extract tags and keywords
    tags, keywords = extract_tags_and_keywords(content)

    # Insert tags
    for tag in tags:
        token = get_or_create_token(tag, db=db)
        db.add(SnippetTagDB(snippet_id=new_snippet.id, token_id=token.id))

    # Insert keywords
    for keyword in keywords:
        token = get_or_create_token(keyword, db=db)
        db.add(SnippetKeywordDB(snippet_id=new_snippet.id, token_id=token.id))

    db.commit()
    return new_snippet

def get_notes(db: Session = None) -> List[NoteDB]:
    """Retrieves all active notes."""
    db = db or next(get_db())
    return db.query(NoteDB).filter(NoteDB.active == True).all()

def get_note_by_id(note_id: int, db: Session = None) -> Optional[NoteDB]:
    """Retrieves a note by ID."""
    db = db or next(get_db())
    return db.query(NoteDB).filter_by(id=note_id).first()

def archive_note(note_id: int, db: Session = None):
    """Deletes a note (soft delete)."""
    db = db or next(get_db())
    note = db.query(NoteDB).filter_by(id=note_id).first()
    if note:
        note.active = False
        db.commit()

def delete_notes(id: int, title: str = None, confirm: bool = True, db: Session = None):
    """Permanently deletes multiple notes."""
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

def search_notes(filters: List[str], db: Session = None) -> List[NoteDB]:
    """Search for notes based on tag, keyword, or content filters."""
    db = db or next(get_db())

    query = db.query(NoteDB).join(SnippetDB).outerjoin(SnippetTagDB).outerjoin(SnippetKeywordDB)

    for filter_str in filters:
        if filter_str.startswith("#"):
            query = query.filter(SnippetTagDB.tag == filter_str[1:])
        elif filter_str.startswith("@"):
            query = query.filter(SnippetKeywordDB.keyword == filter_str[1:])
        else:
            query = query.filter(SnippetDB.content.ilike(f"%{filter_str}%"))

    return query.distinct().all()

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

# DUMMY
def add_ai_entry(note_id: int, snippet_id: Optional[int], content: str, content_type: str, model_name: str, db: Session = None):
    """Adds an AI-generated entry (embedding, summary, chat response)."""
    db = db or next(get_db())
    
    ai_entry = AIEntry(
        note_id=note_id,
        snippet_id=snippet_id,
        content=content,
        content_type=content_type,
        model_name=model_name,
    )
    
    db.add(ai_entry)
    db.commit()
    db.refresh(ai_entry)
    return ai_entry

def link_notes(from_note: int, to_note: int, relation: str, db: Session = None):
    """Creates a relation (edge) between two notes."""
    db = db or next(get_db())
    
    edge = Edge(from_note=from_note, to_note=to_note, relation=relation)
    db.add(edge)
    db.commit()
    return edge

# QUEUE OPERATIONS

def add_note_to_queue(note_id: int, db: Session = None):
    """Adds a newly created note to the queue for further processing."""
    db = db or next(get_db())
    for task in [
        QueueTask.ASSIGN_METADATA,
        QueueTask.SUGGEST_NODES,
        QueueTask.EMBED,
    ]:
        queue_entry = QueueDB(
            note_id=note_id, 
            task=task,
        )
        db.add(queue_entry)
    db.commit()

def list_queue(db: Session) -> List[QueueDB]:
    """Lists all tasks in the queue."""
    return db.query(QueueDB).all()

def clear_queue(db: Session):
    """Clears all tasks in the queue."""
    db.query(QueueDB).delete()
    db.commit()