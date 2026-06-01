#!/usr/bin/env python3
"""Publish a markdown document to Confluence Server/DC with image attachments.

Usage:
    python .github/skills/confluence-publisher/scripts/publish_to_confluence.py \
        --draft generated_arch_20260310_151609/draft/v1.md \
        --illustrations generated_arch_20260310_151609/illustrations \
        --parent-id 560362556 \
        --space PRDCOMM00129

Requires env vars: CONFLUENCE_URL, CONFLUENCE_PERSONAL_TOKEN (MCP var) or CONFLUENCE_TOKEN (PAT for Bearer auth).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx


def get_client(base_url: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Atlassian-Token": "no-check",
        },
        timeout=30.0,
    )


# ---------------------------------------------------------------------------
# Markdown → Confluence Storage Format conversion
# ---------------------------------------------------------------------------

def _cell_to_xhtml(cell: str) -> str:
    """Convert a table cell that may contain <br>• bullet syntax to XHTML."""
    if "<br>" not in cell and "\u2022" not in cell:
        return _inline(cell)

    parts = cell.split("<br>")
    html_parts: list[str] = []
    bullets: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("\u2022"):
            bullets.append(f"<li>{_inline(part[1:].strip())}</li>")
        else:
            if bullets:
                html_parts.append("<ul>" + "".join(bullets) + "</ul>")
                bullets = []
            html_parts.append(f"<p>{_inline(part)}</p>")

    if bullets:
        html_parts.append("<ul>" + "".join(bullets) + "</ul>")

    return "".join(html_parts)


def _convert_table(md_table: str) -> str:
    """Convert a markdown table string to Confluence XHTML table."""
    lines = [l.strip() for l in md_table.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return md_table

    def _parse_row(row: str) -> list[str]:
        cells = row.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    header_cells = _parse_row(lines[0])
    # lines[1] is the separator (|---|---|...)
    body_rows = [_parse_row(l) for l in lines[2:]]

    html = '<table class="wrapped"><colgroup>'
    for _ in header_cells:
        html += "<col />"
    html += "</colgroup><thead><tr>"
    for cell in header_cells:
        html += f"<th>{_inline(cell)}</th>"
    html += "</tr></thead><tbody>"
    for row in body_rows:
        html += "<tr>"
        for cell in row:
            html += f"<td>{_cell_to_xhtml(cell)}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


def _inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code, links) to HTML."""
    # Protect code spans: extract, replace with placeholders
    code_spans: list[str] = []

    def _save_code(m: re.Match) -> str:
        escaped = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        code_spans.append(f"<code>{escaped}</code>")
        return f"\x00CODE{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _save_code, text)

    # Escape HTML entities in remaining text
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Bold + italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # Restore code spans
    for idx, span in enumerate(code_spans):
        text = text.replace(f"\x00CODE{idx}\x00", span)

    return text


