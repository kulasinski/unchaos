from datetime import datetime
import re
from typing import Tuple

# Regex for extracting tags (#tag) and keywords (@keyword)
TAG_PATTERN = r"#([\w-]+|\"[^\"]+\")"
KEYWORD_PATTERN = r"@([\w-]+|\"[^\"]+\")"

def extract_tags_and_keywords(text: str) -> Tuple[set, set]:
    """Extracts tags and keywords from text."""
    tags = re.findall(TAG_PATTERN, text)
    keywords = re.findall(KEYWORD_PATTERN, text)
    return set(tags), set(keywords)

def containsTagsOnly(text: str):
    """Returns True if the text contains only tags."""
    tokens = text.split()
    for token in tokens:
        if not token.startswith("#"):
            return False
    return True

def flatten(lst):
    return [item for sublist in lst for item in sublist]

def now_formatted():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def clear_terminal_line():
    print("\033[A                             \033[A")
# 🚫