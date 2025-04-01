from enum import Enum
from typing import List, Literal
from datetime import datetime

from pydantic import BaseModel

class NoteMetadata(BaseModel):
    tags: List[str] = []
    entities: List[str] = []

    def strip_prefixes(self):
        self.tags = [tag.strip("#") for tag in self.tags]
        self.entities = [entity.strip("@") for entity in self.entities]

class SuggestedNodes(BaseModel):
    nested_nodes: List[str] = []

    def split_nested_nodes(self) -> List[List[str]]:
        def split_node(node: str):
            return [n.strip() for n in node.split(">")]
        return [split_node(node) for node in self.nested_nodes]
    
class EntityType(str, Enum):
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    DATE = "DATE"
    
class Token(BaseModel):
    type: Literal["ENTITY", "TAG"]
    value: str
    entityType: EntityType | None = None
    count: int | None = None

class QueueStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class QueueTask(str, Enum):
    ASSIGN_METADATA = "ASSIGN_METADATA"
    SUGGEST_NODES = "SUGGEST_NODES"
    EMBED = "EMBED"

class TimeScope(Enum):
    SECOND = "SECOND"
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"
    CENTURY = "CENTURY"

class Time(BaseModel):
    value: datetime
    literal: str
    scope: TimeScope | None = None

    def __hash__(self):
        """Make Time objects hashable."""
        return hash((self.value, self.literal, self.scope))

    def __eq__(self, other):
        """Ensure equality checks are consistent with hashing."""
        if not isinstance(other, Time):
            return False
        return (self.value, self.literal, self.scope) == (other.value, other.literal, other.scope)