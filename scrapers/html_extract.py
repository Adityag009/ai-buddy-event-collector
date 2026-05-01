"""HTML → plain text for LLM."""

from __future__ import annotations

from bs4 import BeautifulSoup


def html_to_plain_text(html: str, *, max_chars: int | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title_el = soup.title
    title = title_el.get_text(strip=True) if title_el else ""
    body_text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in body_text.splitlines() if ln.strip()]
    text = "\n".join(lines)
    if title:
        text = f"# {title}\n\n{text}"
    if max_chars is not None and len(text) > max_chars:
        text = text[:max_chars] + "\n\n[truncated]"
    return text
