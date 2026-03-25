#!/usr/bin/env python3
"""
Waymo Reddit Code Scanner
Scans the r/waymo Mega Invite Referral Codes thread for new codes
posted in the last 5 hours and saves them to a timestamped .txt file.

NO Reddit API credentials needed — uses Reddit's public JSON endpoint.
Just run:  python3 waymo_code_scanner.py
"""

import re
import sys
import time
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

MOUNTAIN_TZ = ZoneInfo("America/Denver")  # Handles MST (UTC-7) and MDT (UTC-6) automatically

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
POST_ID    = "1qw8cgh"
SUBREDDIT  = "waymo"
HOURS_BACK = 5
OUTPUT_DIR = Path(__file__).parent

# Reddit requires a descriptive User-Agent for public JSON requests
USER_AGENT = "waymo-code-scanner/2.0 (personal use; read-only)"

BASE_URL = (
    f"https://www.reddit.com/r/{SUBREDDIT}/comments/{POST_ID}/.json"
    "?limit=500&sort=new"
)


# ─────────────────────────────────────────────
#  CODE EXTRACTION
# ─────────────────────────────────────────────
PATTERNS = [
    # Waymo invite/referral URLs (full or partial)
    r'https?://(?:www\.)?(?:one\.)?waymo\.com/\S+',
    r'one\.waymo\.com/\S+',
    # Generic short invite-style codes: 6–20 uppercase alphanumeric chars
    r'\b[A-Z0-9]{6,20}\b',
]

STOPWORDS = {
    "THE","AND","FOR","THIS","THAT","WITH","FROM","HAVE","WILL","WAYMO",
    "CODE","CODES","INVITE","REFERRAL","COMMENT","POSTED","THREAD","POST",
    "REDDIT","ANYONE","PLEASE","THANKS","STILL","VALID","MINE","USED",
    "WORK","DOES","HERE","SHARE","FREE","JUST","ALSO","ONLY","YOUR","THEIR",
    "HTTPS","HTTP","WERE","THEY","BEEN","SOME","MORE","WHEN","INTO","WHAT",
}

def extract_codes(text: str) -> list[str]:
    found = []
    for pat in PATTERNS:
        for m in re.findall(pat, text, re.IGNORECASE):
            if re.fullmatch(r'[A-Z0-9]{6,20}', m, re.IGNORECASE):
                if m.upper() in STOPWORDS:
                    continue
            found.append(m)
    # Deduplicate (case-insensitive)
    seen, result = set(), []
    for c in found:
        if c.lower() not in seen:
            seen.add(c.lower())
            result.append(c)
    return result


# ─────────────────────────────────────────────
#  FETCH ALL COMMENTS (handles pagination)
# ─────────────────────────────────────────────
def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def flatten_comments(comment_list: list, results: list):
    """Recursively walk the comment tree and collect all comment objects."""
    for item in comment_list:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        data = item.get("data", {})

        if kind == "t1":  # regular comment
            results.append(data)
            replies = data.get("replies")
            if isinstance(replies, dict):
                flatten_comments(
                    replies.get("data", {}).get("children", []), results
                )

        elif kind == "more":
            # "load more" stubs — fetch them if they have IDs
            ids = data.get("children", [])
            if ids:
                fetch_more_comments(ids, results)

        elif kind == "Listing":
            flatten_comments(data.get("children", []), results)


def fetch_more_comments(ids: list[str], results: list, chunk_size: int = 100):
    """Fetch additional comment stubs in batches via the morechildren endpoint."""
    for i in range(0, len(ids), chunk_size):
        batch = ids[i : i + chunk_size]
        url = (
            "https://www.reddit.com/api/morechildren.json"
            f"?link_id=t3_{POST_ID}&children={','.join(batch)}&api_type=json"
        )
        try:
            time.sleep(1)  # be polite to Reddit's servers
            data = fetch_json(url)
            things = (
                data.get("json", {}).get("data", {}).get("things", [])
            )
            for thing in things:
                if thing.get("kind") == "t1":
                    results.append(thing["data"])
        except Exception as e:
            print(f"  [WARN] Could not fetch comment batch: {e}")


# ─────────────────────────────────────────────
#  MAIN SCAN LOGIC
# ─────────────────────────────────────────────
def scan_thread() -> list[dict]:
    print(f"[INFO] Fetching thread from Reddit (no credentials needed)...")
    try:
        raw = fetch_json(BASE_URL)
    except Exception as e:
        print(f"[ERROR] Could not reach Reddit: {e}")
        sys.exit(1)

    # Reddit returns [post_listing, comments_listing]
    if not isinstance(raw, list) or len(raw) < 2:
        print("[ERROR] Unexpected response format from Reddit.")
        sys.exit(1)

    post_title = raw[0]["data"]["children"][0]["data"].get("title", "Unknown post")
    print(f"[INFO] Post: \"{post_title}\"")

    all_comments: list[dict] = []
    flatten_comments(raw[1]["data"]["children"], all_comments)
    print(f"[INFO] Loaded {len(all_comments)} comments total.")

    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=HOURS_BACK)
    results = []

    for c in all_comments:
        created = c.get("created_utc", 0)
        comment_time = datetime.fromtimestamp(created, tz=timezone.utc)
        if comment_time < cutoff:
            continue

        body = c.get("body", "")
        codes = extract_codes(body)
        if not codes:
            continue

        author = c.get("author", "[deleted]")
        permalink = c.get("permalink", "")
        comment_time_mt = comment_time.astimezone(MOUNTAIN_TZ)
        results.append({
            "author":  author,
            "time_mt": comment_time_mt.strftime("%Y-%m-%d %H:%M %Z"),
            "codes":   codes,
            "snippet": body[:200].replace("\n", " "),
            "link":    f"https://reddit.com{permalink}" if permalink else "N/A",
        })

    return results


# ─────────────────────────────────────────────
#  SAVE RESULTS
# ─────────────────────────────────────────────
def save_results(results: list[dict]) -> Path:
    timestamp = datetime.now(MOUNTAIN_TZ).strftime("%Y-%m-%d_%H-%M")
    out_file  = OUTPUT_DIR / f"waymo_codes_{timestamp}.txt"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  WAYMO REFERRAL / INVITE CODES — LAST 5 HOURS\n")
        f.write(f"  Scanned at : {datetime.now(MOUNTAIN_TZ).strftime('%Y-%m-%d %H:%M %Z')}\n")
        f.write(f"  Source     : https://reddit.com/r/{SUBREDDIT}/comments/{POST_ID}/\n")
        f.write("=" * 60 + "\n\n")

        if not results:
            f.write("No new codes found in the last 5 hours.\n")
        else:
            for i, entry in enumerate(results, 1):
                f.write(f"[{i}] Posted by : u/{entry['author']}\n")
                f.write(f"    Time      : {entry['time_mt']}\n")
                f.write(f"    Code(s)   : {', '.join(entry['codes'])}\n")
                f.write(f"    Comment   : {entry['snippet']}{'...' if len(entry['snippet']) == 200 else ''}\n")
                f.write(f"    Link      : {entry['link']}\n")
                f.write("-" * 60 + "\n")

        f.write(f"\nTotal comments with codes: {len(results)}\n")

    return out_file


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    print("\n🚗  Waymo Code Scanner — Starting\n")
    results  = scan_thread()
    out_file = save_results(results)
    print(f"\n✅  Done! Found {len(results)} comment(s) with codes.")
    print(f"📄  Results saved to: {out_file}\n")


if __name__ == "__main__":
    main()
