import re
from typing import List, Dict, Set, Optional, Tuple
import requests
from src.config import NOTION_API_KEY, NOTION_VERSION

def _get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

def get_database_tags(database_id: str) -> List[str]:
    """Lekéri a Notion adatbázis létező címkéit (Tags multi-select)."""
    headers = _get_headers()
    url = f"https://api.notion.com/v1/databases/{database_id}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            props = res.json().get("properties", {})
            tags_prop = props.get("Tags", {})
            options = tags_prop.get("multi_select", {}).get("options", [])
            return [opt.get("name") for opt in options if opt.get("name")]
    except Exception as e:
        print(f"Hiba a címkék lekérésekor: {e}")
    return []

def get_existing_video_urls(database_id: str) -> Set[str]:
    """
    Lekérdezi az adatbázisban már rögzített YouTube videók URL-jeit.
    Kezeli az oldalazást (pagination).
    """
    headers = _get_headers()
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    existing_urls = set()
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code != 200:
                break
            data = res.json()
            for page in data.get("results", []):
                props = page.get("properties", {})
                url_prop = props.get("URL", {})
                v_url = url_prop.get("url")
                if v_url:
                    existing_urls.add(v_url.strip())
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        except Exception as e:
            print(f"Hiba a létező URL-ek lekérdezésekor: {e}")
            break

    return existing_urls

def parse_inline_markdown(text: str) -> List[Dict]:
    """
    Átalakítja a Markdown szövegrészleteket valódi Notion rich_text elemekké:
    kezeli a **félkövér**, *dőlt*, `kód` és [szöveg](https://link) formázásokat,
    hogy ne maradjanak nyers csillagok a Notionben.
    """
    if not text:
        return []

    token_pattern = re.compile(
        r'(\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?://[^\s)]+\)|\*[^*\n]+\*)'
    )
    parts = token_pattern.split(text)
    rich_items: List[Dict] = []

    def _add_segment(content: str, bold: bool = False, italic: bool = False, code: bool = False, link: Optional[str] = None):
        if not content:
            return
        for start in range(0, len(content), 1900):
            chunk = content[start:start + 1900]
            text_obj: Dict = {"content": chunk}
            if link:
                text_obj["link"] = {"url": link}
            item: Dict = {"type": "text", "text": text_obj}
            if bold or italic or code:
                item["annotations"] = {
                    "bold": bold,
                    "italic": italic,
                    "code": code,
                    "strikethrough": False,
                    "underline": False,
                    "color": "default",
                }
            rich_items.append(item)

    for part in parts:
        if not part:
            continue
        if part.startswith("***") and part.endswith("***") and len(part) > 6:
            _add_segment(part[3:-3], bold=True, italic=True)
        elif part.startswith("**") and part.endswith("**") and len(part) > 4:
            _add_segment(part[2:-2], bold=True)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            _add_segment(part[1:-1], code=True)
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            m = re.match(r'^\[([^\]]+)\]\((https?://[^\s)]+)\)$', part)
            if m:
                _add_segment(m.group(1), link=m.group(2))
            else:
                _add_segment(part)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            _add_segment(part[1:-1], italic=True)
        else:
            _add_segment(part)

    return rich_items if rich_items else [{"type": "text", "text": {"content": text[:1900]}}]


def _parse_list_line(line: str) -> Optional[Tuple[int, str, str, bool]]:
    """
    Felismeri a lista-elemeket és behúzásukat:
    Visszatérés: (indent_spaces, block_type, clean_text, is_checked) vagy None.
    """
    stripped = line.lstrip(" \t")
    indent = len(line) - len(stripped)
    # Tabokat 2 szóköznek számoljuk
    indent = line[:indent].count(" ") + line[:indent].count("\t") * 2

    # Pipálható To-Do: - [ ] vagy - [x]
    m_todo = re.match(r'^[-*•]\s+\[([ xX])\]\s+(.*)', stripped)
    if m_todo:
        checked = m_todo.group(1).lower() == "x"
        return indent, "to_do", m_todo.group(2).strip(), checked

    # Sima felsorolás: - , * , •
    m_bullet = re.match(r'^[-*•]\s+(.*)', stripped)
    if m_bullet:
        return indent, "bulleted_list_item", m_bullet.group(1).strip(), False

    # Számozott lista: 1. vagy 1)
    m_num = re.match(r'^\d+[\.\)]\s+(.*)', stripped)
    if m_num:
        return indent, "numbered_list_item", m_num.group(1).strip(), False

    return None


