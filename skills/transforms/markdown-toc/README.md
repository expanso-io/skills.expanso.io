# markdown-toc

Extract table of contents from markdown documents.

## Usage

```bash
echo "# Title
## Section 1
## Section 2
### Subsection" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "headings": ["# Title", "## Section 1", "## Section 2", "### Subsection"],
  "heading_count": 4,
  "h1_count": 1,
  "h2_count": 2,
  "h3_count": 1
}
```
