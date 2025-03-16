import os
import json
import uuid
from datetime import datetime
import re

from .config import STORAGE_DIR

TAG_PATTERN = r'#(?:\"(.*?)\"|(\w+))'
KEYWORD_PATTERN = r'@(\w+)'

def extract_tags_and_keywords(text):
    """Extracts tags (#tag or #"multi-word tag") and keywords (@keyword) from text."""
    tags = [match[0] or match[1] for match in re.findall(TAG_PATTERN, text)]
    keywords = re.findall(KEYWORD_PATTERN, text)
    return tags, keywords

def save_note(content):
    """Saves a note to a JSON file with a unique ID."""
    note_id = str(uuid.uuid4())  # Generate unique ID
    note_data = {
        "id": note_id,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }

    file_path = os.path.join(STORAGE_DIR, f"{note_id}.json")
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(note_data, f, indent=4)

    return note_id

def list_notes():
    """Lists all stored notes."""
    notes = []
    for filename in os.listdir(STORAGE_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(STORAGE_DIR, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                notes.append(json.load(f))
    return notes

def remove_note(note_id):
    """Removes a note by its ID."""
    file_path = os.path.join(STORAGE_DIR, f"{note_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

class Note:
    """Handles note creation and storage."""
    def __init__(self):
        self.note_id = str(uuid.uuid4())
        self.file_path = os.path.join(STORAGE_DIR, f"{self.note_id}.json")
        self.note_data = {
            "id": self.note_id,
            "meta": {
                "created_at": datetime.now().isoformat(),
                "updated_at": None,
                "title": None
            },
            "snippets": [],
            "tags": [],
            "keywords": []
        }

    def save_snippet(self, content):
        """Appends a snippet to the note, extracts tags & keywords, and persists immediately."""
        tags, keywords = extract_tags_and_keywords(content)

        snippet = {
            "created_at": datetime.now().isoformat(),
            "content": content
        }
        self.note_data["snippets"].append(snippet)

        # Update tags and keywords
        self.note_data["tags"].extend(tag for tag in tags if tag not in self.note_data["tags"])
        self.note_data["keywords"].extend(keyword for keyword in keywords if keyword not in self.note_data["keywords"])

        self.note_data["meta"]["updated_at"] = datetime.now().isoformat()

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.note_data, f, indent=4)