from datetime import datetime
import re
from typing import List, Tuple

from colorama import Fore, Style

# Regex for extracting tags (#tag) and entities (@entity)
TAG_PATTERN = r"#([\w-]+|\"[^\"]+\")"
KEYWORD_PATTERN = r"@([\w-]+|\"[^\"]+\")"
URL_PATTERN = r'(https?://\S+|www\.\S+|\S+\.\S+)'

def extract_tags_and_entities(text: str) -> Tuple[set, set]:
    """Extracts tags and entities from text."""
    tags = re.findall(TAG_PATTERN, text)
    entities = re.findall(KEYWORD_PATTERN, text)
    return set(tags), set(entities)

def extract_urls(text: str) -> set:
    """Extracts URLs from text."""
    urls = re.findall(URL_PATTERN, text, re.IGNORECASE)
    return set(urls)

def containsTagsOnly(text: str):
    """Returns True if the text contains only tags."""
    tokens = text.split()
    for token in tokens:
        if not token.startswith("#"):
            return False
    return True

def split_location_to_nodes(location: str, split_char: str = ">") -> List[str]:
    """Split location string to nodes."""
    return [node.strip() for node in location.split(split_char)]

def flatten(lst):
    return [item for sublist in lst for item in sublist]

def now_formatted():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fsys(content: str):
    """ Format string for system output. """
    return f"{Fore.CYAN}{content}{Style.RESET_ALL}"

def fwarn(content: str):
    """ Format string for warning output. """
    return f"{Fore.YELLOW}{content}{Style.RESET_ALL}"

def ferror(content: str):
    """ Format string for error output. """
    return f"{Fore.RED}{content}{Style.RESET_ALL}"

def fentity(content: str):
    """ Format string for entity output. """
    return f"{Fore.MAGENTA}@{content}{Style.RESET_ALL}"

def ftag(content: str):
    """ Format string for tag output. """
    return f"{Fore.GREEN}#{content}{Style.RESET_ALL}"

def format_urls_gray(text: str) -> str:
    """Formats URLs in gray color."""
    urls = extract_urls(text)
    for url in urls:
        text = text.replace(url, f"{Fore.LIGHTBLACK_EX}{url}{Style.RESET_ALL}")
    return text

def validate_url(url: str) -> bool:
    """Validates a URL."""
    return bool(re.match(URL_PATTERN, url, re.IGNORECASE))

def normalize_url(url: str) -> str:
    """Normalizes a URL to a standard format."""
    url = url.lower().strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url

def clear_terminal_line():
    print("\n\033[A                             \033[A")

def clear_terminal():
    print("\033c")
