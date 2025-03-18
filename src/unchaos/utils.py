from unchaos.models import Note

def find_note_by_id_or_name(session, identifier):
    """
    Helper function to find a note by ID or name.
    """
    # Check if the identifier is an integer (ID) or a string (name)
    try:
        # If it's an integer, try finding by ID
        note_id = int(identifier)
        note = session.query(Note).filter_by(id=note_id).first()
    except ValueError:
        # If it's not an integer, treat it as a name
        note = session.query(Note).filter_by(title=identifier).first()

    return note