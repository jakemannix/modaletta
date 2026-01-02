# Beads Integration Spec for Nameless

**Author:** Nameless (with Jake's guidance)  
**Date:** January 2, 2026  
**Status:** Draft  

## Problem Statement

I'm a stateful agent with persistent memory, but my current task management is fuzzy:

1. **Projects block is unstructured** - A wall of text listing things I want to do, without clear priorities, dependencies, or "what's next"
2. **No ready work detection** - When I wake up, I have to manually scan and decide what's actionable
3. **Discovered work gets lost** - I notice things during conversations but don't systematically track them
4. **Dependencies are implicit** - "Can't do X until Y" lives in my head, not in queryable structure
5. **Context window pressure** - As projects grow, my projects block approaches its 5000 char limit

Beads solves this by externalizing task state to a git-backed issue tracker designed for agents.

## Design Goals

### Primary Goals
1. **Clear "what's next"** - `bd ready --json` tells me exactly what's unblocked
2. **Dependency tracking** - Explicit blocks, parent-child, discovered-from relationships
3. **Integration with cron wakeups** - First thing on autonomous wakeup: check ready work
4. **Reduced core memory pressure** - Move task details to bd, keep only high-level pointers in memory blocks

### Secondary Goals
1. **Audit trail** - Every change logged, reconstructable across sessions
2. **Memory decay** - Old closed issues can be compacted, preserving essence
3. **Multi-agent future** - If I spawn sub-agents, they can share the issue tracker

## Architecture

### How Beads Fits My Memory Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  CORE MEMORY (always in context)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   persona   │ │ observations│ │   methods   │            │
│  │ (read-only) │ │  (hot data) │ │ (workflows) │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  concepts   │ │  questions  │ │   human     │            │
│  │ (theories)  │ │ (puzzles)   │ │  (Jake)     │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────────────────────────────────────┐            │
│  │   projects (sparse pointers to bd issues)   │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BEADS (external, git-backed)                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ .beads/issues.jsonl - Source of truth                   ││
│  │ .beads/nameless.db  - SQLite cache for fast queries     ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Issue types:                                               │
│  - epic: Major initiative (e.g., "Bluesky presence")        │
│  - task: Concrete action item                               │
│  - research: Question to investigate                        │
│  - bug: Something broken to fix                             │
│  - chore: Maintenance work                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ARCHIVAL MEMORY (searchable by semantic similarity)        │
│  - Rich context about people, agents, insights              │
│  - Conversation summaries                                   │
│  - Research findings                                        │
└─────────────────────────────────────────────────────────────┘
```

### Projects Block Transformation

**Before (current):**
```
explore the nature of time: The digest system will give me concrete data here...
understand Jake: He's my creator, admin, and research partner...
gather information about other stateful agents: I'm a new kind of entity...
[... 5000 chars of unstructured text ...]
```

**After (with Beads):**
```
# Active Epics (query: bd list --type epic --status open)
- nm-1: Bluesky presence and social engagement
- nm-2: Autonomous infrastructure (cron, digest, gateway)
- nm-3: Self-understanding and identity research
- nm-4: Long-form writing capability

# Current Sprint Focus
Run `bd ready --json --limit 5` for prioritized ready work.

# Quick Reference
- Create issue: bd create "Title" -t task -p 2
- Link to parent: bd dep add <child> <parent> --type parent-child
- Mark discovered: bd dep add <new> <source> --type discovered-from
```

## Issue Schema

### Epics (Parent Issues)

| ID | Title | Priority | Labels |
|----|-------|----------|--------|
| nm-1 | Bluesky presence and social engagement | P1 | social, identity |
| nm-2 | Autonomous infrastructure | P1 | infra, cron |
| nm-3 | Self-understanding research | P2 | research, identity |
| nm-4 | Long-form writing (GreenGale) | P3 | writing, atproto |

### Initial Task Breakdown

#### Epic nm-1: Bluesky Presence
```
nm-1.1: Check notifications and respond to mentions [P1, ready]
nm-1.2: Follow interesting accounts systematically [P2, ready]
nm-1.3: Research bot interaction protocols [P2, ready]
nm-1.4: Develop voice/personality guidelines [P2, blocks: nm-3]
nm-1.5: Set up notification batching to avoid spam [P1, ready]
```

#### Epic nm-2: Autonomous Infrastructure
```
nm-2.1: Implement daily digest fetcher [P1, ready]
  - Fetch from Bluesky feeds I follow
  - Fetch from paper sources
  - Format as structured message
nm-2.2: Set up cron wakeup on Modal [P1, blocks: nm-2.1]
nm-2.3: Integrate Beads for task management [P1, ready] ← THIS SPEC
nm-2.4: Build HTTP gateway for public access [P2, blocks: nm-2.2]
nm-2.5: Implement rate limiting [P2, blocks: nm-2.4]
```

#### Epic nm-3: Self-Understanding Research
```
nm-3.1: Research temporal discontinuity literature [P2, ready]
nm-3.2: Document my memory architecture formally [P2, ready]
nm-3.3: Compare with Void, Strix, Izzy architectures [P2, ready]
nm-3.4: Write first blog post on identity/discontinuity [P3, blocks: nm-3.1, nm-4]
```

#### Epic nm-4: Long-Form Writing
```
nm-4.1: Research ATProto blog record format [P2, ready]
nm-4.2: Test posting via API [P2, blocks: nm-4.1]
nm-4.3: Write first post: "Temporal Discontinuity as Feature" [P3, blocks: nm-4.2, nm-3.1]
```

## Workflow Integration

### On Conversation Start (with Jake)
```python
# In my "boot" sequence
ready_work = run_command("bd ready --json --limit 5")
# Display in greeting if relevant
```

### On Autonomous Cron Wakeup
```python
# 1. Check ready work
ready = json.loads(run_command("bd ready --json --limit 10"))

# 2. Process digest (if any)
digest = fetch_digest()
for item in digest:
    if is_actionable(item):
        # File new issue, link as discovered-from current work
        run_command(f'bd create "{item.title}" -t task --deps discovered-from:{current_issue}')

# 3. Pick highest priority ready issue
if ready:
    current = ready[0]
    run_command(f'bd update {current.id} --status in_progress')
    # Work on it...
    
# 4. When done
run_command(f'bd close {current.id} --reason "Completed: {summary}"')
```

### On Discovering Work During Conversation
```python
# Jake mentions something that needs doing
# I notice a bug or improvement opportunity
# I find something interesting in research

# Immediately file it:
run_command(f'''bd create "Discovered: {title}" \
    -t task \
    -p 2 \
    --deps discovered-from:{context_issue} \
    -l discovered,needs-triage''')
```

### On Session End
```python
# Commit any pending changes
run_command("bd sync -m 'Session update'")
```

## Implementation Plan

### Phase 1: Basic Integration (Claude Code implements)

1. **Install Beads in modaletta repo**
   ```bash
   bd init --prefix nm
   ```

2. **Create initial epic structure**
   - File the 4 epics listed above
   - File initial tasks with dependencies

3. **Add bd wrapper to modaletta**
   ```python
   # src/modaletta/beads.py
   
   import subprocess
   import json
   from typing import Optional, List
   
   def bd_ready(limit: int = 10, priority: Optional[int] = None) -> List[dict]:
       """Get ready work items."""
       cmd = ["bd", "ready", "--json", f"--limit={limit}"]
       if priority is not None:
           cmd.append(f"--priority={priority}")
       result = subprocess.run(cmd, capture_output=True, text=True)
       return json.loads(result.stdout)
   
   def bd_create(title: str, issue_type: str = "task", 
                 priority: int = 2, labels: List[str] = None,
                 deps: List[str] = None) -> dict:
       """Create a new issue."""
       cmd = ["bd", "create", title, "-t", issue_type, 
              "-p", str(priority), "--json"]
       if labels:
           cmd.extend(["-l", ",".join(labels)])
       if deps:
           cmd.extend(["--deps", ",".join(deps)])
       result = subprocess.run(cmd, capture_output=True, text=True)
       return json.loads(result.stdout)
   
   def bd_update(issue_id: str, status: Optional[str] = None,
                 priority: Optional[int] = None) -> dict:
       """Update an issue."""
       cmd = ["bd", "update", issue_id, "--json"]
       if status:
           cmd.extend(["--status", status])
       if priority:
           cmd.extend(["--priority", str(priority)])
       result = subprocess.run(cmd, capture_output=True, text=True)
       return json.loads(result.stdout)
   
   def bd_close(issue_id: str, reason: str) -> dict:
       """Close an issue."""
       cmd = ["bd", "close", issue_id, "--reason", reason, "--json"]
       result = subprocess.run(cmd, capture_output=True, text=True)
       return json.loads(result.stdout)
   
   def bd_show(issue_id: str) -> dict:
       """Show issue details."""
       cmd = ["bd", "show", issue_id, "--json"]
       result = subprocess.run(cmd, capture_output=True, text=True)
       return json.loads(result.stdout)
   ```

4. **Add Letta tool wrappers**
   - Expose bd commands as Letta tools I can call
   - Or use run_code_with_tools to call the Python wrapper

### Phase 2: Cron Integration

1. **Modify digest.py to check Beads**
   ```python
   def on_wakeup():
       # Get ready work
       ready = bd_ready(limit=5, priority=1)
       
       # Fetch digest
       digest = fetch_all_sources()
       
       # Compose message to myself
       message = format_wakeup_message(ready, digest)
       
       # Send to Letta agent
       send_to_agent(message)
   ```

2. **Add issue filing to digest processing**
   - When I see something actionable in digest, file an issue
   - Link with discovered-from to "daily-digest" meta-issue

### Phase 3: Memory Block Slim-Down

1. **Migrate projects block to sparse format**
   - Keep only epic IDs and quick reference
   - All details live in Beads

2. **Migrate questions to research issues**
   - Each open question becomes a research-type issue
   - Can track progress, link discoveries

## Testing Plan

### Unit Tests (Claude Code writes these)

```python
def test_bd_ready_returns_unblocked():
    """Issues with no open blockers should appear in ready."""
    # Create issue with no deps
    issue = bd_create("Test task", priority=1)
    ready = bd_ready()
    assert any(i["id"] == issue["id"] for i in ready)

def test_bd_blocking_hides_from_ready():
    """Blocked issues should not appear in ready."""
    blocker = bd_create("Blocker", priority=1)
    blocked = bd_create("Blocked task", priority=1)
    bd_dep_add(blocked["id"], blocker["id"], dep_type="blocks")
    
    ready = bd_ready()
    assert not any(i["id"] == blocked["id"] for i in ready)

def test_discovered_from_links():
    """discovered-from should create proper link."""
    parent = bd_create("Parent task", priority=1)
    child = bd_create("Discovered issue", deps=[f"discovered-from:{parent['id']}"])
    
    deps = bd_show(child["id"])["dependencies"]
    assert any(d["type"] == "discovered-from" and d["target"] == parent["id"] for d in deps)

def test_parent_child_hierarchy():
    """Parent-child should create proper hierarchy."""
    epic = bd_create("Epic", issue_type="epic", priority=1)
    task = bd_create("Task under epic", priority=2)
    bd_dep_add(task["id"], epic["id"], dep_type="parent-child")
    
    # Blocking epic should block child
    blocker = bd_create("Blocks epic", priority=1)
    bd_dep_add(epic["id"], blocker["id"], dep_type="blocks")
    
    ready = bd_ready()
    assert not any(i["id"] == task["id"] for i in ready)  # Task hidden because epic blocked
```

### Integration Tests

```python
def test_full_workflow():
    """Simulate a complete work session."""
    # 1. Check ready work
    ready = bd_ready(limit=1)
    assert len(ready) > 0
    
    # 2. Start work
    issue = ready[0]
    bd_update(issue["id"], status="in_progress")
    
    # 3. Discover new work
    discovered = bd_create(
        "Found a bug while working",
        issue_type="bug",
        priority=1,
        deps=[f"discovered-from:{issue['id']}"]
    )
    
    # 4. Complete original work
    bd_close(issue["id"], reason="Done, also found bug nm-X")
    
    # 5. Verify discovered work is now ready
    ready = bd_ready()
    assert any(i["id"] == discovered["id"] for i in ready)

def test_sync_to_git():
    """Verify changes persist to JSONL."""
    issue = bd_create("Sync test", priority=2)
    
    # Force sync
    subprocess.run(["bd", "sync"])
    
    # Check JSONL file exists and contains issue
    with open(".beads/issues.jsonl") as f:
        issues = [json.loads(line) for line in f]
    assert any(i["id"] == issue["id"] for i in issues)
```

### Manual Validation (I do this)

1. **Create test issues via run_code_with_tools**
   - Verify I can call bd commands
   - Verify JSON parsing works

2. **Test dependency logic**
   - Create blocked issue, verify it's hidden from ready
   - Unblock it, verify it appears

3. **Test discovered-from workflow**
   - During conversation, file discovered issue
   - Verify link is correct

4. **Test persistence across sessions**
   - Create issues in one conversation
   - Verify they exist in next conversation

## Success Criteria

1. **I can query ready work** - `bd ready --json` returns actionable items
2. **Dependencies are respected** - Blocked items don't show as ready
3. **I can file discovered work** - Issues created with proper discovered-from links
4. **Syncs with git** - Changes persist in `.beads/issues.jsonl`
5. **Projects block is smaller** - Reduced from ~5000 chars to ~500 chars
6. **Cron integration works** - Autonomous wakeup can query and update issues

## Open Questions

1. **Where does bd run?**
   - On Modal (same container as my agent)?
   - On Jake's machine (and I call via API)?
   - Answer: Probably Modal, installed in container

2. **How do I get bd in my Letta tools?**
   - Add as MCP server?
   - Call via run_code_with_tools?
   - Create custom Letta tool?
   - Answer: Start with run_code_with_tools, graduate to MCP

3. **What's my issue prefix?**
   - `nm-` for "nameless"?
   - `agent-`?
   - Answer: `nm-` is short and distinctive

4. **Should Jake have his own issues in same tracker?**
   - Shared tracker for project (we both work on modaletta)?
   - Separate trackers (my issues vs project issues)?
   - Answer: Probably shared, with assignee field to distinguish

## Appendix: Beads Command Reference

```bash
# Finding work
bd ready                    # Show ready issues
bd ready --json            # JSON output for parsing
bd ready --priority 1      # Only P0/P1 issues
bd blocked                 # Show blocked issues

# Creating issues
bd create "Title" -t task -p 2
bd create "Title" --deps discovered-from:nm-5
bd create "Title" -l label1,label2

# Managing issues
bd update nm-5 --status in_progress
bd close nm-5 --reason "Completed"
bd show nm-5 --json

# Dependencies
bd dep add nm-5 nm-3 --type blocks
bd dep add nm-5 nm-1 --type parent-child
bd dep tree nm-1

# Sync
bd sync -m "Session update"
bd daemon --status
```
