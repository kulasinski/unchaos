import argparse
import signal
import sys
import os
import json

from colorama import Fore, Style, init

from .storage import Note
from .config import STORAGE_DIR

init(autoreset=True)  # Initialize colorama


def show_note(note_id, show_all=False):
    """Display a note with color highlights for tags and keywords."""
    note_file = os.path.join(STORAGE_DIR, f"{note_id}.json")

    if not os.path.exists(note_file):
        print(f"{Fore.RED}Error: Note {note_id} not found.")
        return

    with open(note_file, "r", encoding="utf-8") as f:
        note = json.load(f)

    print(Fore.CYAN+(note['id']+" " if show_all else "")+f"{note['meta']['title']} ({note['meta']['created_at']})")

    for idx, snippet in enumerate(note['snippets']):
        snippet_id = snippet['id'] if show_all else f"[{idx+1}]"
        snippet_content = snippet['content']

        # Highlight tags and keywords
        for tag in note['tags']:
            snippet_content = snippet_content.replace(f"#{tag}", f"{Fore.GREEN}#{tag}{Style.RESET_ALL}")
        for keyword in note['keywords']:
            snippet_content = snippet_content.replace(f"@{keyword}", f"{Fore.MAGENTA}@{keyword}{Style.RESET_ALL}")

        print(f"{Fore.CYAN}{snippet_id}{Style.RESET_ALL} {snippet_content}")

def add_note(title="Untitled"):
    """Interactive snippet input with Ctrl+D to save and Ctrl+C to discard."""
    print(f"Creating note: {title}\nEnter snippets (Ctrl+D to save, Ctrl+C to discard):")
    
    note = Note(title)  # Pass title to Note

    def handle_interrupt(sig, frame):
        print("\nDiscarding note...")
        note.discard()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    try:
        while True:
            try:
                snippet = input("> ")
                if snippet.strip():
                    note.save_snippet(snippet)
            except EOFError:
                print("\nNote saved.")
                break
    except KeyboardInterrupt:
        print("\nDiscarding note...")
        note.discard()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(prog="unchaos", description="Unchaos your notes")
    parser.add_argument("action", choices=["add", "list", "remove", "show"], help="Action to perform")
    parser.add_argument("note", nargs="?", help="Note content or ID")
    parser.add_argument("-a", "--all", action="store_true", help="Show note ID and snippet ID")

    args = parser.parse_args()

    if args.action == "add":
        add_note(args.note if args.note else "Untitled")

    elif args.action == "list":
        from .storage import list_notes
        notes = list_notes()
        if not notes:
            print("No notes found.")
        else:
            for note in notes:
                print(f"[{note['id']}] {note['meta'].get('title', 'Untitled')} ({len(note['snippets'])} snippets)")

    elif args.action == "remove":
        from .storage import remove_note
        if not args.note:
            print("Error: Please provide note ID to remove.")
            return
        if remove_note(args.note):
            print(f"Note {args.note} removed.")
        else:
            print(f"Error: Note {args.note} not found.")

    elif args.action == "show":
        if not args.note:
            print("Error: Please provide note ID to show.")
            return
        show_note(args.note, show_all=args.all)

if __name__ == "__main__":
    main()