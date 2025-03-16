import argparse
import signal
import sys

from .storage import Note, list_notes
from .io import show_note

def parse_filters(filter_str):
    """Parse the filter string and return a list of required tags and keywords."""
    filters = {"tags": [], "keywords": []}
    
    # Split the filter by spaces, which is the default delimiter
    parts = filter_str.split()

    # Check if we have # or @ in the string
    for part in parts:
        if part.startswith('#'):
            filters["tags"].append(part[1:])
        elif part.startswith('@'):
            filters["keywords"].append(part[1:])
        else:
            # Treat unprefixed words as both tags or keywords
            filters["tags"].append(part)
            filters["keywords"].append(part)

    return filters

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
    parser.add_argument("-f", "--filter", help="Filter notes by tags and keywords, e.g. '#redflag&@Mike'")

    args = parser.parse_args()

    if args.action == "add":
        add_note(args.note if args.note else "Untitled")

    elif args.action == "list":
        filters = parse_filters(args.filter) if args.filter else None
        list_notes(filters)

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