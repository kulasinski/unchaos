# unchaos
Your git for Notes.
 Take notes like pro - enhanced with AI
 Take notes the way our brain works - it is not linear!

Locally:

```
poetry install
poetry run unchaos list
```

Globally:
```
poetry build
python3 -m pip install --force-reinstall dist/*.whl --break-system-packages # Install it globally via pip
```

## Usage

### Add/create a note
### Delete a note
- by id (integer) `unchaos delete <id>`
- by title (string) `unchaos delete <title>`
- using wildcard in "", e.g. `unchaos delete "untitled*"`

## Tips

- Run `sqlite3 ~/.unchaos/unchaos.db` to view the database.

## Migrations

poetry run alembic revision --autogenerate -m "Initial migration"
Apply Migration: poetry run alembic upgrade head

## Structure

unchaos/
│── unchaos/
│   │── __init__.py
│   │── cli.py              # CLI entry point
│   │── config.py           # Handles config loading from ~/.unchaos/config.toml
│   │── db.py               # SQLite database connection and migrations
│   │── models.py           # ORM-like classes for Notes, Snippets, Queue
│   │── queue.py            # Handles the primitive LLM queue mechanism
│   │── ollama_client.py    # Interface to the local Ollama instance
│   │── commands/
│   │   │── __init__.py
│   │   │── add.py          # Handles 'unchaos add'
│   │   │── list.py         # Handles 'unchaos list'
│   │   │── show.py         # Handles 'unchaos show'
│   │   │── remove.py       # Handles 'unchaos remove'
│   │── utils/
│   │   │── extractors.py   # Tag and keyword extraction logic
│   │   │── formatter.py    # Terminal color formatting for display
│── tests/                  # Unit tests
│── pyproject.toml          # Poetry package configuration
│── README.md               # Documentation

## Init

`unchaos init --db_location <path to db file>`

## Example usage

# TODO
* supabase storage
* handle updated_at
* tabela do urli i quotesów i pytań (2 ostatnie moze tylko przez tagi?)- regex 
* chat - oparty na SQL searchu + semantic search
* smarter search
* add quote field, next to tags and kws
* leverage copilot workspace!
* add: unchaos tags/kw to display those in use
* cron sync every night