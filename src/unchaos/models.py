from sqlalchemy.orm import Session
from .db import get_db, Note, Snippet, Tag, SnippetTag, Keyword, SnippetKeyword, AIEntry, Edge, Queue
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
def create_note(title: str = "untitled", db: Session = None) -> Note:
    """Creates a new note with a title."""
    db = db or next(get_db())
    new_note = Note(title=title)
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

def add_snippet(note_id: int, content: str, db: Session = None) -> Snippet:
    """Adds a snippet to a note and extracts tags/keywords."""
    db = db or next(get_db())
    
    new_snippet = Snippet(note_id=note_id, content=content)
    db.add(new_snippet)
    db.commit()
    db.refresh(new_snippet)

    # Extract tags and keywords
    tags, keywords = extract_tags_and_keywords(content)
    
    # Insert tags
    for tag in tags:
        if not db.query(Tag).filter_by(tag=tag).first():
            db.add(Tag(tag=tag))
        db.add(SnippetTag(snippet_id=new_snippet.id, tag=tag))

    # Insert keywords
    for keyword in keywords:
        if not db.query(Keyword).filter_by(keyword=keyword).first():
            db.add(Keyword(keyword=keyword))
        db.add(SnippetKeyword(snippet_id=new_snippet.id, keyword=keyword))

    db.commit()
    return new_snippet

def get_notes(db: Session = None) -> List[Note]:
    """Retrieves all active notes."""
    db = db or next(get_db())
    return db.query(Note).filter(Note.active == True).all()

def get_note_by_id(note_id: int, db: Session = None) -> Optional[Note]:
    """Retrieves a note by ID."""
    db = db or next(get_db())
    return db.query(Note).filter_by(id=note_id, active=True).first()

def archive_note(note_id: int, db: Session = None):
    """Deletes a note (soft delete)."""
    db = db or next(get_db())
    note = db.query(Note).filter_by(id=note_id).first()
    if note:
        note.active = False
        db.commit()

def delete_note(note_id: int, db: Session = None):
    """Permanently deletes a note."""
    db = db or next(get_db())
    note = db.query(Note).filter_by(id=note_id).first()
    if note:
        db.delete(note)
        db.commit()

def search_notes(filters: List[str], db: Session = None) -> List[Note]:
    """Search for notes based on tag, keyword, or content filters."""
    db = db or next(get_db())

    query = db.query(Note).join(Snippet).outerjoin(SnippetTag).outerjoin(SnippetKeyword)

    for filter_str in filters:
        if filter_str.startswith("#"):
            query = query.filter(SnippetTag.tag == filter_str[1:])
        elif filter_str.startswith("@"):
            query = query.filter(SnippetKeyword.keyword == filter_str[1:])
        else:
            query = query.filter(Snippet.content.ilike(f"%{filter_str}%"))

    return query.distinct().all()

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

# Function to add note to queue
def add_to_queue(note_id: int, db: Session):
    """Adds a newly created note to the queue for further processing."""
    queue_entry = Queue(note_id=note_id, status="pending", created_at=datetime.utcnow())
    db.add(queue_entry)
    db.commit()