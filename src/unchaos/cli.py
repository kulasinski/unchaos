import logging
import os
from datetime import datetime
import signal
import sys

import toml
import click

from unchaos.utils import find_note_by_id_or_name

from .models import add_to_queue, create_note, add_snippet, get_notes, get_note_by_id, delete_note, search_notes, add_ai_entry, link_notes
from .db import get_db
from sqlalchemy.orm import Session
from typing import List

@click.group()
def cli():
    """Unchaos CLI - A tool for managing your notes with advanced tagging, AI integration, and searching."""
    pass


# Helper function to get the active DB session
def get_session() -> Session:
    """Returns an active session for database interaction."""
    return next(get_db())

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
@click.argument("title", default="untitled")
def add(title: str):
    """Adds a new note with the given title."""
    # Create a new note
    note = create_note(title=title, db=get_session())
    click.echo(f"Note created with ID: {note.id} and title: {note.title}")
    click.echo("Enter snippets one by one. (Ctrl+D to save note, Ctrl+C to discard note):")

    def handle_interrupt(sig, frame):
        click.echo("\nCancelling and deleting note...")
        delete_note(note.id, db=get_session())  # Deleting the note on Ctrl+C
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    # Loop to accept multiple snippets from the user
    while True:
        try:
            content = click.prompt("> ", prompt_suffix="")
            if not content.strip():
                continue
            add_snippet(note.id, content, db=get_session())  # Adding snippet
            click.echo(f"Snippet added to Note {note.id}")
        except EOFError:
            click.echo("\nFinishing and saving note...")
            # Add the newly created note to the queue
            add_to_queue(note.id, db=get_session())
            click.echo(f"Note {note.id} added to the queue.")
            break

# --- Command to Delete a Note ---
@click.command()
@click.argument('identifier')  # ID or name of the note
def delete(identifier):
    """
    Delete a note by its ID or name.
    """
    session = get_session()

    # Use helper function to find the note by ID or name
    note = find_note_by_id_or_name(session, identifier)
    
    if not note:
        click.echo(f"No note found with identifier: {identifier}")
        return

    session.delete(note)
    session.commit()

    click.echo(f"Note with identifier '{identifier}' has been deleted.")

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

# Registering commands
cli.add_command(init)
cli.add_command(add)
cli.add_command(delete)
cli.add_command(show)
cli.add_command(list)
cli.add_command(link)
cli.add_command(ai)

if __name__ == "__main__":
    cli()