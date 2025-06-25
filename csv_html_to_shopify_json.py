#!/usr/bin/env python3
"""
CSV HTML → Shopify JSON converter
---------------------------------

Reads a CSV that contains HTML (or plain text) in **"description.language"**, converts
that column to Shopify-compatible JSON nodes, and writes a new CSV. By default the
script now assumes the CSV is **semicolon-separated (`;`)** so you can just run:

    python csv_html_to_shopify_json.py input.csv output.csv

If your file actually uses a different delimiter you can still override with
`--sep ','`, but in normal usage no flag is needed.

Dependencies:
    pip install pandas beautifulsoup4
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

DEFAULT_SEP = ";"  # <-- hard-coded default separator


def html_to_json(html: str) -> str:
    """Convert an HTML fragment to the JSON structure Shopify expects."""

    soup = BeautifulSoup(html, "html.parser")

    def parse_element(element):
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            return {
                "type": "heading",
                "children": [{"type": "text", "value": element.get_text(strip=True)}],
                "level": int(element.name[1]),
            }
        elif element.name == "p":
            children = []
            for child in element.children:
                if child.name == "em":
                    children.append({"type": "text", "value": child.get_text(strip=True), "italic": True})
                elif child.name == "strong":
                    children.append({"type": "text", "value": child.get_text(strip=True), "bold": True})
                elif child.name == "a":
                    link_obj = {
                        "type": "link",
                        "url": child.get("href", ""),
                        "children": [{"type": "text", "value": child.get_text(strip=True)}],
                    }
                    if child.has_attr("target"):
                        link_obj["target"] = child["target"]
                    if child.has_attr("title"):
                        link_obj["title"] = child["title"]
                    children.append(link_obj)
                elif child.name is None:
                    txt = child.strip()
                    if txt:
                        children.append({"type": "text", "value": txt})
            return {"type": "paragraph", "children": children}
        elif element.name in ["ul", "ol"]:
            list_type = "unordered" if element.name == "ul" else "ordered"
            return {"type": list_type, "children": [parse_element(li) for li in element.find_all("li", recursive=False)]}
        elif element.name == "li":
            children = []
            for child in element.children:
                if child.name == "i":
                    children.append({"type": "text", "value": child.get_text(strip=True), "italic": True})
                elif child.name == "strong":
                    children.append({"type": "text", "value": child.get_text(strip=True), "bold": True})
                elif child.name is None:
                    txt = child.strip()
                    if txt:
                        children.append({"type": "text", "value": txt})
            return {"type": "list-item", "children": children}
        return None

    root = {"type": "root", "children": []}
    for element in soup.children:
        parsed = parse_element(element)
        if parsed:
            root["children"].append(parsed)
    return json.dumps(root, ensure_ascii=False)


def convert_cell(text: str) -> str:
    """Convert a single CSV cell to JSON (handles plain text too)."""
    if text is None or str(text).strip() == "":
        return ""
    raw = str(text).strip()
    soup = BeautifulSoup(raw, "html.parser")
    has_tags = any(getattr(node, "name", None) for node in soup.descendants)
    html_fragment = raw if has_tags else f"<p>{raw}</p>"
    return html_to_json(html_fragment)


def main():
    parser = argparse.ArgumentParser(description="Convert description.language column from HTML to Shopify JSON")
    parser.add_argument("input_csv", help="Path to input CSV")
    parser.add_argument("output_csv", help="Path to output CSV")
    parser.add_argument("--sep", default=DEFAULT_SEP, help=f"Field separator (default '{DEFAULT_SEP}')")
    args = parser.parse_args()

    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    sep = args.sep

    if not in_path.exists():
        sys.exit(f"Input file not found: {in_path}")

    try:
        df = pd.read_csv(
            in_path,
            dtype=str,
            keep_default_na=False,
            sep=sep,
            quotechar='"',
            escapechar='\\',
            engine="python",
            quoting=csv.QUOTE_MINIMAL,
        )
    except Exception as e:
        sys.exit(f"Error reading CSV: {e}")

    if "description.language" not in df.columns:
        sys.exit("Column 'description.language' not found in input CSV")

    df["description.language"] = df["description.language"].apply(convert_cell)

    try:
        df.to_csv(out_path, index=False, encoding="utf-8", sep=sep, quoting=csv.QUOTE_MINIMAL)
    except Exception as e:
        sys.exit(f"Error writing CSV: {e}")

    print(f"✅ Conversion complete → {out_path}")


if __name__ == "__main__":
    main()