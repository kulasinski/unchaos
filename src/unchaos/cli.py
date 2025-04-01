import os
import signal
import sys
from typing import List, Union

import toml
import click
from tabulate import tabulate, SEPARATING_LINE
from colorama import Fore, Style, init

from unchaos.ai import handle_queue_task

from .config import config
from .db import NoteURLDB, get_session
from .types import QueueStatus, QueueTask, Token
from .utils import clear_terminal, ferror, fstatus, fsys, ftag, fentity, fwarn, split_location_to_nodes, format_dt
from .models import Graph, Note, clear_queue, list_queue

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
    """Lists notes based on provided filters (tags, entities, or content)."""

    notes = Note.search(filters)

    if not filters:
        click.echo(f"WARNING: Listing ALL {len(notes)} notes... Please provide at least one filter (tag, entity, or content) for better results.")
    else:
        click.echo(f"Found {len(notes)} notes matching filters: {filters}")

    if not notes:
        click.echo(f"No notes found matching filters: {filters}")
        return

    # click.echo("-" * 100)
    # for note in notes:
    #     click.echo(f"{Fore.CYAN}ID:{Style.RESET_ALL} [{note.id}] | "\
    #                f"{Fore.CYAN}Title:{Style.RESET_ALL} {note.title} | "\
    #                f"{Fore.CYAN}Snippets:{Style.RESET_ALL} {len(note.snippets)} | "\
    #                f"{Fore.CYAN}Created at:{Style.RESET_ALL} {note.created_at.strftime('%Y-%m-%d %H:%M:%S')} | "
    #                f"{Fore.CYAN}Tags:{Style.RESET_ALL} {Fore.GREEN}{', '.join(['#'+tag for tag in note.tagsAll])}{Style.RESET_ALL} | "\
    #                f"{Fore.CYAN}Entities:{Style.RESET_ALL} {Fore.MAGENTA}{', '.join(['@'+kw for kw in note.entitiesAll])}{Style.RESET_ALL}"
    #     )
    #     click.echo("-" * 100)

    headers = [fsys("ID"), fsys("Title"), fsys("Snippets"), fsys("Created At"), fsys("Tags"), fsys("Entities"), fsys("Times")]
    table = [
        [
            fsys(str(note.id)),
            note.title,
            len(note.snippets),
            note.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ", ".join([ftag(tag) for tag in note.tagsAll]),
            ", ".join([fentity(entity) for entity in note.entitiesAll]),
            ", ".join([f"{t.literal}" for t in note.timesAll])
        ]
        for note in notes
    ]

    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))
# --- Command to Show Tags, Entities, and Tokens ---

@cli.command(name="tags")
@click.option("--order_by", "-o", type=str, default="count", help="Order by count or name")
def show_tags(order_by: str):
    """Displays all tags in the database. Order by count or name."""
    tags: List[Token] = Note.display_tokens_in_use(tags=True, order_by=order_by)
    unq_tags = len(tags)
    tot_tags = sum(tag.count for tag in tags)
    # click.echo(f"Tags in use: {len(tags)}")

    headers = ["Tag", "Count"]
    table = [[ftag(tag.value), tag.count] for tag in tags]
    table += ["",
        [fwarn("UNIQUE"), unq_tags],
        [fwarn("TOTAL"), tot_tags],
    ]
    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))

@cli.command(name="entities")
@click.option("--order_by", "-o", type=str, default="count", help="Order by count or name")
def show_entities(order_by: str):
    """Displays all entities in the database. Order by count or name."""
    entities: List[Token] = Note.display_tokens_in_use(entities=True, order_by=order_by)
    unq_entities = len(entities)
    tot_entities = sum(e.count for e in entities)

    headers = ["Entity", "Count", "Type"]
    table = [[fentity(e.value), e.count, e.entityType or "?"] for e in entities]
    table += ["",
        [fwarn("UNIQUE"), unq_entities, ""],
        [fwarn("TOTAL"), tot_entities, ""],
    ]
    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))

