from datetime import datetime
import re
from typing import List, Tuple

from colorama import Fore, Style

from .types import QueueStatus

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

def format_dt(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string."""
    return dt.strftime(fmt)

def now_formatted():
    return format_dt(datetime.now())

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

def fstatus(status: str):
    if status == QueueStatus.PENDING:
        return Fore.YELLOW + status + Style.RESET_ALL
    elif status == QueueStatus.PROCESSING:
        return Fore.CYAN + status + Style.RESET_ALL
    elif status == QueueStatus.COMPLETED:
        return Fore.GREEN + status + Style.RESET_ALL
    elif status == QueueStatus.FAILED:
        return Fore.RED + status + Style.RESET_ALL

def furl(content: str) -> str:
    """Formats URLs in gray color."""
    urls = extract_urls(content)
    for url in urls:
        content = content.replace(url, f"{Fore.LIGHTBLACK_EX}{url}{Style.RESET_ALL}")
    return content

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
