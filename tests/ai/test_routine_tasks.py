from unchaos.ai import NoteMetadata, SuggestedNodes, assign_metadata_to_text, suggest_nodes_to_text

def test_metadata_assignment():
    output = assign_metadata_to_text("I told @Mike to meet me the next day at 10 am in starbucks. #todo \n\nI also need to buy some groceries.\n what is NLP??")
    assert output is not None
    assert isinstance(output, NoteMetadata)
    assert "todo" in output.tags
    assert "Mike" in output.keywords
    assert "NLP" in output.keywords
    assert "Starbucks" in output.entities

def test_graph_placement():
    output = suggest_nodes_to_text("I need to buy some groceries and meet @Mike at starbucks.")
    assert output is not None
    assert isinstance(output, SuggestedNodes)
    nodes_split = output.split_nested_nodes()
    assert any(["Household" in node_split for node_split in nodes_split])
    assert any(["Personal" in node_split for node_split in nodes_split])