"""
Module: jira_client.py
Chapter 11 — Smart Self-Healing + Real Jira Integration

A single reusable Jira REST API client used by all agentic scripts.
Supports both real Jira (when credentials are set in .env) and a graceful
dry-run mode (prints actions to stdout) when credentials are absent.

Operations:
  fetch_story(key)                      — get story + acceptance criteria
  list_stories(project_key, status)     — list issues from a Jira project
  post_comment(key, body)               — post plain-text comment to an issue
  create_bug(summary, description,      — create a Bug issue, optionally linked
             parent_key, labels)          to a parent story
  upload_file(key, file_path)           — attach any file to an issue
  transition_issue(key, status_name)    — move issue to a workflow status

Required .env vars (for real Jira):
  JIRA_BASE_URL    e.g. https://yourcompany.atlassian.net
  JIRA_EMAIL       your Jira account email
  JIRA_API_TOKEN   API token from id.atlassian.com
  JIRA_PROJECT_KEY e.g. SCRUM  (used as default project for create_bug)
"""

import base64
import json
import os
import ssl
import sys
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


# ─── Credentials ─────────────────────────────────────────────────────────────

def _creds() -> tuple[str, str, str]:
    """Return (base_url, email, token). Raises EnvironmentError if not set."""
    url   = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    return url, email, token


def has_credentials() -> bool:
    url, email, token = _creds()
    return bool(url and email and token)


def _auth_header() -> str:
    _, email, token = _creds()
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def _request(method: str, path: str, body: dict | None = None,
             extra_headers: dict | None = None) -> Any:
    """Make an authenticated Jira REST API request. Returns parsed JSON."""
    base_url, _, _ = _creds()
    url     = f"{base_url}/rest/api/3/{path.lstrip('/')}"
    payload = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": _auth_header(),
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20, context=_ssl_ctx()) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _log(msg: str) -> None:
    print(f"[jira] {msg}")


# ─── ADF helpers ─────────────────────────────────────────────────────────────

