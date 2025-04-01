from enum import Enum
from datetime import datetime
import os

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLAEnum, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

from unchaos.types import QueueStatus, TimeScope
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
    entities = relationship("NoteEntityDB", back_populates="note", cascade="all, delete-orphan")
    urls = relationship("NoteURLDB", back_populates="note", cascade="all, delete-orphan")
    nodes = relationship("NoteNodeDB", back_populates="note", cascade="all, delete-orphan")
    times = relationship("NoteTimeDB", back_populates="note", cascade="all, delete-orphan")

class SnippetDB(Base):
    __tablename__ = "snippets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    note = relationship("NoteDB", back_populates="snippets")
    tags = relationship("SnippetTagDB", back_populates="snippet", cascade="all, delete-orphan")
    entities = relationship("SnippetEntityDB", back_populates="snippet", cascade="all, delete-orphan")
    times = relationship("SnippetTimeDB", back_populates="snippet", cascade="all, delete-orphan")

class TokenDB(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(256), unique=True, nullable=False)  # Unique tokens

    note_tags = relationship("NoteTagDB", back_populates="tag", cascade="all, delete-orphan")
    snippet_tags = relationship("SnippetTagDB", back_populates="tag", cascade="all, delete-orphan")
    note_entities = relationship("NoteEntityDB", back_populates="entity", cascade="all, delete-orphan")
    snippet_entities = relationship("SnippetEntityDB", back_populates="entity", cascade="all, delete-orphan")
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

class SnippetEntityDB(Base):
    __tablename__ = "snippet_entities"

    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)
    entity_type = Column(String(50), nullable=True)  # see EntityType enum

    snippet = relationship("SnippetDB", back_populates="entities")
    entity = relationship("TokenDB", foreign_keys=[token_id])

class NoteEntityDB(Base):
    __tablename__ = "note_entities"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)
    entity_type = Column(String(50), nullable=True)  # see EntityType enum

    note = relationship("NoteDB", back_populates="entities")
    entity = relationship("TokenDB", foreign_keys=[token_id])

class NoteURLDB(Base):
    __tablename__ = "note_urls"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    token_id = Column(Integer, ForeignKey("tokens.id", ondelete="RESTRICT"), primary_key=True)

    note = relationship("NoteDB", back_populates="urls")
    url = relationship("TokenDB", foreign_keys=[token_id])

class NoteTimeDB(Base):
    __tablename__ = "note_times"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    time_id = Column(Integer, ForeignKey("times.id", ondelete="CASCADE"), primary_key=True)

    note = relationship("NoteDB", back_populates="times")
    time = relationship("TimeDB", back_populates="note_times")

class SnippetTimeDB(Base):
    __tablename__ = "snippet_times"

    snippet_id = Column(Integer, ForeignKey("snippets.id", ondelete="CASCADE"), primary_key=True)
    time_id = Column(Integer, ForeignKey("times.id", ondelete="CASCADE"), primary_key=True)

    snippet = relationship("SnippetDB", back_populates="times")
    time = relationship("TimeDB", back_populates="snippet_times")

# --- Other Tables ---

class NodeDB(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # Unique node names

    edges_from = relationship(
        "EdgeDB", foreign_keys="[EdgeDB.from_node]", back_populates="from_node_rel"
    )
    edges_to = relationship(
        "EdgeDB", foreign_keys="[EdgeDB.to_node]", back_populates="to_node_rel"
    )
    note_links = relationship("NoteNodeDB", back_populates="node", cascade="all, delete-orphan")

class EdgeDB(Base):
    __tablename__ = "edges"

    from_node = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    to_node = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)

    from_node_rel = relationship("NodeDB", foreign_keys=[from_node], back_populates="edges_from")
    to_node_rel = relationship("NodeDB", foreign_keys=[to_node], back_populates="edges_to")
    
class NoteNodeDB(Base):
    __tablename__ = "note_nodes"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)

    note = relationship("NoteDB", back_populates="nodes")
    node = relationship("NodeDB", back_populates="note_links")

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

class TimeDB(Base):
    __tablename__ = "times"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(DateTime(timezone=True), nullable=False)
    literal = Column(String, nullable=False)
    scope = Column(SQLAEnum(TimeScope), nullable=True)

    note_times = relationship("NoteTimeDB", back_populates="time", cascade="all, delete-orphan")
    snippet_times = relationship("SnippetTimeDB", back_populates="time", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('value', 'literal', 'scope', name='_value_literal_scope_uc'),
        CheckConstraint(
            "scope IN ('SECOND', 'MINUTE', 'HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR', 'CENTURY')",
            name='check_scope'
        ),
    )

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

def get_or_create_url(value: str, db: Session = None) -> TokenDB:
    """Retrieves or creates a URL by value."""
    db = db or get_session()
    url = db.query(TokenDB).filter_by(value=value).first()
    if not url:
        url = TokenDB(value=value)
        db.add(url)
        db.commit()  # Commit to ensure the URL ID is generated
    return url

# --- Session Helper ---
def get_db():
    """Dependency for getting a session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
