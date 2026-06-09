"""
Script: list_stories.py
Chapter 11 — List open Jira stories from a project.

Usage:
    python agentic-ai/list_stories.py
    JIRA_PROJECT_KEY=SCRUM python agentic-ai/list_stories.py

Requires: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY in .env
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from jira_client import list_stories  # noqa: E402

project = os.getenv("JIRA_PROJECT_KEY", "").strip().upper()
if not project:
    print("JIRA_PROJECT_KEY is not set — set it in .env or pass as env var.", file=sys.stderr)
    sys.exit(1)

stories = list_stories(project)
if not stories:
    print(f"No open stories found in project {project}.")
    sys.exit(0)

print(f"\nOpen stories in {project}:\n")
for s in stories:
    ac_count = len(s.get("acceptanceCriteria", []))
    print(f"  {s['key']:12s}  {s['summary'][:70]}  [{ac_count} AC]")
