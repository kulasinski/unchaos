from enum import Enum
from datetime import datetime
import os

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from unchaos.types import QueueStatus
from .config import config

# Load database path from config
DB_PATH = config.get("database.path")
if not DB_PATH:
    print("⚠️ Database path not found in config. Make sure to include the path to your database file.")
    exit(1)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Core Tables ---

class NoteDB(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, default="untitled", nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    custom_fields = Column(Text)  # Store as JSON or serialized metadata
    embedding = Column(Text)  # Store as JSON or serialized vector
    active = Column(Boolean, default=True)

    snippets = relationship("SnippetDB", back_populates="note", cascade="all, delete-orphan")
    queue = relationship("QueueDB", back_populates="note", cascade="all, delete-orphan")
    tags = relationship("NoteTagDB", back_populates="note", cascade="all, delete-orphan")
    keywords = relationship("NoteKeywordDB", back_populates="note", cascade="all, delete-orphan")
    entities = relationship("NoteEntityDB", back_populates="note", cascade="all, delete-orphan")
    urls = relationship("NoteURLDB", back_populates="note", cascade="all, delete-orphan")

class SnippetDB(Base):
    __tablename__ = "snippets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    note = relationship("NoteDB", back_populates="snippets")
    tags = relationship("SnippetTagDB", back_populates="snippet", cascade="all, delete-orphan")
    keywords = relationship("SnippetKeywordDB", back_populates="snippet", cascade="all, delete-orphan")

class TokenDB(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(256), unique=True, nullable=False)  # Unique tokens

    note_tags = relationship("NoteTagDB", back_populates="tag", cascade="all, delete-orphan")
    snippet_tags = relationship("SnippetTagDB", back_populates="tag", cascade="all, delete-orphan")
    note_keywords = relationship("NoteKeywordDB", back_populates="keyword", cascade="all, delete-orphan")
    snippet_keywords = relationship("SnippetKeywordDB", back_populates="keyword", cascade="all, delete-orphan")
    note_entities = relationship("NoteEntityDB", back_populates="entity", cascade="all, delete-orphan")
    note_urls = relationship("NoteURLDB", back_populates="url", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TokenDB(value={self.value})>"

# --- Linking Tables ---

class SnippetTagDB(Base):
    __tablename__ = "snippet_tags"

    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    snippet = relationship("SnippetDB", back_populates="tags")
    tag = relationship("TokenDB", foreign_keys=[token_id])

class NoteTagDB(Base):
    __tablename__ = "note_tags"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    note = relationship("NoteDB", back_populates="tags")
    tag = relationship("TokenDB", foreign_keys=[token_id])

class SnippetKeywordDB(Base):
    __tablename__ = "snippet_keywords"

    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    snippet = relationship("SnippetDB", back_populates="keywords")
    keyword = relationship("TokenDB", foreign_keys=[token_id])

class NoteKeywordDB(Base):
    __tablename__ = "note_keywords"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    note = relationship("NoteDB", back_populates="keywords")
    keyword = relationship("TokenDB", foreign_keys=[token_id])

# class SnippetEntity(Base): Snippets are only at the note level! same for URLs, because user does not add them to snippets manually

class NoteEntityDB(Base):
    __tablename__ = "note_entities"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    note = relationship("NoteDB", back_populates="entities")
    entity = relationship("TokenDB", foreign_keys=[token_id])

class NoteURLDB(Base):
    __tablename__ = "note_urls"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    note = relationship("NoteDB", back_populates="urls")
    url = relationship("TokenDB", foreign_keys=[token_id])

# --- Other Tables ---

# class AIEntry(Base):
#     __tablename__ = "ai"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
#     snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), nullable=True)
#     content = Column(Text, nullable=False)
#     content_type = Column(String, nullable=False)  # 'embedding', 'summary', 'chat'
#     model_name = Column(String, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EdgeDB(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    to_note = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    relation = Column(String, nullable=False)  # e.g., "causes", "relates_to"

class QueueDB(Base):
    __tablename__ = 'queue'

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey('notes.id', ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default=QueueStatus.PENDING.value)
    status_details = Column(Text, nullable=True)
    task = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    note = relationship("NoteDB", back_populates="queue")

    def __repr__(self):
        return f"<QueueDB(id={self.id}, note_id={self.note_id}, status={self.status})>"

# --- Database Initialization ---
def init_db():
    """Initialize the database schema."""
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at {DB_PATH}")

# -- Helper Functions

def get_session() -> Session:
    """Returns an active session for database interaction."""
    return next(get_db())

def get_or_create_token(value: str, db: Session = None) -> TokenDB:
    """Retrieves or creates a token by value."""
    db = db or get_session()
    token = db.query(TokenDB).filter_by(value=value).first()
    if not token:
        token = TokenDB(value=value)
        db.add(token)
        db.commit()  # Commit to ensure the token ID is generated
    return token

# --- Session Helper ---
def get_db():
    """Dependency for getting a session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()