def md_to_confluence(md: str) -> str:
    """Convert markdown content to Confluence storage format XHTML."""
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    in_table = False
    table_lines: list[str] = []

    def _flush_table():
        nonlocal in_table, table_lines
        if table_lines:
            out.append(_convert_table("\n".join(table_lines)))
            table_lines = []
        in_table = False

    while i < len(lines):
        line = lines[i]

        # --- GFM-style alert blocks: > [!WARNING], > [!NOTE], > [!INFO], > [!TIP] ---
        alert_m = re.match(r"^>\s*\[!(WARNING|NOTE|INFO|TIP|CAUTION)\]\s*$", line.strip(), re.IGNORECASE)
        if alert_m:
            _flush_table()
            alert_type = alert_m.group(1).upper()
            macro_name = {"WARNING": "warning", "CAUTION": "warning", "NOTE": "note", "INFO": "info", "TIP": "tip"}.get(alert_type, "note")
            i += 1
            body_lines: list[str] = []
            while i < len(lines) and lines[i].startswith(">"):
                body_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            inner = md_to_confluence("\n".join(body_lines))
            out.append(
                f'<ac:structured-macro ac:name="{macro_name}">'
                f"<ac:rich-text-body>{inner}</ac:rich-text-body>"
                f"</ac:structured-macro>"
            )
            continue

        # --- Plain blockquote (> text) ---
        if line.strip().startswith(">") and not line.strip().startswith(">|"):
            _flush_table()
            bq_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                bq_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            inner = md_to_confluence("\n".join(bq_lines))
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # --- Fenced code blocks ---
        if line.strip().startswith("```") and not in_code:
            _flush_table()
            in_code = True
            code_lang = line.strip().lstrip("`").strip()
            code_lines = []
            i += 1
            continue
        if line.strip().startswith("```") and in_code:
            lang_attr = f' ac:language="{code_lang}"' if code_lang else ""
            escaped = "\n".join(code_lines).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out.append(
                f'<ac:structured-macro ac:name="code"{lang_attr}>'
                f"<ac:plain-text-body><![CDATA[{escaped}]]></ac:plain-text-body>"
                f"</ac:structured-macro>"
            )
            in_code = False
            code_lang = ""
            code_lines = []
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # --- Tables ---
        if re.match(r"^\s*\|", line):
            in_table = True
            table_lines.append(line)
            i += 1
            continue
        if in_table:
            _flush_table()

        stripped = line.strip()

        # --- Blank lines ---
        if not stripped:
            i += 1
            continue

        # --- Horizontal rules ---
        if re.match(r"^-{3,}$", stripped):
            out.append("<hr />")
            i += 1
            continue

        # --- Headers ---
        m = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if m:
            level = len(m.group(1))
            title = _inline(m.group(2))
            out.append(f"<h{level}>{title}</h{level}>")
            i += 1
            continue

        # --- Images (convert to attachment refs) ---
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if m:
            alt = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            src = m.group(2)
            filename = Path(src).name
            out.append(
                f'<p><ac:image ac:alt="{alt}" ac:width="800">'
                f'<ri:attachment ri:filename="{filename}" />'
                f"</ac:image></p>"
            )
            i += 1
            continue

        # --- Unordered list items ---
        if re.match(r"^[-*]\s", stripped):
            list_items: list[str] = []
            while i < len(lines) and re.match(r"^\s*[-*]\s", lines[i]):
                item_text = re.sub(r"^\s*[-*]\s+", "", lines[i])
                list_items.append(f"<li>{_inline(item_text.strip())}</li>")
                i += 1
            out.append("<ul>" + "".join(list_items) + "</ul>")
            continue

        # --- Ordered list items ---
        if re.match(r"^\d+\.\s", stripped):
            list_items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s", lines[i]):
                item_text = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                list_items.append(f"<li>{_inline(item_text.strip())}</li>")
                i += 1
            out.append("<ol>" + "".join(list_items) + "</ol>")
            continue

        # --- Paragraph ---
        para_lines: list[str] = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#") and not lines[i].strip().startswith("```") and not re.match(r"^\s*\|", lines[i]) and not re.match(r"^-{3,}$", lines[i].strip()) and not re.match(r"^!\[", lines[i].strip()) and not re.match(r"^[-*]\s", lines[i].strip()) and not re.match(r"^\d+\.\s", lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(para_lines))}</p>")

    _flush_table()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Confluence REST API operations
# ---------------------------------------------------------------------------

