import os
import json
import uuid
from datetime import datetime
import re

from .io import show_note
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

def list_notes(filters=None):
    """List notes filtered by tags and keywords."""
    notes = []
    
    if filters:
        print(f"Filtering notes by tags: {filters.get('tags', [])} and keywords: {filters.get('keywords', [])}")

    for file_name in os.listdir(STORAGE_DIR):
        if file_name.endswith(".json"):
            note_file = os.path.join(STORAGE_DIR, file_name)

            with open(note_file, "r", encoding="utf-8") as f:
                note = json.load(f)

            if not filters:  # No filters, add all notes
                notes.append(note)
                continue

            # Check if note matches filter criteria
            tags_match = any(tag in note["tags"] for tag in filters.get("tags", []))
            keywords_match = any(keyword in note["keywords"] for keyword in filters.get("keywords", []))

            # print(note["tags"], note["keywords"], tags_match, keywords_match)

            if tags_match or keywords_match:
                notes.append(note)

        # Show matching notes and their snippets
    if notes and filters:
        for note in notes:
            show_note(note["id"], show_all=True, filters=filters)
    elif filters:
        print("No notes found matching the filters.")
    elif notes:
        for note in notes:
            print(f"{note['id']} {note['meta']['title']} ({note['meta']['created_at']})")
    else:
        print("No notes found.")


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
    def __init__(self, title="Untitled"):
        self.note_id = str(uuid.uuid4())
        self.file_path = os.path.join(STORAGE_DIR, f"{self.note_id}.json")
        self.note_data = {
            "id": self.note_id,
            "meta": {
                "created_at": datetime.now().isoformat(),
                "updated_at": "",
                "title": title
            },
            "snippets": [],
            "tags": [],
            "keywords": []
        }

    def save_snippet(self, content):
        """Appends a snippet to the note, extracts tags & keywords, and persists immediately."""
        tags, keywords = extract_tags_and_keywords(content)

        snippet = {
            "id": str(uuid.uuid4()),
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