def _make_list_block(btype: str, content: str, checked: bool = False) -> Dict:
    rt = parse_inline_markdown(content)
    if btype == "to_do":
        return {"object": "block", "type": "to_do", "to_do": {"rich_text": rt, "checked": checked}}
    return {"object": "block", "type": btype, btype: {"rich_text": rt}}


def markdown_to_notion_blocks(markdown_text: str) -> List[Dict]:
    """
    Átalakítja a komplex Zettelkasten Markdown szöveget valódi, gazdag Notion blokkokká:
    - Inline formázások (**félkövér**, *dőlt*, `kód`, linkek)
    - Címsorok (#, ##, ###), elválasztók (---), többsoros idézetek (>)
    - Többszintű (beágyazott / nested) bullet-, számozott- és pipálható to_do listák
    - Markdown táblázatok (| A | B |) -> valódi Notion table + table_row blokkok
    """
    lines = markdown_text.splitlines()
    blocks: List[Dict] = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Üres sorok átugrása
        if not line.strip():
            i += 1
            continue

        # Elválasztó vonal (---)
        if line.strip() in ["---", "***", "___"]:
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Markdown táblázat felismerése (| oszlop1 | oszlop2 |)
        if line.lstrip().startswith("|") and line.rstrip().endswith("|") and line.count("|") >= 2:
            table_rows_raw: List[List[str]] = []
            while i < len(lines):
                t_line = lines[i].strip()
                if not (t_line.startswith("|") and t_line.endswith("|")):
                    break
                cells = [c.strip() for c in t_line.strip("|").split("|")]
                # Elválasztó sor kihagyása (pl. |---|---|)
                if all(re.match(r'^:?-{2,}:?$', c) or c == "" for c in cells):
                    i += 1
                    continue
                table_rows_raw.append(cells)
                i += 1

            if table_rows_raw:
                col_count = max(len(r) for r in table_rows_raw)
                if col_count >= 1:
                    notion_rows = []
                    for r in table_rows_raw:
                        padded = r + [""] * (col_count - len(r))
                        cell_rts = [parse_inline_markdown(c) if c else [] for c in padded[:col_count]]
                        notion_rows.append({
                            "object": "block",
                            "type": "table_row",
                            "table_row": {"cells": cell_rts}
                        })
                    blocks.append({
                        "object": "block",
                        "type": "table",
                        "table": {
                            "table_width": col_count,
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": notion_rows[:95]
                        }
                    })
            continue

        # Címsorok (#, ##, ###, ####)
        if line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": parse_inline_markdown(line[2:].strip())}
            })
            i += 1
            continue

        if line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": parse_inline_markdown(line[3:].strip())}
            })
            i += 1
            continue

        if line.startswith("### ") or line.startswith("#### "):
            clean_h3 = re.sub(r'^#{3,4}\s+', '', line).strip()
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": parse_inline_markdown(clean_h3)}
            })
            i += 1
            continue

        # Idézet (több egymást követő > sor összefűzése egyetlen quote blokkba)
        if line.lstrip().startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                q_clean = re.sub(r'^\s*>\s?', '', lines[i]).rstrip()
                if q_clean:
                    quote_lines.append(q_clean)
                i += 1
            full_quote = "\n".join(quote_lines).strip()
            if full_quote:
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": parse_inline_markdown(full_quote)}
                })
            continue

        # Lista elemek (többszintű hierarchia támogatással max 2 gyermek-szintig, Notion API szabály szerint)
        parsed_list = _parse_list_line(line)
        if parsed_list:
            level0_blocks: List[Dict] = []
            base_indent = parsed_list[0]
            while i < len(lines):
                curr_line = lines[i].rstrip()
                if not curr_line.strip():
                    # Ha a következő nem-üres sor behúzott al-elem, ne szakítsuk meg a listát
                    if i + 1 < len(lines) and _parse_list_line(lines[i + 1].rstrip()):
                        i += 1
                        continue
                    break
                p_item = _parse_list_line(curr_line)
                if not p_item:
                    break
                ind, btype, ctext, chk = p_item
                new_block = _make_list_block(btype, ctext, chk)

                if ind <= base_indent or not level0_blocks:
                    level0_blocks.append(new_block)
                elif ind <= base_indent + 3:
                    # 1. szintű gyermek (al-pont)
                    parent = level0_blocks[-1]
                    ptype = parent["type"]
                    parent[ptype].setdefault("children", []).append(new_block)
                else:
                    # 2. szintű gyermek (unoka-pont)
                    parent = level0_blocks[-1]
                    ptype = parent["type"]
                    lvl1_list = parent[ptype].setdefault("children", [])
                    if lvl1_list:
                        lvl1_parent = lvl1_list[-1]
                        l1_type = lvl1_parent["type"]
                        lvl1_parent[l1_type].setdefault("children", []).append(new_block)
                    else:
                        lvl1_list.append(new_block)
                i += 1

            blocks.extend(level0_blocks)
            continue

        # Normál bekezdés (együtt tartva az összetartozó sorokat)
        para_lines = [line.strip()]
        while i + 1 < len(lines):
            next_line = lines[i + 1].rstrip()
            if (
                not next_line.strip()
                or next_line.strip() in ["---", "***", "___"]
                or next_line.startswith("#")
                or next_line.lstrip().startswith(">")
                or (next_line.lstrip().startswith("|") and next_line.rstrip().endswith("|"))
                or _parse_list_line(next_line) is not None
            ):
                break
            para_lines.append(next_line.strip())
            i += 1

        full_para = " ".join(para_lines).strip()
        if full_para:
            for chunk_start in range(0, len(full_para), 1900):
                chunk = full_para[chunk_start:chunk_start + 1900]
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": parse_inline_markdown(chunk)}
                })
        i += 1

    return blocks

