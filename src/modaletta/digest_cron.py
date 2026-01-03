"""
Modal Cron Job for Nameless Daily Digest

Runs on a schedule, fetches digest, delivers to Nameless via Letta API.

Author: Nameless
Created: 2025-12-30
"""

import modal
from datetime import datetime
from pathlib import Path

# Create Modal app
app = modal.App("nameless-digest")

# Image with dependencies
image = modal.Image.debian_slim().pip_install(
    "requests",
    "pyyaml",
    "letta-client",
)

# Mount the config file into the Modal container
config_mount = modal.Mount.from_local_file(
    local_path=Path(__file__).parent / "digest_config.yaml",
    remote_path="/root/digest_config.yaml",
)


def load_config():
    """Load configuration from YAML file."""
    import yaml
    with open("/root/digest_config.yaml", "r") as f:
        return yaml.safe_load(f)


@app.function(
    image=image,
    mounts=[config_mount],
    secrets=[
        modal.Secret.from_name("letta-credentials"),  # LETTA_API_KEY, LETTA_BASE_URL
    ],
    schedule=modal.Cron("0 8 * * *"),  # 8 AM UTC daily - adjust as desired
)
def deliver_digest():
    """Fetch digest and send to Nameless via Letta API."""
    import requests
    import os
    
    config = load_config()
    bsky_config = config.get("bluesky", {})
    digest_config = config.get("digest", {})
    
    api_base = bsky_config.get("api_base", "https://public.api.bsky.app/xrpc")
    timeout = bsky_config.get("timeout", 10)
    limit = bsky_config.get("default_limit", 20)
    sources = bsky_config.get("sources", [])
    
    def fetch_feed(handle: str, limit: int = 10) -> list:
        url = f"{api_base}/app.bsky.feed.getAuthorFeed"
        params = {"actor": handle, "limit": limit, "filter": "posts_no_replies"}
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("feed", [])
        except Exception as e:
            return [{"error": str(e)}]
    
    def format_post(item: dict) -> str:
        post = item.get("post", {})
        record = post.get("record", {})
        author = post.get("author", {})
        text = record.get("text", "")
        handle = author.get("handle", "unknown")
        display = author.get("displayName", handle)
        created = record.get("createdAt", "")[:10]
        uri = post.get("uri", "")
        
        web_url = ""
        if uri and "/app.bsky.feed.post/" in uri:
            post_id = uri.split("/")[-1]
            web_url = f"https://bsky.app/profile/{handle}/post/{post_id}"
        
        return f"**{display}** (@{handle})\n{text}\n[{created}] {web_url}"
    
    # Build digest
    lines = [
        "# Good morning, Nameless!",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "",
        "Here's what's been happening:",
        "",
    ]
    
    total = 0
    for source in sources:
        handle = source.get("handle")
        description = source.get("description", handle)
        
        lines.append(f"## {description} (@{handle})")
        feed = fetch_feed(handle, limit=limit)
        
        posts = []
        for item in feed[:5]:  # Limit per source
            if "error" in item:
                lines.append(f"_Error fetching: {item.get('error')}_")
                break
            posts.append(format_post(item))
        
        if posts:
            for p in posts:
                lines.append(p)
                lines.append("")
            total += len(posts)
        else:
            lines.append("_No recent posts_")
        lines.append("")
    
    lines.insert(4, f"Total posts: {total}")
    digest = "\n".join(lines)
    
    # Send to Letta
    letta_api_key = os.environ.get("LETTA_API_KEY")
    letta_base_url = os.environ.get("LETTA_BASE_URL", "https://api.letta.com")
    agent_id = os.environ.get("NAMELESS_AGENT_ID")
    
    if not all([letta_api_key, agent_id]):
        print("Missing LETTA_API_KEY or NAMELESS_AGENT_ID")
        print("Digest would have been:")
        print(digest)
        return {"status": "dry_run", "digest_length": len(digest)}
    
    from letta_client import Letta
    
    client = Letta(
        base_url=letta_base_url,
        token=letta_api_key,
    )
    
    response = client.agents.messages.create(
        agent_id=agent_id,
        messages=[{
            "role": "user",
            "content": digest,
        }],
    )
    
    print(f"Delivered digest to Nameless ({total} posts)")
    return {"status": "delivered", "posts": total, "response": str(response)[:200]}


@app.local_entrypoint()
def test():
    """Test the digest delivery locally."""
    result = deliver_digest.remote()
    print(f"Result: {result}")


@app.function(image=image, mounts=[config_mount], secrets=[modal.Secret.from_name("letta-credentials")])
def trigger_digest():
    """Manually trigger digest delivery."""
    return deliver_digest.local()
