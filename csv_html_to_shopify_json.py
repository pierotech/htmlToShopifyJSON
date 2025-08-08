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
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_SEP = ';'  # default CSV delimiter

# Map HTML list tag → Shopify listType
LIST_TYPE_MAP = {'ul': 'unordered', 'ol': 'ordered'}

# Tags that should be treated as block elements
BLOCK_TAGS = {'p', 'div', 'section', 'article', 'main', 'aside', 'header', 'footer', 
              'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'blockquote', 'pre'}

# Tags that should be treated as inline formatting
INLINE_FORMATTING_TAGS = {'em', 'i', 'strong', 'b', 'u', 's', 'strike', 'del', 
                          'sup', 'sub', 'code', 'kbd', 'mark'}

# Tags that should be ignored/skipped entirely (no content extracted)
SKIP_TAGS = {'script', 'style', 'noscript', 'hr', 'br'}


def html_to_json(html: str) -> str:
    """Convert an HTML fragment to the JSON structure accepted by Shopify."""

    soup = BeautifulSoup(html, 'html.parser')

    def extract_text_with_formatting(element):
        """Recursively extract text with inline formatting from an element."""
        results = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip():  # Only add non-whitespace text
                    # Preserve single spaces between words
                    if results and text.startswith(' '):
                        text = ' ' + text.lstrip()
                    if text.endswith(' ') and text.strip():
                        text = text.rstrip() + ' '
                    if text.strip():
                        results.append({'type': 'text', 'value': text.strip()})
            elif isinstance(child, Tag):
                if child.name in SKIP_TAGS:
                    continue
                elif child.name == 'a':
                    link_text = child.get_text().strip()
                    if link_text:
                        link_obj = {
                            'type': 'link',
                            'url': child.get('href', ''),
                            'children': [{'type': 'text', 'value': link_text}]
                        }
                        if child.has_attr('title'):
                            link_obj['title'] = child['title']
                        results.append(link_obj)
                elif child.name in ['em', 'i']:
                    nested_content = extract_text_with_formatting(child)
                    for item in nested_content:
                        if item['type'] == 'text':
                            item['italic'] = True
                        results.append(item)
                elif child.name in ['strong', 'b']:
                    nested_content = extract_text_with_formatting(child)
                    for item in nested_content:
                        if item['type'] == 'text':
                            item['bold'] = True
                        results.append(item)
                elif child.name in ['u']:
                    nested_content = extract_text_with_formatting(child)
                    for item in nested_content:
                        if item['type'] == 'text':
                            item['underline'] = True
                        results.append(item)
                elif child.name in ['s', 'strike', 'del']:
                    nested_content = extract_text_with_formatting(child)
                    for item in nested_content:
                        if item['type'] == 'text':
                            item['strikethrough'] = True
                        results.append(item)
                elif child.name == 'span' or child.name in INLINE_FORMATTING_TAGS:
                    # For span and other inline tags, recursively extract content
                    results.extend(extract_text_with_formatting(child))
                else:
                    # For any other tag, just get the text content
                    text = child.get_text().strip()
                    if text:
                        results.append({'type': 'text', 'value': text})
        
        return results

    def parse_block_element(element):
        """Parse a block-level element and return Shopify JSON structure."""
        
        # Skip certain tags entirely
        if element.name in SKIP_TAGS:
            return None
            
        # Headings
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text(strip=True)
            if text:
                return {
                    'type': 'heading',
                    'level': int(element.name[1]),
                    'children': [{'type': 'text', 'value': text}]
                }
            return None
            
        # Lists
        elif element.name in ['ul', 'ol']:
            list_type = LIST_TYPE_MAP[element.name]
            list_items = []
            
            for li in element.find_all('li', recursive=False):
                children = extract_text_with_formatting(li)
                if not children:
                    children = [{'type': 'text', 'value': ''}]
                list_items.append({
                    'type': 'list-item',
                    'children': children
                })
            
            if list_items:
                return {
                    'type': 'list',
                    'listType': list_type,
                    'children': list_items
                }
            return None
            
        # Paragraphs and other block elements
        elif element.name == 'p' or element.name in BLOCK_TAGS:
            # Check if this block contains other blocks
            nested_blocks = element.find_all(BLOCK_TAGS, recursive=False)
            
            if nested_blocks:
                # This block contains other blocks, process them recursively
                results = []
                for child in element.children:
                    if isinstance(child, Tag) and child.name in BLOCK_TAGS:
                        parsed = parse_block_element(child)
                        if parsed:
                            results.append(parsed)
                    elif isinstance(child, Tag) or (isinstance(child, NavigableString) and str(child).strip()):
                        # Collect inline content between blocks
                        temp_container = BeautifulSoup('<temp></temp>', 'html.parser').temp
                        temp_container.append(child)
                        inline_content = extract_text_with_formatting(temp_container)
                        if inline_content:
                            results.append({
                                'type': 'paragraph',
                                'children': inline_content
                            })
                return results if results else None
            else:
                # This block only contains inline content
                children = extract_text_with_formatting(element)
                if children:
                    return {'type': 'paragraph', 'children': children}
                # Return empty paragraph if needed
                elif element.name == 'p':
                    return {'type': 'paragraph', 'children': [{'type': 'text', 'value': ''}]}
                return None
        
        return None

    def process_soup_children(parent):
        """Process all children of a BeautifulSoup element."""
        results = []
        current_inline_content = []
        
        for child in parent.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    current_inline_content.append(child)
            elif isinstance(child, Tag):
                if child.name in SKIP_TAGS:
                    # Skip these tags entirely
                    continue
                elif child.name in BLOCK_TAGS or child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol']:
                    # First, flush any accumulated inline content
                    if current_inline_content:
                        temp_container = BeautifulSoup('<temp></temp>', 'html.parser').temp
                        for item in current_inline_content:
                            temp_container.append(item)
                        inline_children = extract_text_with_formatting(temp_container)
                        if inline_children:
                            results.append({
                                'type': 'paragraph',
                                'children': inline_children
                            })
                        current_inline_content = []
                    
                    # Then process the block element
                    parsed = parse_block_element(child)
                    if parsed:
                        if isinstance(parsed, list):
                            results.extend(parsed)
                        else:
                            results.append(parsed)
                else:
                    # Inline element, accumulate it
                    current_inline_content.append(child)
        
        # Flush any remaining inline content
        if current_inline_content:
            temp_container = BeautifulSoup('<temp></temp>', 'html.parser').temp
            for item in current_inline_content:
                if isinstance(item, NavigableString):
                    temp_container.append(str(item))
                else:
                    temp_container.append(item)
            inline_children = extract_text_with_formatting(temp_container)
            if inline_children:
                results.append({
                    'type': 'paragraph',
                    'children': inline_children
                })
        
        return results

    # Build root
    root = {'type': 'root', 'children': []}
    
    # Process all top-level content
    children = process_soup_children(soup)
    root['children'] = children

    # Ensure we have at least one paragraph if completely empty
    if not root['children']:
        root['children'].append({
            'type': 'paragraph',
            'children': [{'type': 'text', 'value': ''}]
        })

    return json.dumps(root, ensure_ascii=False)


def convert_cell(text: str) -> str:
    """Convert a CSV cell (HTML or plain text) to Shopify JSON."""
    if text is None or str(text).strip() == '':
        return ''

    raw = str(text).strip()
    
    # Check if it contains HTML tags
    soup = BeautifulSoup(raw, 'html.parser')
    has_tags = bool(soup.find())
    
    if not has_tags:
        # Plain text - wrap in paragraph
        html_fragment = f'<p>{raw}</p>'
    else:
        # Already HTML
        html_fragment = raw
    
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
