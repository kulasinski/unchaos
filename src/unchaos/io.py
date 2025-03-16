import os
import json

from colorama import Fore, Style, init

from .config import STORAGE_DIR

init(autoreset=True)  # Initialize colorama

def show_note(note_id, show_all=False, filters=None):
    """Display a note with color highlights for tags and keywords."""
    note_file = os.path.join(STORAGE_DIR, f"{note_id}.json")

    print("filters", filters)   

    if not os.path.exists(note_file):
        print(f"{Fore.RED}Error: Note {note_id} not found.")
        return

    with open(note_file, "r", encoding="utf-8") as f:
        note = json.load(f)

    print(Fore.CYAN+(note['id']+" " if show_all else "")+f"{note['meta']['title']} ({note['meta']['created_at']})")

    for idx, snippet in enumerate(note['snippets']):
        if filters:
            tags = [f'#{tag}' for tag in filters['tags']]
            keywords = [f'@{keyword}' for keyword in filters['keywords']]
            if not any(tag in snippet['content'] for tag in tags) and not any(keyword in snippet['content'] for keyword in keywords):
                continue
            
        snippet_id = snippet['id'] if show_all else f"[{idx+1}]"
        snippet_content = snippet['content']

        # Highlight tags and keywords
        for tag in note['tags']:
            snippet_content = snippet_content.replace(f"#{tag}", f"{Fore.GREEN}#{tag}{Style.RESET_ALL}")
        for keyword in note['keywords']:
            snippet_content = snippet_content.replace(f"@{keyword}", f"{Fore.MAGENTA}@{keyword}{Style.RESET_ALL}")

        print(f"{Fore.CYAN}{snippet_id}{Style.RESET_ALL} {snippet_content}")