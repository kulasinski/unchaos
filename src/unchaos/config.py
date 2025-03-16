import os

# Base storage directory
STORAGE_DIR = os.path.expanduser("~/.unchaos/storage")

# Ensure the directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)