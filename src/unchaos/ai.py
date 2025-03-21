from typing import Annotated, Any, List, Sequence, Union
from ollama import EmbedResponse, chat, embed as embed_ollama
from pydantic import BaseModel

from .config import config

""" Load relevant configuration parameters. """
model_basic = config.get("llm.model_basic")
model_reason = config.get("llm.model_reason")
model_embedding = config.get("llm.model_embedding")
graph_roots = config.get("graph.roots")

class NoteMetadata(BaseModel):
    tags: List[str] = []
    keywords: List[str] = []
    entities: List[str] = []

    def strip_prefixes(self):
        self.tags = [tag.strip("#") for tag in self.tags]
        self.keywords = [keyword.strip("@") for keyword in self.keywords]

class SuggestedNodes(BaseModel):
    nested_nodes: List[str] = []

    def split_nested_nodes(self) -> List[List[str]]:
        def split_node(node: str):
            return [n.strip() for n in node.split(">")]
        return [split_node(node) for node in self.nested_nodes]

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
    Then, assign metadata to the text: tags, keywords, and entities.

    Examples:
    - entities are names, dates, locations, addresses, IP addresses, etc.
    - tags are categories, topics, or themes.
    - keywords are important words or phrases.

    Note: if the text already contains #tags, please include them in the tags field. Feel free to add more tags.
    Note: if the text already contains keywords (prefixed by @), please include them in the keywords field. Feel free to add more keywords.
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