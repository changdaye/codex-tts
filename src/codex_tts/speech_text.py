import re

MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(((?:https?://|www\.)[^)]+)\)")
BARE_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+")
INLINE_WHITESPACE_PATTERN = re.compile(r"[ \t]+")
SPACE_BEFORE_PUNCTUATION_PATTERN = re.compile(r"\s+([.,!?;:])")


def _replace_bare_url(match: re.Match[str]) -> str:
    token = match.group(0)
    trailing = ""
    while token and token[-1] in ".,!?;:)]":
        trailing = token[-1] + trailing
        token = token[:-1]
    return trailing


def sanitize_for_speech(text: str) -> str:
    sanitized = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    sanitized = BARE_URL_PATTERN.sub(_replace_bare_url, sanitized)

    lines: list[str] = []
    for raw_line in sanitized.splitlines():
        line = INLINE_WHITESPACE_PATTERN.sub(" ", raw_line).strip()
        line = SPACE_BEFORE_PUNCTUATION_PATTERN.sub(r"\1", line)
        if line:
            lines.append(line)

    return "\n".join(lines).strip()