@cli.command(name="tokens")
@click.option("--order_by", "-o", type=str, default="count", help="Order by count or name")
def show_tokens(order_by: str):
    """Displays all tokens in the database. Order by count or name."""
    tokens: List[Token] = Note.display_tokens_in_use(tags=True, entities=True, order_by=order_by)
    unq_tokens = len(tokens)
    tot_tokens = sum(t.count for t in tokens)

    headers = ["Tag | Entity", "Type", "Entity Type", "Count"]
    table = [[ftag(t.value) if t.type=='TAG' else fentity(t.value), 
              t.type, 
              t.entityType or ('-' if t.type=='TAG' else '?'), 
              t.count] for t in tokens]
    table += ["",
        [fwarn("UNIQUE"), unq_tokens, ""],
        [fwarn("TOTAL"), tot_tokens, ""],
    ]
    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))

@cli.command(name="time")
def show_times():
    """Displays all time entries in the database."""
    from .db import get_session
    from .db import TimeDB

    db = get_session()
    times = db.query(TimeDB).all()

    if not times:
        click.echo("No time entries found.")
        return

    headers = ["ID", "Value", "Literal", "Scope"]
    table = [[time.id, time.value, time.literal, time.scope or "-"] for time in times]
    
    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))

# --- Command to Show URLs ---
@cli.command(name="url")
def show_urls():
    """Displays all URLs stored in the database."""
    db = get_session()
    urls = db.query(NoteURLDB).all()

    headers = ["Note ID", "Note Title", "URL"]
    table = [[url.note_id, url.note.title, url.url.value] for url in urls]

    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))

# --- Command to List Tasks in the Queue ---
@click.group()
def queue():
    """Manage tasks in the queue."""
    pass

@queue.command(name="list")
def queue_list():
    """Lists tasks in the queue."""
    from .models import list_queue

    queue_items = list_queue()
    headers = ["Task ID", "Note ID", "Task", "Status", "Created At"]
    table = [
        [fsys(item.id), fsys(item.note_id), item.task, fstatus(item.status), fsys(format_dt(item.created_at))]
        for item in queue_items
    ]
    click.echo(tabulate(table, headers=headers, tablefmt="simple_outline"))

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

# --- Command for Graph Handling ---
@click.group()
def graph():
    pass

@graph.command(name="init")
def init_graph():
    """Initializes the graph structure using the locations provided in the config"""

    root_locations = config.get("graph.roots", [])
    root_locations_expanded = []
    for loc in root_locations:
        node_names = split_location_to_nodes(loc)
        last_node = node_names[-1]
        if "|" in last_node:
            for last_node_split in last_node.split("|"):
                root_locations_expanded.append(node_names[:-1] + [last_node_split.strip()])
        else:
            root_locations_expanded.append(node_names)

    G = Graph.initDB(root_locations=root_locations_expanded)

@graph.command(name="add")
@click.argument("location", type=str)
def add_node(location: str):
    """Adds a new node to the graph structure. Use notation 'Node1 > Node2 > Node3'."""
    db = get_session()
    new_nodeDB = Graph\
        .fromDB(db=db)\
        .get_or_create_location(location=location, db=db)
    if new_nodeDB:
        click.echo(f"Node '{location}' added to the graph.")

@graph.command(name="show")
def show_graph():
    """Displays the graph structure of the notes."""
    Graph.fromDB().display_nodes()

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
    db = get_session()
    tasks = list_queue(db=db)
    """ Order tasks by the task type: ASSIGN_METADATA, SUGGEST_NODES, EMBED """
    order = {QueueTask.ASSIGN_METADATA: 1, QueueTask.SUGGEST_NODES: 2, QueueTask.EMBED: 3}
    tasks = sorted(tasks, key=lambda task: order[task.task])
    click.echo(f"Found {len(tasks)} tasks in the queue.")

    # Handle task one by one
    for task in tasks:
        print(fsys(f"Handling task {task.task} for note {task.note_id}..."))
        note = Note.get(task.note_id, db=db)
        if not note:
            click.echo(ferror(f"Note with ID {task.note_id} not found."))
            continue
        handle_queue_task(task, note, db=db)

        break # TODO temp

    click.echo("🔮 Magick complete! ✅")

# ----------------------------
# --- Registering commands ---
# ----------------------------

cli.add_command(init)
cli.add_command(create)
cli.add_command(delete)
cli.add_command(show)
cli.add_command(show_tags)
cli.add_command(show_entities)
cli.add_command(show_tokens)
cli.add_command(show_times)
cli.add_command(show_urls)
cli.add_command(edit)
cli.add_command(list)
cli.add_command(graph)
cli.add_command(queue)
cli.add_command(magick)
cli.add_command(delete_db)

if __name__ == "__main__":
    cli()  # Run the CLI application