def create_zettelkasten_note(
    database_id: str,
    title: str,
    video_url: str,
    tags: List[str],
    markdown_content: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Létrehozza a jegyzetet a Notion 'Zettelkasten Notes [PT]' adatbázisban.
    Visszatérés: (siker, üzenet, notion_page_url)
    """
    headers = _get_headers()
    blocks = markdown_to_notion_blocks(markdown_content)

    initial_blocks = blocks[:100]
    remaining_blocks = blocks[100:]

    properties = {
        "Name": {
            "title": [{"type": "text", "text": {"content": title[:200]}}]
        },
        "URL": {
            "url": video_url
        }
    }

    if tags:
        properties["Tags"] = {
            "multi_select": [{"name": t} for t in tags]
        }

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": initial_blocks
    }

    create_url = "https://api.notion.com/v1/pages"
    try:
        res = requests.post(create_url, headers=headers, json=payload, timeout=20)
        if res.status_code != 200:
            return False, f"Notion hiba (HTTP {res.status_code}): {res.text}", None

        page_data = res.json()
        page_id = page_data.get("id")
        page_url = page_data.get("url")

        if remaining_blocks and page_id:
            append_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            for b_idx in range(0, len(remaining_blocks), 100):
                batch = remaining_blocks[b_idx:b_idx + 100]
                batch_res = requests.patch(append_url, headers=headers, json={"children": batch}, timeout=20)
                if batch_res.status_code != 200:
                    print(f"Figyelmeztetés: néhány blokk hozzáfűzése sikertelen volt: {batch_res.text}")

        return True, "Sikeresen mentve a Notion adatbázisba!", page_url

    except Exception as e:
        return False, f"Hálózati hiba a Notion mentés során: {str(e)}", None
