"""Convert Markdown into standalone, styled HTML pages.

Usage:
    uv run md2html.py                                  # build the whole site (see below)
    uv run md2html.py notes.md                         # writes notes.html next to it
    uv run md2html.py notes.md -o site/index.html      # writes elsewhere and copies local images

Site mode: every <folder>/index.md is converted to <folder>/index.html, and a root
index.html is generated that links to each page using its first heading and
first paragraph. To add a page, create a new folder with an index.md and rebuild.

When the output goes to a different folder, any local images the page uses
(e.g. images/42032.jpg) are copied alongside it so the page still works.
"""

import argparse
import html
import re
import shutil
from pathlib import Path

import markdown

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #f7f7f5; --surface: #ffffff; --text: #1f2328; --muted: #59636e;
    --border: #d8dee4; --accent: #c8102e; --row-alt: #f6f8fa;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0d1117; --surface: #161b22; --text: #e6edf3; --muted: #9198a1;
      --border: #30363d; --accent: #ff6b6b; --row-alt: #1c2128;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 32px 16px 64px; }}
  h1 {{ font-size: 2.2rem; margin: 0 0 8px; }}
  h2 {{ margin-top: 48px; padding-bottom: 6px; border-bottom: 3px solid var(--accent); }}
  a {{ color: var(--accent); }}
  hr {{ border: 0; border-top: 1px solid var(--border); margin: 40px 0; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{
    width: 100%; border-collapse: collapse; background: var(--surface);
    border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
  }}
  th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  th {{ text-align: left; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }}
  tbody tr:nth-child(even) {{ background: var(--row-alt); }}
  td img {{ display: block; max-width: 160px; height: auto; border-radius: 6px; background: #fff; }}
  em {{ color: var(--muted); }}
  nav.home {{ margin-bottom: 16px; font-size: 0.9rem; }}
  nav.home a {{ text-decoration: none; }}
</style>
</head>
<body>
<main>
{nav}{body}
</main>
</body>
</html>
"""


SITE_ROOT = Path(__file__).parent
SITE_TITLE = "sweetlilmre's stuff"


def page_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def page_summary(text: str) -> str:
    """First plain paragraph after the heading, used as the page's blurb on the landing page."""
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block and not block.startswith(("#", "|", "-", "*", "<", "!", ">")):
            return block
    return ""


def render(text: str, title: str, home: bool = False) -> str:
    body = markdown.markdown(text, extensions=["tables", "toc"])
    # Wrap tables so wide ones scroll on narrow screens instead of breaking the layout.
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    nav = '<nav class="home"><a href="../">&larr; All pages</a></nav>\n' if home else ""
    return TEMPLATE.format(title=html.escape(title), nav=nav, body=body)


def convert(src: Path, dest: Path, home: bool = False) -> None:
    text = src.read_text(encoding="utf-8")
    page = render(text, page_title(text, src.stem), home)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")

    if dest.parent.resolve() != src.parent.resolve():
        copy_local_images(page, src.parent, dest.parent)


def copy_local_images(body: str, src_dir: Path, dest_dir: Path) -> None:
    for ref in set(re.findall(r'<img[^>]+src="([^"]+)"', body)):
        if re.match(r"^[a-z]+:", ref) or ref.startswith("/"):
            continue  # remote or absolute — nothing to copy
        source = src_dir / ref
        if source.is_file():
            target = dest_dir / ref
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        else:
            print(f"warning: image not found: {source}")


def build_site(root: Path) -> None:
    pages = []
    for src in sorted(root.glob("*/index.md")):
        if src.parent.name.startswith("."):
            continue  # skip .venv, .git and the like
        dest = src.with_suffix(".html")
        convert(src, dest, home=True)
        print(f"wrote {dest.relative_to(root)}")
        text = src.read_text(encoding="utf-8")
        pages.append((src.parent.name, page_title(text, src.parent.name), page_summary(text)))

    lines = [f"# {SITE_TITLE}", ""]
    if pages:
        lines += ["| Page | About |", "| --- | --- |"]
        lines += [f"| [{title}]({folder}/) | {summary} |" for folder, title, summary in pages]
    else:
        lines.append("Nothing here yet.")
    (root / "index.html").write_text(render("\n".join(lines) + "\n", SITE_TITLE), encoding="utf-8")
    print(f"wrote index.html ({len(pages)} page{'s' if len(pages) != 1 else ''} listed)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown to styled HTML pages.")
    parser.add_argument("input", type=Path, nargs="?", help="Markdown file to convert (omit to build the whole site)")
    parser.add_argument("-o", "--output", type=Path, help="HTML file to write (default: same name, .html)")
    args = parser.parse_args()

    if args.input is None:
        build_site(SITE_ROOT)
        return

    dest = args.output or args.input.with_suffix(".html")
    convert(args.input, dest)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
