# HTML to Shopify JSON Converter V2

A robust Python script that converts HTML content to Shopify Rich Text JSON format, designed for processing CSV files with HTML descriptions and converting them to Shopify-compatible metafield format.

## Features

This script converts HTML/plain-text content from CSV files into the JSON structure required by Shopify's Rich Text metafields, supporting a comprehensive range of HTML elements.

## Supported HTML Elements

### Text Formatting (Inline Elements)
- **Bold**: `<strong>`, `<b>`
- **Italic**: `<em>`, `<i>`
- **Links**: `<a>` (with href and optional title attributes)

### Headings
- `<h1>` through `<h6>` - Converted to Shopify heading nodes with appropriate levels

### Lists
- **Unordered lists**: `<ul>` with `<li>` items
- **Ordered lists**: `<ol>` with `<li>` items

### Block Elements
The script recognizes and processes the following as block-level elements:
- **Content sections**: `<p>`, `<div>`, `<section>`, `<article>`, `<main>`, `<aside>`, `<header>`, `<footer>`, `<nav>`
- **Quotes and code**: `<blockquote>`, `<pre>`
- **Figures**: `<figure>`, `<figcaption>`
- **Tables**: `<table>`, `<thead>`, `<tbody>`, `<tfoot>`, `<tr>`, `<td>`, `<th>` (simplified to text representation)
- **Forms**: `<form>`, `<fieldset>`, `<legend>`
- **Other**: `<address>`, `<details>`, `<summary>`, `<hr>`, `<br>`
- **Media**: `<canvas>`, `<video>`, `<audio>` (content extracted as text)

### Special Handling

#### Tables
Tables are converted to a simplified text representation using pipe separators:
```
Cell 1 | Cell 2 | Cell 3
Data 1 | Data 2 | Data 3
```

#### Horizontal Rules and Line Breaks
- `<hr>` → Converted to a paragraph with "---"
- `<br>` → Converted to an empty paragraph

### Skipped Elements
The following elements are completely ignored (no content extracted):
- `<script>`, `<style>`, `<noscript>`
- `<iframe>`, `<embed>`, `<object>`, `<applet>`
- `<meta>`, `<link>`, `<base>`, `<title>`, `<head>`
- HTML comments

## Usage

### Basic Usage
```bash
python csv_html_to_shopify_json.py input.csv output.csv
```

### With Custom Separator
```bash
python csv_html_to_shopify_json.py input.csv output.csv --sep ','
```

### Parameters
- `input.csv`: Path to the input CSV file containing HTML in the `description.language` column
- `output.csv`: Path for the output CSV file with converted JSON
- `--sep`: CSV field separator (default: `;`, use `,` for comma-separated files)

## Requirements

- Python 3.6+
- pandas
- beautifulsoup4

### Installation
```bash
pip install pandas beautifulsoup4
```

## CSV Format

The script expects a CSV file with a column named `description.language` containing HTML or plain text content. All other columns are preserved unchanged.

### Example Input
```csv
id;title;description.language
1;Product A;<h1>Main Title</h1><p>This is a <strong>bold</strong> paragraph.</p>
2;Product B;Plain text description
```

### Example Output
```csv
id;title;description.language
1;Product A;{"type": "root", "children": [{"type": "heading", "level": 1, "children": [{"type": "text", "value": "Main Title"}]}, {"type": "paragraph", "children": [{"type": "text", "value": "This is a "}, {"type": "text", "value": "bold", "bold": true}, {"type": "text", "value": " paragraph."}]}]}
2;Product B;{"type": "root", "children": [{"type": "paragraph", "children": [{"type": "text", "value": "Plain text description"}]}]}
```

## Shopify JSON Structure

The output follows Shopify's Rich Text JSON format:
- Root node with type "root"
- Children nodes for different content types (paragraph, heading, list, etc.)
- Text nodes with optional formatting attributes (bold, italic, underline, strikethrough)
- Link nodes with URL and optional title
- List nodes with listType (ordered/unordered) and list-item children

## Notes

- The script uses BeautifulSoup for robust HTML parsing, handling most HTML variations and malformed markup
- Plain text input is automatically wrapped in a paragraph element
- Empty cells remain empty in the output
- All other CSV columns are preserved without modification
- UTF-8 encoding is used for both input and output

## Testing

The `test.html` file contains example HTML code demonstrating all supported tags and can be used to verify the conversion functionality.

## Version History

### V2.0
- Expanded block element support (30+ HTML tags)
- Improved heading handling with proper Shopify heading nodes
- Table to text conversion
- Better handling of media elements
- Enhanced skip list for non-content elements
- Refined inline formatting to focus on core text styling

### V1.0
- Initial release with basic HTML tag support
- Core paragraph, list, and text formatting