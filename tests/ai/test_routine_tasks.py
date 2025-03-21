from unchaos.ai import NoteMetadata, SuggestedNodes, assign_metadata_to_text, embed, suggest_nodes_to_text

def test_metadata_assignment():
    # output = assign_metadata_to_text("I told @Mike to meet me the next day at 10 am in starbucks. #todo \n\nI also need to buy some groceries.\n what is NLP??")
    output = assign_metadata_to_text("Nauczyć Mieszka jak robić kupę w nocniku. #todo")
    assert output is not None
    assert isinstance(output, NoteMetadata)
    assert "todo" in output.tags
    # assert "Mike" in output.keywords
    # assert "NLP" in output.keywords
    # assert "Starbucks" in output.entities

def test_graph_placement():
    # output = suggest_nodes_to_text("I need to buy some groceries and meet @Mike at starbucks.")
    # output = suggest_nodes_to_text("Nauczyć Mieszka jak robić kupę w nocniku. #todo")
    output = suggest_nodes_to_text("remind @Mike about fixing the code for Forecastix.")
    assert output is not None
    assert isinstance(output, SuggestedNodes)
    nodes_split = output.split_nested_nodes()
    print(nodes_split)
    assert any(["Household" in node_split for node_split in nodes_split])
    assert any(["Personal" in node_split for node_split in nodes_split])

def test_embedding():
    texts = [
        "I need to buy some groceries and meet @Mike at starbucks.",
        "I like coffee and tea.",
    ]

    embedding = embed(texts[0])
    assert embedding is not None
    assert len(embedding) == 768
    
    embeddings = embed(texts)
    assert embeddings is not None
    assert len(embeddings) == 2
    assert len(embeddings[0]) == len(embedding)