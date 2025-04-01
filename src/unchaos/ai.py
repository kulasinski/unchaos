from typing import Annotated, Any, List, Sequence, Union
from datetime import datetime
import re

from ollama import EmbedResponse, chat, embed as embed_ollama
from pydantic import BaseModel
from sqlalchemy.orm import Session

from unchaos.db import NoteDB, QueueDB, QueueStatus, TimeDB, get_or_create_token
from unchaos.models import Note, update_note_metadata
from unchaos.types import NoteMetadata, QueueTask, SuggestedNodes, TimeScope
from .config import config

""" Load relevant configuration parameters. """
model_basic = config.get("llm.model_basic")
model_reason = config.get("llm.model_reason")
model_embedding = config.get("llm.model_embedding")
graph_roots = config.get("graph.roots")

def generate_formatted_output(format: Any,  model_name: str, sys_prompt: str = None, user_prompt: str = None) -> BaseModel:
    if not any([sys_prompt, user_prompt]):
        raise ValueError("At least one of sys_prompt or user_prompt must be provided.")
    messages = []
    if sys_prompt:
        messages.append({
            'role': 'system',
            'content': sys_prompt,
        })
    if user_prompt:
        messages.append({
            'role': 'user',
            'content': user_prompt,
        })
    response = chat(
        messages=messages,
        model=model_name,
        format=format.model_json_schema(),
    )
    return format.model_validate_json(response.message.content)

def assign_metadata_to_text(text: str, model_name = model_reason) -> NoteMetadata:
    """ Assign metadata to the text provided by the user. """

    sys_prompt = f"""
    Your job is to assign metadata to the text provided by the user.
    First, analyze the text and its intent.
    Then, assign metadata to the text: tags and entities.

    Examples:
    - entities are (key) names, dates, locations, addresses, IP addresses, etc.
    - tags are categories, topics, themes, or just important words - but not entities.

    Note: if the text already contains #tags, please include them in the tags field. Feel free to add more tags.
    Note: if the text already contains entities (prefixed by @), please include them in the entities field. Feel free to add more entities.
    """

    output = generate_formatted_output(NoteMetadata, model_name, sys_prompt=sys_prompt, user_prompt=text)
    assert output is not None
    assert isinstance(output, NoteMetadata)
    output.strip_prefixes()

    return output

def suggest_nodes_to_text(text: str, model_name = model_reason) -> SuggestedNodes:
    """ Suggest graph nodes to the text provided by the user. """

    graph_roots_formatted = "\n".join([f"- {root}" for root in graph_roots])

    sys_prompt = f"""
    Your job is to suggest nodes to the text provided by the user, in order to correctly categorize the text and help user find thei information easily.
    First, analyze the text and its intent.
    Analyze the current node structure.
    Then, suggest nodes to the text.

    Suggest nodes in a nested format, such as: "[root_node] > [node] > [node] > etc."

    Examples:
    - If the text is about a meeting, suggest nodes like "Work > Meetings > Daily Standup".
    - If the text is about a shopping list, suggest nodes like "Household > Shopping > Groceries".
    - If the text is about a project, suggest nodes like "Work > Projects > [Project Name]".
    - If the text is about a personal note, suggest nodes like "Personal > [Topic] > [Subtopic] > etc.".

    Existing node structure (should be obeyed):
    {graph_roots_formatted}
    (Note: shorthand notation A > B | C means: A > B and A > C)

    === GENERAL TIPS ===
    Note: you can suggest between 1 and 3 nested nodes. 1 when there is only a single possible match, more than 1 when there are multiple possible matches.
    Note: as much as possible try not to create new structure if one of the existing structures can be reused.
    Note: you must not create your own root nodes (top level), as they are imposed by the user. Try to obey the existing structure.
    """ # TODO add existing schemas to inspire -> use embeddings to show the nodes of the similar notes

    output = generate_formatted_output(SuggestedNodes, model_name, sys_prompt=sys_prompt, user_prompt=text)
    assert output is not None
    assert isinstance(output, SuggestedNodes)
    assert len(output.nested_nodes) <= 3 and len(output.nested_nodes) > 0
    for node in output.nested_nodes:
        assert ">" in node

    return output

def embed(input: Union[str, List[str]]) -> Union[Sequence[Sequence[float]], Sequence[float]]:
    embed_response: EmbedResponse = embed_ollama(model=model_embedding, input=input)
    assert embed_response
    assert isinstance(embed_response, EmbedResponse)
    assert embed_response.embeddings
    if isinstance(input, str):
        return embed_response.embeddings[0]
    else:
        return embed_response.embeddings
    
def handle_queue_task(task: QueueDB, note: Note, db: Session):
    """Handle a task from the queue."""
    print(f"Handling task {task.task} for note {note.id}...")
    status = None
    status_details = None

    """ Update the note with the metadata. """
    if task.task == QueueTask.ASSIGN_METADATA:
        try:
            note_snippets = '\n'.join([snippet.content for snippet in note.snippets])
            metadata: NoteMetadata = assign_metadata_to_text(note_snippets)
            print(metadata)
            # update_note_metadata(note, metadata, db=db)
            # status = QueueStatus.COMPLETED  
        except ConnectionError as e:
            print(f"Error assigning metadata: {e}")
            raise e
        except Exception as e:
            print(f"Error assigning metadata: {e}")
            raise e
            status = QueueStatus.FAILED
            status_details = str(e)
    else:
        print(f"Task not recognized: {task.task}")
        # status = QueueStatus.FAILED
        # status_details = "Task not recognized"


    """ Update the status of the task in the database after processing. """
    # task.status = status
    # task.status_details = status_details
    # task.updated_at = datetime.utcnow()
    # db.commit()

def extract_dates(text: str) -> List[dict]:
    """Extract dates from text using regex."""
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
        r"\b\d{2}/\d{2}/\d{4}\b",  # MM/DD/YYYY
        r"\b\d{2}-\d{2}-\d{4}\b",  # DD-MM-YYYY
        r"\b\d{2} \w+ \d{4}\b",    # DD Month YYYY
        r"\b\w+ \d{2}, \d{4}\b",   # Month DD, YYYY
    ]
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            dates.append({"literal": match, "value": datetime.strptime(match, "%Y-%m-%d")})
    return dates

def append_dates_to_time_table(dates: List[dict], db: Session):
    """Append dates to the TIME table."""
    for date in dates:
        time_entry = TimeDB(
            value=date["value"],
            literal=date["literal"],
            scope=TimeScope.DAY  # Example scope, adjust as needed
        )
        db.add(time_entry)
    db.commit()

def scan_notes_for_dates(note: NoteDB, db: Session):
    """Scan notes for dates and append them to the TIME table."""
    for snippet in note.snippets:
        dates = extract_dates(snippet.content)
        append_dates_to_time_table(dates, db)
