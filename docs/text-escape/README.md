# text-escape

Escape special characters for URL and HTML.

## Usage

```bash
echo "Hello <World> & Friends" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original": "Hello <World> & Friends",
  "url_escaped": "Hello+%3CWorld%3E+%26+Friends",
  "html_escaped": "Hello &lt;World&gt; &amp; Friends"
}
```
