"""Generate Space Daily newsletter editions from reviewed cached NASA content.

Safe default: preview mode writes local HTML only.  It never contacts Kit.
Kit writes are opt-in modes with separate environment approval gates; no
subscriber records are fetched or written to disk.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
DATA = BASE / "data"
DEFAULT_OUTPUT = BASE / "build" / "newsletters"
KIT_API = "https://api.kit.com/v4"
TAG_NAMES = {"daily": "Daily Newsletter", "weekly": "Weekly Newsletter"}


class NewsletterError(RuntimeError):
    pass


def record_status(message):
    """Write non-personal operational status to an Actions job summary, if any."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        pathlib.Path(summary).open("a", encoding="utf-8").write(message + "\n")


def load_json(path: pathlib.Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def clean(value, limit=360):
    text = html.unescape(str(value or ""))
    text = " ".join(text.replace("<", " <").split())
    return text[:limit].strip()


def parse_date(value):
    try:
        return email.utils.parsedate_to_datetime(value).astimezone(dt.timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def article_key(article):
    return str(article.get("link", "")).rstrip("/")


def unique_articles(items):
    seen = set()
    result = []
    for item in items:
        key = article_key(item)
        if not key or key in seen or not str(item.get("link", "")).startswith("https://"):
            continue
        seen.add(key)
        result.append(item)
    return result


def ranked_articles(items):
    """Prioritise NASA-labelled discoveries without adding editorial claims."""
    def score(item):
        title = clean(item.get("title")).lower()
        return (0 if item.get("category") == "Discovery" else 1,
                1 if title.startswith("apod:") else 0,
                -(parse_date(item.get("date")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)).timestamp())
    # APOD is already the dedicated featured image below. Do not repeat it as a
    # headline and risk presenting the same source twice in one edition.
    return sorted((item for item in unique_articles(items) if not clean(item.get("title")).lower().startswith("apod:")), key=score)


def content_for(edition, issue_date):
    latest = load_json(DATA / "latest.json", {})
    lessons = load_json(DATA / "lessons.json", [])
    history = load_json(DATA / "newsletter-history.json", {"news": latest.get("news", [])})
    if not isinstance(lessons, list) or not lessons:
        return None, "No reviewed lesson catalogue is available."
    try:
        refreshed = dt.datetime.fromisoformat(str(latest.get("updated", "")).replace("Z", "+00:00")).date()
    except ValueError:
        refreshed = None
    if refreshed != issue_date:
        return None, "NASA cache was not successfully refreshed for this issue date."
    apod = latest.get("apod") or {}
    if apod.get("media_type") != "image" or not str(apod.get("image", "")).startswith("https://"):
        return None, "No valid NASA APOD image is available."
    if edition == "daily":
        candidates = latest.get("news", [])
        heading = "Today’s NASA reporting"
        limit = 3
    else:
        start = dt.datetime.combine(issue_date - dt.timedelta(days=6), dt.time.min, tzinfo=dt.timezone.utc)
        end = dt.datetime.combine(issue_date, dt.time.max, tzinfo=dt.timezone.utc)
        candidates = [item for item in history.get("news", []) if (parse_date(item.get("date")) and start <= parse_date(item.get("date")) <= end)]
        heading = "NASA reporting from the past week"
        limit = 5
    articles = ranked_articles(candidates)[:limit]
    if len(articles) < 3:
        return None, f"Only {len(articles)} valid non-duplicate NASA stories are available; delivery is skipped."
    lesson = lessons[issue_date.toordinal() % len(lessons)]
    return {
        "edition": edition,
        "issue_date": issue_date,
        "articles": articles,
        "heading": heading,
        "apod": apod,
        "lesson": lesson,
    }, None


def safe_url(value):
    value = str(value or "")
    return value if value.startswith("https://") else ""


def site_url():
    value = os.environ.get("SPACE_DAILY_SITE_URL", "").rstrip("/")
    return value if value.startswith("https://") else ""


def render_html(content, site):
    edition = content["edition"].title()
    apod = content["apod"]
    lesson = content["lesson"]
    rows = []
    for article in content["articles"]:
        title = html.escape(clean(article.get("title"), 180))
        summary = html.escape(clean(article.get("description"), 320))
        date = html.escape(clean(article.get("date"), 80))
        link = html.escape(safe_url(article.get("link")), quote=True)
        rows.append(f'''<tr><td style="padding:0 0 22px"><p style="margin:0 0 6px;color:#9fb9d4;font:700 11px Arial,sans-serif;letter-spacing:1.2px;text-transform:uppercase">NASA · {date}</p><h2 style="margin:0 0 8px;font:400 25px Georgia,serif;color:#f4f8ff;line-height:1.2">{title}</h2><p style="margin:0 0 10px;color:#c4d0dd;font:15px/1.55 Arial,sans-serif">{summary}</p><a href="{link}" style="color:#d5edff;font:700 13px Arial,sans-serif">Read the NASA source →</a></td></tr>''')
    lesson_link = f"{site}/#lesson" if site else safe_url(lesson.get("source"))
    home_link = site or safe_url(lesson.get("source"))
    apod_link = safe_url(apod.get("link"))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;padding:0;background:#050914;color:#edf3fb"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#050914"><tr><td align="center" style="padding:28px 14px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#10151e;border:1px solid #334154"><tr><td style="padding:30px 30px 20px;border-bottom:1px solid #334154"><p style="margin:0 0 7px;color:#a9c7e2;font:700 10px Arial,sans-serif;letter-spacing:2px">NEWS · EXPLORATION · DISCOVERY</p><h1 style="margin:0;color:#f4f8ff;font:400 31px Georgia,serif;letter-spacing:3px;text-transform:uppercase">Space Daily</h1><p style="margin:16px 0 0;color:#b9c8d8;font:14px/1.5 Arial,sans-serif">{edition} edition · {content['issue_date'].strftime('%d %B %Y')}</p></td></tr><tr><td style="padding:30px"><h2 style="margin:0 0 20px;color:#f4f8ff;font:400 30px Georgia,serif">{content['heading']}</h2><table role="presentation" width="100%" cellspacing="0" cellpadding="0">{''.join(rows)}</table><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:8px;border-top:1px solid #334154;border-bottom:1px solid #334154"><tr><td style="padding:24px 0"><a href="{html.escape(apod_link,quote=True)}"><img src="{html.escape(safe_url(apod.get('image')),quote=True)}" alt="{html.escape(clean(apod.get('alt') or apod.get('title'),180),quote=True)}" width="580" style="display:block;width:100%;max-width:580px;height:auto;border:0"></a><p style="margin:12px 0 4px;color:#a9c7e2;font:700 10px Arial,sans-serif;letter-spacing:1.2px;text-transform:uppercase">NASA Astronomy Picture of the Day</p><h2 style="margin:0 0 7px;color:#f4f8ff;font:400 25px Georgia,serif">{html.escape(clean(apod.get('title'),180))}</h2><p style="margin:0;color:#b9c8d8;font:12px/1.5 Arial,sans-serif">Image credit: {html.escape(clean(apod.get('credit'),240))} · <a href="{html.escape(apod_link,quote=True)}" style="color:#d5edff">View original</a></p></td></tr></table><p style="margin:25px 0 7px;color:#a9c7e2;font:700 10px Arial,sans-serif;letter-spacing:1.2px;text-transform:uppercase">Today’s discovery</p><h2 style="margin:0 0 8px;color:#f4f8ff;font:400 25px Georgia,serif">{html.escape(clean(lesson.get('title'),180))}</h2><p style="margin:0 0 12px;color:#c4d0dd;font:15px/1.55 Arial,sans-serif">{html.escape(clean(lesson.get('summary'),320))}</p><a href="{html.escape(lesson_link,quote=True)}" style="color:#d5edff;font:700 13px Arial,sans-serif">Explore the lesson →</a></td></tr><tr><td style="padding:20px 30px;border-top:1px solid #334154;color:#8998aa;font:11px/1.5 Arial,sans-serif">NASA stories and images are credited and linked to their original sources. <a href="{html.escape(home_link,quote=True)}" style="color:#b9d9f2">Space Daily</a> · <a href="{{{{ unsubscribe_url }}}}" style="color:#b9d9f2">Unsubscribe</a></td></tr></table></td></tr></table></body></html>'''


def write_preview(content, output, site):
    directory = output / content["issue_date"].isoformat()
    directory.mkdir(parents=True, exist_ok=True)
    html_path = directory / f"{content['edition']}.html"
    html_path.write_text(render_html(content, site), encoding="utf-8")
    metadata = {"edition": content["edition"], "issue_date": content["issue_date"].isoformat(), "article_count": len(content["articles"]), "mode": "preview", "status": "generated"}
    (directory / f"{content['edition']}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return html_path


def kit_request(method, path, key, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(KIT_API + path, data=body, method=method, headers={"X-Kit-Api-Key": key, "Content-Type": "application/json", "User-Agent": "SpaceDailyNewsletter/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                time.sleep(int(error.headers.get("Retry-After", 2 ** attempt)))
                continue
            raise NewsletterError(f"Kit API returned HTTP {error.code}; no subscriber data was logged.") from error
        except urllib.error.URLError as error:
            if attempt == 2: raise NewsletterError("Kit API connection failed.") from error
            time.sleep(2 ** attempt)
    raise NewsletterError("Kit API rate limit or server error persisted after retries.")


def kit_tags(key):
    tags = []
    path = "/tags?per_page=1000"
    while path:
        page = kit_request("GET", path, key)
        tags.extend(page.get("tags", []))
        pagination = page.get("pagination", {})
        path = f"/tags?per_page=1000&after={urllib.parse.quote(str(pagination.get('end_cursor','')))}" if pagination.get("has_next_page") else ""
    return {tag.get("name"): tag.get("id") for tag in tags}


def existing_broadcast(key, marker):
    path = "/broadcasts?per_page=1000&slim=true"
    while path:
        page = kit_request("GET", path, key)
        for broadcast in page.get("broadcasts", []):
            if broadcast.get("description") == marker:
                return broadcast
        pagination = page.get("pagination", {})
        path = f"/broadcasts?per_page=1000&slim=true&after={urllib.parse.quote(str(pagination.get('end_cursor','')))}" if pagination.get("has_next_page") else ""
    return None


def create_broadcast(content, key, tag_id, mode, site, send_at=None):
    marker = f"space-daily:{content['edition']}:{content['issue_date'].isoformat()}"
    existing = existing_broadcast(key, marker)
    if existing:
        return {"status": "duplicate-prevented", "broadcast_id": existing.get("id")}
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    payload = {"content": render_html(content, site), "description": marker, "public": False, "published_at": now, "send_at": send_at, "preview_text": "NASA reporting, imagery, and learning from Space Daily.", "subject": f"Space Daily — {content['edition'].title()} edition · {content['issue_date'].strftime('%d %b')}", "subscriber_filter": [{"all": [{"type": "tag", "ids": [tag_id]}], "any": None, "none": None}]}
    result = kit_request("POST", "/broadcasts", key, payload)
    broadcast = result.get("broadcast", {})
    return {"status": "scheduled" if send_at else "draft-created", "broadcast_id": broadcast.get("id"), "mode": mode}


def approved(name, expected):
    if os.environ.get(name) != expected:
        raise NewsletterError(f"{name} is not explicitly enabled; no email action was taken.")


def run_edition(content, args, output):
    preview = write_preview(content, output, site_url())
    print(f"{content['edition']}: preview generated at {preview}")
    record_status(f"- {content['edition']}: preview generated ({len(content['articles'])} NASA stories; no recipients queried)")
    if args.mode == "preview": return
    key = os.environ.get("KIT_API_KEY")
    if not key: raise NewsletterError("KIT_API_KEY is required for Kit verification or write modes.")
    tags = kit_tags(key)
    tag_id = tags.get(TAG_NAMES[content["edition"]])
    if not tag_id: raise NewsletterError(f"Kit tag '{TAG_NAMES[content['edition']]}' was not found; no broadcast was created.")
    print(f"{content['edition']}: verified target tag id {tag_id}")
    if args.mode == "verify": return
    site = site_url()
    if not site: raise NewsletterError("SPACE_DAILY_SITE_URL must be an HTTPS URL before creating a Kit broadcast.")
    if args.mode == "draft":
        approved("KIT_DRAFTS_ENABLED", "true")
        result = create_broadcast(content, key, tag_id, "draft", site)
    elif args.mode == "test-send":
        approved("NEWSLETTER_TEST_SEND_ENABLED", "I_APPROVE_TEST_SEND")
        if not args.confirm_test_send: raise NewsletterError("Pass --confirm-test-send for the approved test-audience mode.")
        test_tag = os.environ.get("KIT_TEST_TAG_ID")
        if not test_tag or not test_tag.isdigit(): raise NewsletterError("KIT_TEST_TAG_ID is required and must identify an approved test-only tag.")
        if not args.send_at: raise NewsletterError("--send-at (future ISO8601 UTC time) is required for test delivery.")
        try:
            if dt.datetime.fromisoformat(args.send_at.replace("Z", "+00:00")).astimezone(dt.timezone.utc) <= dt.datetime.now(dt.timezone.utc):
                raise ValueError
        except ValueError:
            raise NewsletterError("--send-at must be a future ISO8601 UTC timestamp.")
        result = create_broadcast(content, key, int(test_tag), "test-send", site, args.send_at)
    else:
        approved("NEWSLETTER_PRODUCTION_ENABLED", "I_APPROVE_PRODUCTION_SENDING")
        send_at = args.send_at or (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10)).isoformat()
        result = create_broadcast(content, key, tag_id, "production", site, send_at)
    print(f"{content['edition']}: {result['status']} (broadcast id {result.get('broadcast_id','not-created')})")
    record_status(f"- {content['edition']}: {result['status']} (broadcast id {result.get('broadcast_id','not-created')}; no subscriber data recorded)")


def main():
    parser = argparse.ArgumentParser(description="Prepare Space Daily newsletters safely.")
    parser.add_argument("--edition", choices=("daily", "weekly", "both"), default="both")
    parser.add_argument("--mode", choices=("preview", "verify", "draft", "test-send", "production"), default="preview")
    parser.add_argument("--date", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
    parser.add_argument("--output-dir", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--send-at", help="Future ISO8601 UTC timestamp, only for approved send modes.")
    parser.add_argument("--confirm-test-send", action="store_true")
    args = parser.parse_args()
    editions = ("daily", "weekly") if args.edition == "both" else (args.edition,)
    skipped = []
    for edition in editions:
        content, reason = content_for(edition, args.date)
        if not content:
            skipped.append(f"{edition}: {reason}")
            print(f"{edition}: skipped — {reason}")
            record_status(f"- {edition}: skipped — {reason}")
            continue
        run_edition(content, args, args.output_dir)
    if skipped and len(skipped) == len(editions):
        print("No delivery action taken because valid content was insufficient.")


if __name__ == "__main__":
    try:
        main()
    except NewsletterError as error:
        print(f"Newsletter safety stop: {error}")
        raise SystemExit(2)
