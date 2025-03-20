import logging
import os
from datetime import datetime
import signal
import sys

import toml
import click

from .models import add_to_queue, create_note, add_snippet, get_notes, get_note_by_id, delete_notes, list_queue, search_notes, add_ai_entry, link_notes
from .db import get_db
from sqlalchemy.orm import Session
from typing import List, Union

@click.group()
def cli():
    """Unchaos CLI - A tool for managing your notes with advanced tagging, AI integration, and searching."""
    pass

# Helper function to get the active DB session
def get_session() -> Session:
    """Returns an active session for database interaction."""
    return next(get_db())


# ------------------------------------
# --- Command Line Interface (CLI) ---
# ------------------------------------

# --- Command to Initialize the System ---
@click.command()
def init():
    """Initializes the system: creates the configuration file and sets up the database."""
    
    # Ensure the user has the necessary directories
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".unchaos")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    # Create the config file if it does not exist
    config_path = os.path.join(config_dir, "config.toml")
    if not os.path.exists(config_path):
        config_data = {
            "database": {
                "path": os.path.join(config_dir, "unchaos.db")
            },
            "llm": {
                "host": "localhost",
                "port": 11411  # Default port for Ollama, for example
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

# --- Command to Add a Note ---
@click.command()
@click.argument("title", default=None, required=False)
def add(title: str):
    """Adds a new note with the given title."""
    if not title:
        title = f"untitled ({datetime.now().strftime("%Y-%m-%d %H:%M:%S")})"
    # Create a new note
    note = create_note(title=title, db=get_session())
    click.echo(f"Note created with ID: {note.id} and title: {note.title}")
    click.echo("Enter snippets one by one. (Ctrl+D to save note, Ctrl+C to discard note):")

    def handle_interrupt(sig, frame):
        click.echo("\nCancelling and deleting note...")
        delete_notes(note.id, db=get_session())  # Deleting the note on Ctrl+C
        sys.exit(0)

    def handle_exit(sig, frame):
        click.echo("\nFinishing and saving note...")
        add_to_queue(note.id, db=get_session())
        click.echo(f"Note {note.id} added to the queue.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGQUIT, handle_exit)

    # Loop to accept multiple snippets from the user
    while True:
        try:
            content = click.prompt("> ", prompt_suffix="")
        except click.Abort:
            handle_exit(None, None)
        if not content.strip():
            continue
        add_snippet(note.id, content, db=get_session())  # Adding snippet
        click.echo(f"Snippet added to Note {note.id}")

# --- Command to Delete a Note ---
@click.command()
@click.argument('identifier')  # ID or name of the note
def delete(identifier: Union[str,int]):
    """
    Delete a note by its ID or name.
    """
    session = get_session()

    # Infer the type of identifier (ID or name) and find the note
    id, title = None, None
    try:
        id = int(identifier)
    except ValueError:
        title = identifier

    len_notes_deleted = delete_notes(id=id, title=title, db=session)

    if not len_notes_deleted:
        click.echo(f"No notes deleted.")
    elif len_notes_deleted == 0:
        click.echo(f"No note found with {'id' if id else 'title'} '{identifier}'.")
    else:
        click.echo(f"{len_notes_deleted} note(s) with {'id' if id else 'title'} '{identifier}' has been deleted.")

# --- Command to Show Notes ---
@click.command()
@click.argument("note_id", type=int)
def show(note_id: int):
    """Displays a note by ID."""
    note = get_note_by_id(note_id, db=get_session())

    if not note:
        click.echo(f"Note with ID {note_id} not found.")
        return

    click.echo(f"Note Title: {note.title}")
    click.echo(f"Created At: {note.created_at.isoformat()}")
    click.echo("-" * 50)

    for snippet in note.snippets:
        click.echo(f"Snippet ID: {snippet.id} | Content: {snippet.content}")
        # Display tags and keywords
        tags = [tag.tag for tag in snippet.tags]
        keywords = [keyword.keyword for keyword in snippet.keywords]
        click.echo(f"Tags: {tags}")
        click.echo(f"Keywords: {keywords}")
        click.echo("-" * 50)

# --- Command to List Notes ---
@click.command()
@click.argument("filters", nargs=-1)
def list(filters: List[str]):
    """Lists notes based on provided filters (tags, keywords, or content)."""
    

    if not filters:
        print("WARNING: Listing ALL the notes... Please provide at least one filter (tag, keyword, or content) for better results.")

    notes = search_notes(filters, db=get_session())

    if not notes:
        click.echo(f"No notes found matching filters: {filters}")
        return

    for note in notes:
        click.echo(f"Note ID: {note.id} | Title: {note.title} | Created At: {note.created_at.isoformat()}")
        click.echo("-" * 50)
        for snippet in note.snippets:
            click.echo(f"Snippet ID: {snippet.id} | Content: {snippet.content}")
            tags = [tag.tag for tag in snippet.tags]
            keywords = [keyword.keyword for keyword in snippet.keywords]
            click.echo(f"Tags: {tags}")
            click.echo(f"Keywords: {keywords}")
            click.echo("-" * 50)

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
@click.command()
def queue():
    """Lists tasks in the queue."""
    queue_items = list_queue(db=get_session())
    click.echo(f"{len(queue_items)} tasks in the queue:")
    for item in queue_items:
        click.echo(f"Task ID: {item.id} | Note ID: {item.note_id} | Status: {item.status} | Created At: {item.created_at}")

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

# ----------------------------
# --- Registering commands ---
# ----------------------------

cli.add_command(init)
cli.add_command(add)
cli.add_command(delete)
cli.add_command(show)
cli.add_command(list)
cli.add_command(link)
cli.add_command(queue)
cli.add_command(ai)
cli.add_command(delete_db)

if __name__ == "__main__":
    cli()  # Run the CLI application