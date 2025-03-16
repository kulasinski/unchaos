import argparse
import signal
import sys

from .storage import Note

def add_note():
    """Interactive snippet input with Ctrl+D to save and Ctrl+C to discard."""
    print("Enter snippets (Ctrl+D to save, Ctrl+C to discard):")
    
    note = Note()  # Create new note instance

    def handle_interrupt(sig, frame):
        print("\nDiscarding note...")
        note.discard()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)  # Capture Ctrl+C

    try:
        while True:
            try:
                snippet = input("> ")  # Get user input
                if snippet.strip():
                    note.save_snippet(snippet)
            except EOFError:  # Handle Ctrl+D
                print("\nNote saved.")
                break
    except KeyboardInterrupt:  # Handle Ctrl+C (failsafe)
        print("\nDiscarding note...")
        note.discard()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(prog="unchaos", description="Unchaos your notes")
    parser.add_argument("action", choices=["add", "list", "remove"], help="Action to perform")
    parser.add_argument("note", nargs="?", help="Note content or ID")

    args = parser.parse_args()

    if args.action == "add":
        add_note()

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

if __name__ == "__main__":
    main()