def create_page(
    client: httpx.Client,
    space_key: str,
    parent_id: str,
    title: str,
    body_html: str,
) -> dict:
    payload = {
        "type": "page",
        "title": title,
        "ancestors": [{"id": parent_id}],
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": body_html,
                "representation": "storage",
            }
        },
    }
    resp = client.post(
        "/rest/api/content",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code not in (200, 201):
        print(f"ERROR creating page: {resp.status_code}\n{resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    print(f"Created page: id={data['id']}  title={data['title']}")
    return data


def upload_attachment(client: httpx.Client, page_id: str, filepath: Path) -> dict:
    with open(filepath, "rb") as f:
        resp = client.post(
            f"/rest/api/content/{page_id}/child/attachment",
            files={"file": (filepath.name, f, "image/png")},
        )
    if resp.status_code == 400 and "same file name" in resp.text:
        # Attachment already exists — find its ID and update
        att_resp = client.get(
            f"/rest/api/content/{page_id}/child/attachment",
            params={"filename": filepath.name},
        )
        if att_resp.status_code == 200:
            results = att_resp.json().get("results", [])
            if results:
                att_id = results[0]["id"]
                with open(filepath, "rb") as f2:
                    resp = client.post(
                        f"/rest/api/content/{page_id}/child/attachment/{att_id}/data",
                        files={"file": (filepath.name, f2, "image/png")},
                    )
    if resp.status_code not in (200, 201):
        # Skip non-critical attachment errors on update (images unchanged)
        print(f"  WARN: {filepath.name}: {resp.status_code} (skipped — may already exist)")
        return {}
    results = resp.json().get("results", [resp.json()])
    att = results[0] if isinstance(results, list) else results
    print(f"  Uploaded: {filepath.name} (id={att.get('id', '?')})")
    return att


def update_page(
    client: httpx.Client,
    page_id: str,
    title: str,
    body_html: str,
) -> dict:
    # Get current version number
    resp = client.get(f"/rest/api/content/{page_id}?expand=version")
    if resp.status_code != 200:
        print(f"ERROR reading page {page_id}: {resp.status_code}\n{resp.text}", file=sys.stderr)
        sys.exit(1)
    current = resp.json()
    version = current["version"]["number"] + 1

    payload = {
        "type": "page",
        "title": title,
        "version": {"number": version, "minorEdit": True},
        "body": {
            "storage": {
                "value": body_html,
                "representation": "storage",
            }
        },
    }
    resp = client.put(
        f"/rest/api/content/{page_id}",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code not in (200, 201):
        print(f"ERROR updating page: {resp.status_code}\n{resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    print(f"Updated page: id={data['id']}  version={version}  title={data['title']}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Publish markdown to Confluence")
    parser.add_argument("--draft", required=True, help="Path to markdown file")
    parser.add_argument("--illustrations", required=True, help="Path to illustrations directory")
    parser.add_argument("--parent-id", required=True, help="Parent page ID")
    parser.add_argument("--space", required=True, help="Confluence space key")
    parser.add_argument("--title", default=None, help="Page title (default: from markdown H1)")
    parser.add_argument("--update", default=None, help="Update existing page by ID instead of creating new")
    parser.add_argument("--toc", action="store_true", default=True, help="Prepend a Table of Contents macro (default: on)")
    parser.add_argument("--no-toc", dest="toc", action="store_false", help="Skip Table of Contents macro")
    args = parser.parse_args()

    url = os.environ.get("CONFLUENCE_URL")
    # CONFLUENCE_PERSONAL_TOKEN — MCP mcp-atlassian config var name
    # CONFLUENCE_TOKEN          — legacy / manual export fallback
    token = os.environ.get("CONFLUENCE_PERSONAL_TOKEN") or os.environ.get("CONFLUENCE_TOKEN")
    if not url or not token:
        print("ERROR: Set CONFLUENCE_URL and CONFLUENCE_PERSONAL_TOKEN (or CONFLUENCE_TOKEN) env vars", file=sys.stderr)
        sys.exit(1)

    draft_path = Path(args.draft)
    illust_dir = Path(args.illustrations)

    md = draft_path.read_text(encoding="utf-8")

    # Extract title from first H1 if not provided
    title = args.title
    if not title:
        m = re.search(r"^#\s+(.+)", md, re.MULTILINE)
        title = m.group(1).strip() if m else "Untitled"

    print(f"Title: {title}")
    print(f"Space: {args.space}")
    print(f"Parent: {args.parent_id}")

    # Convert markdown → Confluence storage format
    body = md_to_confluence(md)
    if args.toc:
        toc_macro = (
            '<ac:structured-macro ac:name="toc">'
            '<ac:parameter ac:name="minLevel">1</ac:parameter>'
            '<ac:parameter ac:name="maxLevel">3</ac:parameter>'
            '<ac:parameter ac:name="printable">true</ac:parameter>'
            '</ac:structured-macro>'
        )
        body = toc_macro + "\n" + body
    print(f"Converted to storage format: {len(body)} chars")

    client = get_client(url, token)

    # 1. Verify parent page exists
    resp = client.get(f"/rest/api/content/{args.parent_id}")
    if resp.status_code != 200:
        print(f"ERROR: Cannot read parent page {args.parent_id}: {resp.status_code}", file=sys.stderr)
        sys.exit(1)
    print(f"Parent page: {resp.json()['title']}")

    # 2. Create or update page
    if args.update:
        page = update_page(client, args.update, title, body)
        page_id = args.update
    else:
        page = create_page(client, args.space, args.parent_id, title, body)
        page_id = page["id"]

    # 3. Upload illustrations
    png_files = sorted(illust_dir.glob("*.png"))
    print(f"\nUploading {len(png_files)} illustrations...")
    for png in png_files:
        upload_attachment(client, page_id, png)

    # 4. Print result
    base_url = url.rstrip("/")
    page_url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
    print(f"\n{'='*60}")
    print(f"PUBLISHED: {page_url}")
    print(f"Page ID:   {page_id}")
    print(f"Title:     {title}")
    print(f"Images:    {len(png_files)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
