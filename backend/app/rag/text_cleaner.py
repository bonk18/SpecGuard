"""Conservative safety-text normalization."""

from __future__ import annotations

import re
from collections import Counter

from app.rag.models import DocumentPage


def clean_text(text: str) -> str:
    """Normalize layout noise without paraphrasing safety instructions."""

    # Null bytes and CRLF are extraction artifacts; preserving words and
    # punctuation matters more than making prose look cosmetically perfect.
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    # Only join an obvious word split at a line boundary. We do not remove
    # arbitrary hyphens because equipment identifiers and units may contain them.
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    output: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank:
                output.append("")
            previous_blank = True
            continue
        output.append(line)
        previous_blank = False
    return "\n".join(output).strip()


def clean_pages(pages: list[DocumentPage]) -> list[DocumentPage]:
    """Clean pages and remove only headers/footers repeated on multiple pages."""

    cleaned = [page.model_copy(update={"text": clean_text(page.text)}) for page in pages]
    if len(cleaned) < 2:
        return cleaned

    first_lines = [page.text.splitlines()[0] for page in cleaned if page.text.splitlines()]
    last_lines = [page.text.splitlines()[-1] for page in cleaned if page.text.splitlines()]
    repeated = {
        line for line, count in Counter(first_lines).items() if count >= 2
    } | {line for line, count in Counter(last_lines).items() if count >= 2}
    if not repeated:
        return cleaned

    result: list[DocumentPage] = []
    for page in cleaned:
        lines = page.text.splitlines()
        if lines and lines[0] in repeated:
            lines = lines[1:]
        if lines and lines[-1] in repeated:
            lines = lines[:-1]
        result.append(page.model_copy(update={"text": clean_text("\n".join(lines))}))
    return result
