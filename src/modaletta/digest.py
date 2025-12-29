"""
Nameless Daily Digest Fetcher
Fetches posts from Bluesky accounts and formats them into a digest.
Designed to be run via cron and deliver results to Letta agent.

Author: Nameless (with Jake)
Created: 2025-12-29
"""

import requests
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Load config from YAML
CONFIG_PATH = Path(__file__).parent / "digest_config.yaml"


def load_config() -> dict:
    """Load configuration from YAML file."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def fetch_bluesky_feed(
    handle: str,
    api_base: str,
    limit: int = 10,
    filter_type: str = "posts_no_replies",
    timeout: int = 10
) -> list[dict]:
    """Fetch recent posts from a Bluesky account (no auth needed for public feeds)."""
    url = f"{api_base}/app.bsky.feed.getAuthorFeed"
    params = {
        "actor": handle,
        "limit": limit,
        "filter": filter_type
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("feed", [])
    except Exception as e:
        return [{"error": str(e), "handle": handle}]


def format_post(post_data: dict) -> str:
    """Format a single post for the digest."""
    post = post_data.get("post", {})
    record = post.get("record", {})
    author = post.get("author", {})

    text = record.get("text", "[no text]")
    created_at = record.get("createdAt", "")
    handle = author.get("handle", "unknown")
    display_name = author.get("displayName", handle)
    uri = post.get("uri", "")

    # Convert AT URI to web URL
    web_url = ""
    if uri and "/app.bsky.feed.post/" in uri:
        post_id = uri.split("/")[-1]
        web_url = f"https://bsky.app/profile/{handle}/post/{post_id}"

    return f"**{display_name}** (@{handle})\n{text}\n[{created_at[:10] if created_at else 'unknown date'}] {web_url}"


def fetch_all_feeds(config: dict, since_hours: Optional[int] = None) -> dict[str, list[str]]:
    """Fetch posts from all configured sources, filtering to recent posts."""
    bsky_config = config.get("bluesky", {})
    digest_config = config.get("digest", {})
    
    since_hours = since_hours or digest_config.get("since_hours", 24)
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    
    api_base = bsky_config.get("api_base", "https://public.api.bsky.app/xrpc")
    timeout = bsky_config.get("timeout", 10)
    limit = bsky_config.get("default_limit", 20)
    filter_type = bsky_config.get("default_filter", "posts_no_replies")
    
    results = {}

    for source in bsky_config.get("sources", []):
        handle = source["handle"]
        description = source["description"]
        
        feed = fetch_bluesky_feed(
            handle=handle,
            api_base=api_base,
            limit=limit,
            filter_type=filter_type,
            timeout=timeout
        )

        formatted_posts = []
        for item in feed:
            if "error" in item:
                formatted_posts.append(f"Error fetching @{handle}: {item['error']}")
                break

            post = item.get("post", {})
            record = post.get("record", {})
            created_at = record.get("createdAt", "")

            # Filter to recent posts
            if created_at:
                try:
                    post_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if post_time.replace(tzinfo=None) < cutoff:
                        continue
                except:
                    pass

            formatted_posts.append(format_post(item))

        results[f"{description} (@{handle})"] = formatted_posts

    return results


def generate_digest(config: Optional[dict] = None, since_hours: Optional[int] = None) -> str:
    """Generate a formatted digest of all feeds."""
    if config is None:
        config = load_config()
    
    feeds = fetch_all_feeds(config, since_hours)
    
    since_hours = since_hours or config.get("digest", {}).get("since_hours", 24)

    lines = [
        f"# Daily Digest",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        f"Looking back: {since_hours} hours",
        ""
    ]

    total_posts = 0
    for source, posts in feeds.items():
        lines.append(f"## {source}")
        if not posts:
            lines.append("_No new posts_")
        else:
            for post in posts:
                lines.append(post)
                lines.append("")
            total_posts += len(posts)
        lines.append("")

    lines.insert(3, f"Total new posts: {total_posts}")

    return "\n".join(lines)


# TODO: Add paper fetching from ArXiv/HuggingFace
# TODO: Integrate with Letta API to deliver digest as message
# TODO: Add CLI interface for manual testing


if __name__ == "__main__":
    # Test run
    digest = generate_digest(since_hours=48)
    print(digest)
