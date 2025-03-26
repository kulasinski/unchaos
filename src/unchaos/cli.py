import logging
import os
from datetime import datetime
import signal
import sys
from typing import List, Union

import toml
import click
from colorama import Fore, Style, init

from .db import get_session
from .types import QueueStatus
from .utils import clear_terminal, ferror, fsys
from .models import Note, clear_queue

@click.group()
def cli():
    """Unchaos CLI - A tool for managing your notes with advanced tagging, AI integration, and searching."""
    pass

# ------------------------------------
# --- Command Line Interface (CLI) ---
# ------------------------------------

# --- Command to Initialize the System ---
@click.command()
@click.option("--db_location", type=str, help="Overwrite the location of the database file")
def init(db_location: str = None):
    """Initializes the system: creates the configuration file and sets up the database."""
    
    # Ensure the user has the necessary directories
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".unchaos")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    # Create the config file if it does not exist
    config_path = os.path.join(config_dir, "config.toml")

    # Overwrite the database location if provided
    if db_location:
        db_location_ = os.path.join(os.path.abspath(db_location), "unchaos.db")
    else:
        db_location_ = os.path.join(config_dir, "unchaos.db")

    if not os.path.exists(config_path):
        config_data = {
            "database": {
                "path": db_location_
            },
            "llm": {
                "host": "localhost",
                "port": 11411,  # Default port for Ollama, for example
                "model_basic": "llama3.2:3b",
                "model_reason": "qwen2.5:14b", # deepseek-r1:8b
                "model_embedding": "nomic-embed-text"
            },
            "graph": {
                "roots": [
                    "Work",
                    "Personal",
                    "Household",
                ]
            }
        }
        with open(config_path, "w") as config_file:
            toml.dump(config_data, config_file)
        click.echo(f"Configuration file created at {config_path}")

    # Database initialization
    click.echo("Initializing database...")
    from .db import init_db
    init_db()  # Ensure the database schema is set up correctly
    
    click.echo("Initialization complete!")

# --- Command to Create a Note ---
@click.command(name="create")
@click.argument("title", default=None, required=False)
def create(title: str):
    """Creates a new note with the given title."""

    # Create a new note
    note = Note(
        title=title,
    )

    # Persist the note to the database
    note.persist()

    clear_terminal()
    print(f"{Fore.CYAN}Note created with ID:{Style.RESET_ALL} {note.id} {Fore.CYAN}and title:{Style.RESET_ALL} {note.title}")
    print(f"{Fore.CYAN}Enter snippets one by one. (Ctrl+D to save note, Ctrl+C to discard note):{Style.RESET_ALL}")

    def handle_interrupt(sig, frame):
        print(ferror("\nCancelling and deleting note..."))
        note.delete(confirm=False)  # Deleting the note on Ctrl+C
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_interrupt)

    note.input()

# --- Command to Delete a Note ---
@click.command()
@click.argument('identifier')  # ID or name of the note
def delete(identifier: Union[str,int]):
    """
    Delete a note by its ID or name.
    """

    # Infer the type of identifier (ID or name) and find the note
    id, title = None, None
    try:
        id = int(identifier)
    except ValueError:
        title = identifier

    len_notes_deleted = Note.deleteAll(id=id, title=title, db=None)

    if not len_notes_deleted:
        click.echo(f"No notes deleted.")
    elif len_notes_deleted == 0:
        click.echo(f"No note found with {'id' if id else 'title'} '{identifier}'.")
    else:
        click.echo(ferror(f"{len_notes_deleted} note(s) with {'id' if id else 'title'} ")+str(identifier)+ferror(" has been deleted."))

# --- Command to Show Note ---
@click.command()
@click.argument("note_id", type=int)
@click.option("--width", type=int, default=50, help="Set the width for displaying the note")
def show(note_id: int, width: int):
    """Displays a note by ID."""

    note: Note = Note.get(note_id)

    if not note:
        click.echo(f"{Fore.RED}Note with ID {note_id} not found.")
        return
    
    clear_terminal()
    note.display(width=width, footer=True)

# --- Command to Edit Note ---
@click.command()
@click.argument("note_id", type=int)
@click.option("--width", type=int, default=50, help="Set the width for displaying the note")
def edit(note_id: int, width: int):
    """Edits a note by ID."""
    
    note = Note.get(note_id)

    if not note:
        return
    
    clear_terminal()
    print("Enter snippets one by one. (Ctrl+D to save note, Ctrl+C to discard note):")
    
    note.display(width=width, footer=False)

    note.input()

# --- Command to List Notes ---
@click.command()
@click.argument("filters", nargs=-1)
def list(filters: List[str]):
    """Lists notes based on provided filters (tags, keywords, or content)."""

    notes = Note.search(filters)

    if not filters:
        click.echo(f"WARNING: Listing ALL {len(notes)} notes... Please provide at least one filter (tag, keyword, or content) for better results.")
    else:
        click.echo(f"Found {len(notes)} notes matching filters: {filters}")

    if not notes:
        click.echo(f"No notes found matching filters: {filters}")
        return

    click.echo("-" * 100)
    for note in notes:
        # note-level tokens
        # note_tags = set(tag.tag.value for tag in note.tags)
        # note_keywords = set(kw.keyword.value for kw in note.keywords)

        # snippet-level tokens
        # snippet_tags = set(flatten([tag.tag.value for tag in snippet.tags] for snippet in note.snippets))
        # snippet_keywords = set(flatten([kw.keyword.value for kw in snippet.keywords] for snippet in note.snippets))

        # unioned tokens
        # tags = note_tags.union(snippet_tags)
        # keywords = note_keywords.union(snippet_keywords)


        click.echo(f"{Fore.CYAN}ID:{Style.RESET_ALL} [{note.id}] | "\
                   f"{Fore.CYAN}Title:{Style.RESET_ALL} {note.title} | "\
                   f"{Fore.CYAN}Snippets:{Style.RESET_ALL} {len(note.snippets)} | "\
                   f"{Fore.CYAN}Created at:{Style.RESET_ALL} {note.created_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                   f"{Fore.CYAN}Tags:{Style.RESET_ALL} {Fore.GREEN}{', '.join(['#'+tag for tag in note.tagsAll])}{Style.RESET_ALL} | "\
                   f"{Fore.CYAN}Keywords:{Style.RESET_ALL} {Fore.MAGENTA}{', '.join(['@'+kw for kw in note.keywordsAll])}{Style.RESET_ALL}"
        )
        click.echo("-" * 100)

