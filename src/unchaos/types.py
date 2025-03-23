from pydantic import BaseModel
from typing import List

class NoteMetadata(BaseModel):
    tags: List[str] = []
    keywords: List[str] = []
    entities: List[str] = []

    def strip_prefixes(self):
        self.tags = [tag.strip("#") for tag in self.tags]
        self.keywords = [keyword.strip("@") for keyword in self.keywords]

class SuggestedNodes(BaseModel):
    nested_nodes: List[str] = []

    def split_nested_nodes(self) -> List[List[str]]:
        def split_node(node: str):
            return [n.strip() for n in node.split(">")]
        return [split_node(node) for node in self.nested_nodes]