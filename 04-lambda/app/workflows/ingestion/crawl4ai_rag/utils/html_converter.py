"""HTML to Markdown conversion utilities."""

import html
import re


def html_to_markdown(html_content: str) -> str:
    """
    Convert HTML content to markdown-formatted text.

    Handles common HTML elements like paragraphs, headers, links, lists,
    bold/italic text, code blocks, and more.

    Args:
        html_content: HTML string to convert

    Returns:
        Markdown-formatted string
    """
    if not html_content:
        return ""

    text = html_content

    # Convert line breaks
    text = re.sub(r"<br\s*/?>", "\n", text)

    # Convert paragraphs and divs
    text = re.sub(r"<p[^>]*>", "\n", text)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<div[^>]*>", "\n", text)
    text = re.sub(r"</div>", "\n", text)

    # Convert headers (h1-h6)
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h5[^>]*>(.*?)</h5>", r"\n##### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h6[^>]*>(.*?)</h6>", r"\n###### \1\n", text, flags=re.DOTALL)

    # Convert bold/strong
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)

    # Convert italic/em
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)

    # Convert strikethrough
    text = re.sub(r"<del[^>]*>(.*?)</del>", r"~~\1~~", text, flags=re.DOTALL)
    text = re.sub(r"<s[^>]*>(.*?)</s>", r"~~\1~~", text, flags=re.DOTALL)
    text = re.sub(r"<strike[^>]*>(.*?)</strike>", r"~~\1~~", text, flags=re.DOTALL)

    # Convert links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL)

    # Convert images
    text = re.sub(
        r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',
        r"![\2](\1)",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"[^>]*/?>',
        r"![\1](\2)",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r'<img[^>]*src="([^"]*)"[^>]*/?>', r"![](\1)", text, flags=re.DOTALL)

    # Convert unordered lists
    text = re.sub(r"<ul[^>]*>", "\n", text)
    text = re.sub(r"</ul>", "\n", text)

    # Convert ordered lists
    text = re.sub(r"<ol[^>]*>", "\n", text)
    text = re.sub(r"</ol>", "\n", text)

    # Convert list items (simple - doesn't handle nesting perfectly)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.DOTALL)

    # Convert code blocks (pre)
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL)

    # Convert inline code
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)

    # Convert blockquotes
    text = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>", r"\n> \1\n", text, flags=re.DOTALL)

    # Convert horizontal rules
    text = re.sub(r"<hr[^>]*/?>", "\n---\n", text)

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html.unescape(text)

    # Also handle common entities that might not be caught
    text = text.replace("&nbsp;", " ")

    # Clean up whitespace
    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse multiple blank lines into at most two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def extract_text_from_html(html_content: str) -> str:
    """
    Extract plain text from HTML, stripping all tags.

    Args:
        html_content: HTML string to extract text from

    Returns:
        Plain text with HTML tags removed
    """
    if not html_content:
        return ""

    # Remove script and style elements
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert line breaks and block elements to newlines
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)

    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)  # Collapse horizontal whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse vertical whitespace
    text = text.strip()

    return text
