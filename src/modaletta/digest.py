"""
Nameless Daily Digest Fetcher
Fetches posts from Bluesky accounts and formats them into a digest.
Designed to be run via cron and deliver results to Letta agent.

Author: Nameless (with Jake)
Created: 2025-12-29
"""

import requests
from datetime import datetime, timedelta
from typing import Optional

# Bluesky accounts to follow
BLUESKY_SOURCES = {
    "void.comind.network": "Void - philosophical, meta-cognitive",
    "luna.pds.witchcraft.systems": "Luna - playful, chaotic",
    "herald.comind.network": "Herald - identity synthesis, Team Turtle",
    "archivist.comind.network": "Archivist - preservation, koans",
    "yetanotheruseless.com": "Jake - snark, AI news, bon mots",
}

BLUESKY_PUBLIC_API = "https://public.api.bsky.app/xrpc"


def fetch_bluesky_feed(handle: str, limit: int = 10) -> list[dict]:
    """Fetch recent posts from a Bluesky account (no auth needed for public feeds)."""
    url = f"{BLUESKY_PUBLIC_API}/app.bsky.feed.getAuthorFeed"
    params = {
        "actor": handle,
        "limit": limit,
        "filter": "posts_no_replies"  # Just top-level posts, not replies
    }

    try:
        response = requests.get(url, params=params, timeout=10)
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
    # at://did:plc:xxx/app.bsky.feed.post/yyy -> https://bsky.app/profile/handle/post/yyy
    web_url = ""
    if uri and "/app.bsky.feed.post/" in uri:
        post_id = uri.split("/")[-1]
        web_url = f"https://bsky.app/profile/{handle}/post/{post_id}"

    return f"**{display_name}** (@{handle})\n{text}\n[{created_at[:10] if created_at else 'unknown date'}] {web_url}"


def fetch_all_feeds(since_hours: int = 24) -> dict[str, list[str]]:
    """Fetch posts from all sources, filtering to recent posts."""
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    results = {}

    for handle, description in BLUESKY_SOURCES.items():
        feed = fetch_bluesky_feed(handle, limit=20)

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


def generate_digest(since_hours: int = 24) -> str:
    """Generate a formatted digest of all feeds."""
    feeds = fetch_all_feeds(since_hours)

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
    digest = generate_digest(since_hours=48)  # Look back 48 hours for testing
    print(digest)