# --- Command to Link Notes ---
@click.command()
@click.argument("from_note", type=int)
@click.argument("to_note", type=int)
@click.argument("relation", type=str)
def link(from_note: int, to_note: int, relation: str):
    """Links two notes together by creating a relationship (edge)."""
    link_notes(from_note, to_note, relation, db=get_session())
    click.echo(f"Notes {from_note} and {to_note} linked with relation: {relation}")

# --- Command to List Tasks in the Queue ---
@click.group()
def queue():
    """Manage tasks in the queue."""
    pass

@queue.command(name="list")
def queue_list():
    """Lists tasks in the queue."""
    from .models import list_queue

    def color_status(status: str):
        if status == QueueStatus.PENDING:
            return Fore.YELLOW + status + Style.RESET_ALL
        elif status == QueueStatus.PROCESSING:
            return Fore.CYAN + status + Style.RESET_ALL
        elif status == QueueStatus.COMPLETED:
            return Fore.GREEN + status + Style.RESET_ALL
        elif status == QueueStatus.FAILED:
            return Fore.RED + status + Style.RESET_ALL

    queue_items = list_queue()
    click.echo(f"{len(queue_items)} tasks in the queue:")
    for item in queue_items:
        click.echo(f"Task ID: {item.id} | Note ID: {item.note_id} | Task {item.task} | Status: {color_status(item.status)} | Created At: {item.created_at}")

@queue.command(name="clear")
def queue_clear():
    """Clears all tasks in the queue."""
    clear_queue()
    click.echo("Queue cleared.")

@queue.command(name="add")
@click.argument("note_id", type=int)
def queue_add(note_id: int):
    """Adds a note to the queue for further processing."""
    db=get_session()
    note = Note.get(note_id, db=db)
    if not note:
        click.echo(f"Note with ID {note_id} not found.")
        return
    note.to_queue(db=db)
    click.echo(f"Note {note_id} added to the queue.")

# --- Command to Delete the Database ---
@click.command()
def delete_db():
    """Deletes the database file."""
    config = toml.load(os.path.join(os.path.expanduser("~"), ".unchaos", "config.toml"))
    db_path = config["database"]["path"]
    """ Ask for confirmation before deleting the database """
    confirmation = input(f"Danger! Are you sure you want to delete the database at {db_path}? (y/n): ")
    if confirmation.lower() not in ["y", "yes"]:
        return
    if os.path.exists(db_path):
        os.remove(db_path)
        click.echo("Database deleted.")
    else:
        click.echo("Database file not found.")

# --- AI Integration (Dummy) ---
@click.command()
@click.argument("note_id", type=int)
@click.argument("content", type=str)
@click.argument("content_type", type=str)
@click.argument("model_name", type=str)
def ai(note_id: int, content: str, content_type: str, model_name: str):
    """Adds an AI-generated entry (embedding, summary, etc.) to a note."""
    ai_entry = add_ai_entry(note_id, None, content, content_type, model_name, db=get_session())
    click.echo(f"AI entry added to note {note_id} with model {model_name}. Content: {ai_entry.content[:30]}...")

@click.command()
def magick():
    """ Do the unchaos magick with your notes."""
    click.echo("🔮 Magick begins... Unchaosing your notes...")
    
    """ Getting tasks from the queue and the related notes """
    tasks = list_queue(db=get_session())
    """ Order tasks by the task type: ASSIGN_METADATA, SUGGEST_NODES, EMBED """
    order = {QueueTask.ASSIGN_METADATA: 1, QueueTask.SUGGEST_NODES: 2, QueueTask.EMBED: 3}
    tasks = sorted(tasks, key=lambda task: order[task.task])
    db = get_session()
    for task in tasks:
        note = get_note_by_id(task.note_id, db=db)
        handle_queue_task(task, note, db=db)
    click.echo("🔮 Magick complete! ✅")

# --- Tests ---

@click.command()
def test():
    """Test command for debugging. https://ollama.com/blog/structured-outputs """
    output = assign_metadata_to_text("I told @Mike to meet me the next day at 10 am in starbucks. #todo \n\nI also need to buy some groceries.\n what is NLP??")
    print(output)

# ----------------------------
# --- Registering commands ---
# ----------------------------

cli.add_command(init)
cli.add_command(create)
cli.add_command(delete)
cli.add_command(show)
cli.add_command(edit)
cli.add_command(list)
cli.add_command(link)
cli.add_command(queue)
cli.add_command(magick)
cli.add_command(delete_db)
cli.add_command(test)

if __name__ == "__main__":
    cli()  # Run the CLI application