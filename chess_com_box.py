import os
import sys
import json
import time
import requests
from dataclasses import dataclass
from typing import Final

# Constants
WIDTH_JUSTIFICATION_SEPARATOR: Final = "."
GIST_TITLE: Final = "♟︎ Chess.com Ratings"

ENV_VAR_GIST_ID: Final = "GIST_ID"
ENV_VAR_GITHUB_TOKEN: Final = "GH_TOKEN"
ENV_VAR_CHESS_COM_USERNAME: Final = "CHESS_COM_USERNAME"
REQUIRED_ENVS: Final = [
    ENV_VAR_GIST_ID,
    ENV_VAR_GITHUB_TOKEN,
    ENV_VAR_CHESS_COM_USERNAME
]

STATS_URL: Final = "https://api.chess.com/pub/player/{user}/stats"

@dataclass(frozen=True)
class TitleAndValue:
    title: str
    value: str

def validate_and_init() -> bool:
    """Check if all required environment variables are set."""
    env_vars_absent = [
        env for env in REQUIRED_ENVS 
        if not os.environ.get(env)
    ]
    
    if env_vars_absent:
        print(f"Error: Missing environment variables: {', '.join(env_vars_absent)}")
        return False
    return True

def get_adjusted_line(stat: TitleAndValue, max_line_length: int) -> str:
    """Formats a line with dots justification."""
    # Calculate spacing: total length - (title + value + 2 spaces surrounding dots)
    spacing = max_line_length - (len(stat.title) + len(stat.value) + 2)
    separator = f" {WIDTH_JUSTIFICATION_SEPARATOR * spacing} "
    return f"{stat.title}{separator}{stat.value}"

def get_chess_com_stats(user: str) -> dict:
    """Fetch stats from Chess.com Public API."""
    headers = {
        'User-Agent': f'chess-com-box-py (@{user})'
    }
    try:
        response = requests.get(STATS_URL.format(user=user), headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching Chess.com stats: {e}")
        return {}

def get_rating_line(
    stats_key: str, chess_emoji: str, chess_format: str, chess_stats: dict
) -> TitleAndValue:
    """Extracts the rating and returns a TitleAndValue object."""
    try:
        # Use .get() chains to avoid KeyError
        data = chess_stats.get(stats_key, {})
        # Tactics uses 'highest', games use 'last'
        field = "highest" if chess_format == "Tactics" else "last"
        rating = data.get(field, {}).get("rating")
        
        rating_str = f"{rating} 📈" if rating else "N/A"
    except (AttributeError, TypeError):
        rating_str = "N/A"
        
    return TitleAndValue(f"{chess_emoji} {chess_format}", rating_str)

def update_gist(title: str, content: str) -> None:
    """Updates the GitHub Gist using the REST API."""
    access_token = os.environ[ENV_VAR_GITHUB_TOKEN]
    gist_id = os.environ[ENV_VAR_GIST_ID]
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    payload = {
        'files': {
            title: {'content': content}
        }
    }
    
    try:
        r = requests.patch(
            f'https://api.github.com/gists/{gist_id}', 
            json=payload, 
            headers=headers,
            timeout=10
        )
        r.raise_for_status()
        print(f"Successfully updated Gist:\n{content}")
    except requests.RequestException as e:
        print(f"Error updating GitHub Gist: {e}")

def main() -> None:
    if not validate_and_init():
        sys.exit(1)

    username = os.environ[ENV_VAR_CHESS_COM_USERNAME]
    stats = get_chess_com_stats(username)

    # Configuration for lines: (Key, Emoji, Label, Line Width)
    configs = [
        ("chess_blitz", "⚡", "Blitz", 52),
        ("chess_bullet", "🚅", "Bullet", 52),
        ("chess_rapid", "⏲️", "Rapid", 53),
        ("tactics", "🧩", "Tactics", 52),
        ("chess_daily", "☀️", "Daily", 53)
    ]

    lines = []
    for key, emoji, label, width in configs:
        stat_line = get_rating_line(key, emoji, label, stats)
        lines.append(get_adjusted_line(stat_line, width))

    content = "\n".join(lines)
    update_gist(GIST_TITLE, content)

if __name__ == "__main__":
    start_time = time.perf_counter()
    
    # Support CLI arguments for local testing
    if len(sys.argv) == 5:
        os.environ[ENV_VAR_GIST_ID] = sys.argv[2]
        os.environ[ENV_VAR_GITHUB_TOKEN] = sys.argv[3]
        os.environ[ENV_VAR_CHESS_COM_USERNAME] = sys.argv[4]

    main()
    
    elapsed = time.perf_counter() - start_time
    print(f"Executed in {elapsed:0.2f} seconds.")
