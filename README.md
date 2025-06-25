# htmlToShopifyJSON

This script converts HTML to JSON for Shopify rich text metafields.

Also modified the script to add support for bulk HTML to JSON via CSV file to later import to Shopify.

The file `test.html` contains example HTML code with all tags currently supported by the RTE in the theme editor:

- h1 - h6
- p
- ul, ol and li
- a
- strong
- em

The script works for the test.html file but hasn't been tested for all possible combinations, syntax variations, tag attributes, etc. But since BeautifulSoup is doing the parsing, it should handle most tags.

Instructions for CSV:

<code>python3 -m venv venv</code>
<code>source venv/bin/activate</code>
<code>python3 -m pip install pandas beautifulsoup4</code>
<code>python3 csv_html_to_shopify_json.py entrada.csv salida.csv</code>