def _adf_doc(text: str) -> dict:
    """Wrap plain text in Atlassian Document Format (required by Jira REST v3)."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def _adf_to_text(node: dict) -> str:
    """Recursively extract plain text from an ADF node."""
    if not node:
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    return " ".join(_adf_to_text(c) for c in node.get("content", []))


# ─── fetch_story ─────────────────────────────────────────────────────────────

def fetch_story(key: str) -> dict:
    """
    Fetch a Jira story by key.
    Falls back to agentic-ai/data/jira-story.{key}.json if it exists.

    Returns a normalised dict:
      { key, summary, description, acceptanceCriteria: [...], testCaseLink }
    """
    local_path = Path(__file__).parent / "data" / f"jira-story.{key}.json"
    if local_path.exists():
        _log(f"Using local mock: {local_path.name}")
        data = json.loads(local_path.read_text(encoding="utf-8"))
        # Local mock already in normalised shape
        if "acceptanceCriteria" in data:
            return data
        # Raw Jira API shape stored locally
        return _normalise(data)

    if not has_credentials():
        raise EnvironmentError(
            f'No local mock for "{key}" and Jira credentials are not set.\n'
            f"Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env\n"
            f"or create agentic-ai/data/jira-story.{key}.json"
        )

    _log(f"Fetching {key} from Jira API...")
    data = _request("GET", f"issue/{key}")
    return _normalise(data)


def _extract_ac_from_text(text: str) -> list[str]:
    """
    Parse acceptance criteria from a plain-text block.
    Handles three formats:
      1. Gherkin  — lines/blocks starting with "Scenario:"
      2. Numbered — lines starting with "AC1:", "AC2:", etc.
      3. Fallback — return the whole text as a single AC
    """
    import re
    text = text.strip()
    if not text:
        return []

    # Format 1: Gherkin scenarios
    if "Scenario:" in text:
        parts = re.split(r"(?=Scenario:)", text)
        return [p.strip() for p in parts if p.strip().startswith("Scenario:")]

    # Format 2: AC1: / AC2: numbered lines
    if re.search(r"AC\d+:", text, re.IGNORECASE):
        return [
            line.strip()
            for line in re.split(r"[\n.]+", text)
            if re.match(r"^AC\d+:", line.strip(), re.IGNORECASE)
        ]

    # Fallback: treat the whole block as one AC
    return [text[:600]]


def _normalise(data: dict) -> dict:
    """
    Convert a raw Jira API issue to the normalised shape used by all scripts:
        { key, summary, description, acceptanceCriteria: [str, ...] }

    AC lookup order (stops at the first source that yields results):
      1. Dedicated Jira custom fields:
           customfield_10016 (Story Points — skip)
           customfield_10014 (Epic Link — skip)
           customfield_10500 (common "Acceptance Criteria" field in many Jira configs)
           customfield_10501, customfield_10502, customfield_10503 (other common AC fields)
           Any field whose string value contains "Scenario:" or "AC1:"
      2. Section in description after "Acceptance Criteria:" heading
      3. Full description text
    """
    import re
    fields    = data.get("fields", {})
    full_desc = _adf_to_text(fields.get("description") or {})

    # ── 1. Check dedicated custom fields ──────────────────────────────────────
    # Well-known AC custom field IDs (add yours here if different)
    AC_CUSTOM_FIELDS = [
        "customfield_10500",  # "Acceptance Criteria" — common in Jira Software
        "customfield_10501",
        "customfield_10502",
        "customfield_10503",
        "customfield_10300",
        "customfield_10301",
    ]
    ac_lines: list[str] = []

    for cf in AC_CUSTOM_FIELDS:
        raw_cf = fields.get(cf)
        if not raw_cf:
            continue
        # Could be ADF (dict), plain string, or list of strings
        if isinstance(raw_cf, dict):
            cf_text = _adf_to_text(raw_cf).strip()
        elif isinstance(raw_cf, list):
            cf_text = "\n".join(str(x) for x in raw_cf).strip()
        else:
            cf_text = str(raw_cf).strip()
        if cf_text:
            ac_lines = _extract_ac_from_text(cf_text)
            if ac_lines:
                break  # found in a dedicated field — use it

    # ── 2. Scan ALL custom fields for any that look like AC text ──────────────
    if not ac_lines:
        for k, v in fields.items():
            if not k.startswith("customfield") or not v:
                continue
            if isinstance(v, dict):
                cf_text = _adf_to_text(v).strip()
            elif isinstance(v, str):
                cf_text = v.strip()
            else:
                continue
            if re.search(r"Scenario:|AC\d+:", cf_text, re.IGNORECASE):
                ac_lines = _extract_ac_from_text(cf_text)
                if ac_lines:
                    break

    # ── 3. Fall back to description ───────────────────────────────────────────
    if not ac_lines:
        # If description has an "Acceptance Criteria:" heading, use only that section
        if "Acceptance Criteria:" in full_desc:
            ac_section = full_desc.split("Acceptance Criteria:", 1)[1]
        else:
            ac_section = full_desc
        ac_lines = _extract_ac_from_text(ac_section)

    # Short description = user story part only (before any AC heading)
    short_desc = (
        full_desc.split("Acceptance Criteria:")[0].strip()
        if "Acceptance Criteria:" in full_desc
        else full_desc[:400]
    )

    return {
        "key":                data["key"],
        "summary":            fields.get("summary", ""),
        "description":        short_desc,
        "acceptanceCriteria": ac_lines,
        "testCaseLink":       fields.get("customfield_10016", ""),
    }


# ─── list_stories ─────────────────────────────────────────────────────────────

def list_stories(project_key: str | None = None,
                 status: str = "To Do",
                 max_results: int = 20) -> list[dict]:
    """
    List Jira issues from a project filtered by status.
    Returns a list of normalised story dicts.

    Args:
        project_key: Jira project key, e.g. "SCRUM". Falls back to
                     JIRA_PROJECT_KEY env var.
        status:      Issue status to filter on (default "To Do").
        max_results: Maximum issues to return (default 20).
    """
    proj = project_key or os.getenv("JIRA_PROJECT_KEY", "")
    if not proj:
        raise EnvironmentError(
            "project_key argument or JIRA_PROJECT_KEY env var is required."
        )

    if not has_credentials():
        _log(f"[dry-run] Would list '{status}' stories from project {proj}")
        return []

    jql  = f'project = "{proj}" AND status = "{status}" ORDER BY created DESC'
    _log(f"Querying Jira: {jql}")
    resp = _request("GET", f"search?jql={urllib.request.quote(jql)}&maxResults={max_results}&fields=summary,description,status")
    issues = resp.get("issues", [])
    _log(f"Found {len(issues)} issue(s) with status '{status}' in {proj}")
    return [_normalise(issue) for issue in issues]


# ─── post_comment ─────────────────────────────────────────────────────────────

def post_comment(key: str, body: str) -> None:
    """
    Post a plain-text comment to a Jira issue.
    Dry-runs (prints) when credentials are not set.

    Args:
        key:  Jira issue key, e.g. "SCRUM-1"
        body: Plain text comment body
    """
    if not has_credentials():
        _log(f"[dry-run] Comment on {key}:\n{body}\n")
        return

    _log(f"Posting comment to {key}...")
    result = _request("POST", f"issue/{key}/comment", {"body": _adf_doc(body)})
    _log(f"Comment posted → id={result.get('id')}")


# ─── create_bug ──────────────────────────────────────────────────────────────

def create_bug(summary: str,
               description: str,
               parent_key: str | None = None,
               labels: list[str] | None = None) -> str | None:
    """
    Create a Bug issue in Jira, optionally linked to a parent story.
    Returns the new issue key (e.g. "SCRUM-42"), or None on dry-run.

    Args:
        summary:     Bug title
        description: Detailed bug description (plain text)
        parent_key:  Parent story key to link with "is caused by"
        labels:      List of labels to apply, e.g. ["self-heal", "automated"]
    """
    proj = os.getenv("JIRA_PROJECT_KEY", "")
    if not proj and parent_key:
        proj = parent_key.split("-")[0]

    if not has_credentials():
        _log(f"[dry-run] Would create Bug in {proj}: {summary}")
        if parent_key:
            _log(f"[dry-run] Linked to: {parent_key}")
        return None

    if not proj:
        _log("JIRA_PROJECT_KEY not set — skipping bug creation.")
        return None

    payload: dict = {
        "fields": {
            "project":     {"key": proj},
            "issuetype":   {"name": "Bug"},
            "summary":     summary,
            "description": _adf_doc(description),
            "labels":      labels or ["automated", "self-heal"],
        }
    }

    _log(f"Creating Bug in project {proj}: {summary}")
    result = _request("POST", "issue", payload)
    new_key = result.get("key", "")
    _log(f"Bug created → {new_key}")

    # Link to parent story
    if parent_key and new_key:
        try:
            _request("POST", "issueLink", {
                "type":          {"name": "Cause"},
                "inwardIssue":   {"key": new_key},
                "outwardIssue":  {"key": parent_key},
            })
            _log(f"Linked {new_key} → {parent_key}")
        except Exception as exc:
            _log(f"Warning: could not link issues ({exc})")

    return new_key


# ─── upload_file ─────────────────────────────────────────────────────────────

def upload_file(key: str, file_path: str | Path) -> None:
    """
    Attach a file to a Jira issue (screenshot, HTML report, JSON results, etc).
    Dry-runs when credentials are not set.

    Args:
        key:       Jira issue key, e.g. "SCRUM-1"
        file_path: Absolute or workspace-relative path to the file
    """
    path = Path(file_path)
    if not path.exists():
        _log(f"Warning: file not found, skipping upload — {path}")
        return

    if not has_credentials():
        _log(f"[dry-run] Would attach {path.name} to {key}")
        return

    base_url, _, _ = _creds()
    url      = f"{base_url}/rest/api/3/issue/{key}/attachments"
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization":     _auth_header(),
            "X-Atlassian-Token": "no-check",
            "Content-Type":      f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx()) as resp:
            resp.read()
        _log(f"Attached {path.name} to {key}")
    except urllib.error.HTTPError as exc:
        _log(f"Attachment failed: {exc.code} {exc.reason}")


# ─── transition_issue ────────────────────────────────────────────────────────

def transition_issue(key: str, status_name: str) -> None:
    """
    Move a Jira issue to a named workflow status (e.g. "In Progress", "Done").
    Dry-runs when credentials are not set.

    Args:
        key:         Jira issue key
        status_name: Target status name (case-insensitive match)
    """
    if not has_credentials():
        _log(f"[dry-run] Would transition {key} → '{status_name}'")
        return

    transitions = _request("GET", f"issue/{key}/transitions")
    match = next(
        (t for t in transitions.get("transitions", [])
         if t["name"].lower() == status_name.lower()),
        None,
    )
    if not match:
        available = [t["name"] for t in transitions.get("transitions", [])]
        _log(f"Transition '{status_name}' not found for {key}. Available: {available}")
        return

    _request("POST", f"issue/{key}/transitions", {"transition": {"id": match["id"]}})
    _log(f"Transitioned {key} → '{status_name}'")


# ─── CLI smoke test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "LOGIN-123"
    print(f"\n── fetch_story({key}) ──")
    story = fetch_story(key)
    print(json.dumps(story, indent=2))

    print(f"\n── post_comment({key}) [dry-run if no creds] ──")
    post_comment(key, f"🤖 jira_client.py smoke test — story fetched OK for {key}")

    print("\n── has_credentials() ──")
    print(f"  Real Jira: {has_credentials()}")
