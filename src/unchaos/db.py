from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os
from datetime import datetime
from .config import config

# Load database path from config
DB_PATH = config.get("storage.database", os.path.expanduser("~/.unchaos/unchaos.db"))
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Table Definitions ---
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, default="untitled", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedding = Column(Text)  # Store as JSON or serialized vector
    active = Column(Boolean, default=True)

    snippets = relationship("Snippet", back_populates="note", cascade="all, delete-orphan")
    queue = relationship("Queue", back_populates="note", uselist=False)

class Snippet(Base):
    __tablename__ = "snippets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    note = relationship("Note", back_populates="snippets")
    tags = relationship("SnippetTag", back_populates="snippet", cascade="all, delete-orphan")
    keywords = relationship("SnippetKeyword", back_populates="snippet", cascade="all, delete-orphan")

class Tag(Base):
    __tablename__ = "tags"

    tag = Column(String(128), primary_key=True)  # Tags are unique

class SnippetTag(Base):
    __tablename__ = "snippet_tags"

    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True)
    tag = Column(String(128), ForeignKey("tags.tag", ondelete="CASCADE"), primary_key=True)

    snippet = relationship("Snippet", back_populates="tags")

class Keyword(Base):
    __tablename__ = "keywords"

    keyword = Column(String(128), primary_key=True)  # Keywords are unique

class SnippetKeyword(Base):
    __tablename__ = "snippet_keywords"

    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True)
    keyword = Column(String(128), ForeignKey("keywords.keyword", ondelete="CASCADE"), primary_key=True)

    snippet = relationship("Snippet", back_populates="keywords")

class AIEntry(Base):
    __tablename__ = "ai"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=False)  # 'embedding', 'summary', 'chat'
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Edge(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    to_note = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    relation = Column(String, nullable=False)  # e.g., "causes", "relates_to"

class Queue(Base):
    __tablename__ = 'queue'

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey('notes.id', ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default='pending')  # status could be "pending", "processing", etc.
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    note = relationship("Note", back_populates="queue")

    def __repr__(self):
        return f"<Queue(id={self.id}, note_id={self.note_id}, status={self.status})>"

# --- Database Initialization ---
def init_db():
    """Initialize the database schema."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized.")

# --- Session Helper ---
def get_db():
    """Dependency for getting a session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()