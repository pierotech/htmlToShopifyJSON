#!/usr/bin/env python3
"""csv_html_to_shopify_json.py

Convert the **description.language** column of a CSV from HTML/plain‑text to Shopify
Rich‑Text JSON nodes.

*   Default field separator: semicolon (;).
    Override with --sep ',' if your file uses commas.

Usage
-----
    python csv_html_to_shopify_json.py input.csv output.csv [--sep ',']

Dependencies: pandas, beautifulsoup4
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

DEFAULT_SEP = ';'  # default CSV delimiter

# Map HTML list tag → Shopify listType
LIST_TYPE_MAP = {'ul': 'unordered', 'ol': 'ordered'}


def html_to_json(html: str) -> str:
    """Convert an HTML fragment to the JSON structure accepted by Shopify."""

    soup = BeautifulSoup(html, 'html.parser')

    def parse_element(element):
        # Headings
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return {
                'type': 'heading',
                'level': int(element.name[1]),
                'children': [{'type': 'text', 'value': element.get_text(strip=True)}],
            }

        # Paragraphs (including empty ones)
        elif element.name == 'p':
            children = []
            for child in element.children:
                if child.name == 'em':
                    children.append({'type': 'text',
                                     'value': child.get_text(strip=True),
                                     'italic': True})
                elif child.name == 'strong':
                    children.append({'type': 'text',
                                     'value': child.get_text(strip=True),
                                     'bold': True})
                elif child.name == 'a':
                    link_obj = {
                        'type': 'link',
                        'url': child.get('href', ''),
                        'children': [{'type': 'text',
                                      'value': child.get_text(strip=True)}],
                    }
                    if child.has_attr('title'):
                        link_obj['title'] = child['title']
                    children.append(link_obj)
                elif child.name is None:
                    # Keep whitespace as‑is (allows empty paragraphs)
                    children.append({'type': 'text', 'value': str(child)})

            # Ensure at least one text node for totally empty <p></p>
            if not children:
                children.append({'type': 'text', 'value': ''})

            return {'type': 'paragraph', 'children': children}

        # Lists
        elif element.name in ['ul', 'ol']:
            list_type = LIST_TYPE_MAP[element.name]
            list_children = [parse_element(li)
                             for li in element.find_all('li', recursive=False)]
            # Filter out None entries (e.g., <li></li>)
            list_children = [c for c in list_children if c]
            return {
                'type': 'list',
                'listType': list_type,
                'children': list_children,
            }

        # List items
        elif element.name == 'li':
            children = []
            for child in element.children:
                if child.name == 'i':
                    children.append({'type': 'text',
                                     'value': child.get_text(strip=True),
                                     'italic': True})
                elif child.name == 'strong':
                    children.append({'type': 'text',
                                     'value': child.get_text(strip=True),
                                     'bold': True})
                elif child.name is None:
                    txt = str(child).strip()
                    if txt:
                        children.append({'type': 'text', 'value': txt})

            # Allow empty list items (Shopify permits them as blank bullets)
            if not children:
                children.append({'type': 'text', 'value': ''})

            return {'type': 'list-item', 'children': children}

        return None

    # Build root
    root = {'type': 'root', 'children': []}
    for el in soup.children:
        parsed = parse_element(el)
        if parsed:
            root['children'].append(parsed)

    return json.dumps(root, ensure_ascii=False)


def convert_cell(text: str) -> str:
    """Convert a CSV cell (HTML or plain text) to Shopify JSON."""
    if text is None or str(text).strip() == '':
        return ''

    raw = str(text).strip()
    soup = BeautifulSoup(raw, 'html.parser')
    contains_tags = any(getattr(node, 'name', None) for node in soup.descendants)

    html_fragment = raw if contains_tags else f'<p>{raw}</p>'
    return html_to_json(html_fragment)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Convert description.language column from HTML to Shopify JSON'
    )
    parser.add_argument('input_csv', help='Path to the input CSV')
    parser.add_argument('output_csv', help='Path for the converted CSV')
    parser.add_argument('--sep', default=DEFAULT_SEP,
                        help=f'CSV field separator (default "{DEFAULT_SEP}")')

    args = parser.parse_args()
    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    sep = args.sep

    if not in_path.exists():
        sys.exit(f'Input file not found: {in_path}')

    try:
        df = pd.read_csv(
            in_path,
            dtype=str,
            keep_default_na=False,
            sep=sep,
            quotechar='"',
            escapechar='\\',
            engine='python',
            quoting=csv.QUOTE_MINIMAL,
        )
    except Exception as exc:
        sys.exit(f'Error reading CSV: {exc}')

    if 'description.language' not in df.columns:
        sys.exit("Column 'description.language' not found in the input CSV")

    df['description.language'] = df['description.language'].apply(convert_cell)

    try:
        df.to_csv(out_path, index=False, encoding='utf-8',
                  sep=sep, quoting=csv.QUOTE_MINIMAL)
    except Exception as exc:
        sys.exit(f'Error writing CSV: {exc}')

    print(f'✅ Conversion complete → {out_path}')


if __name__ == '__main__':
    main()
