"""Text cleaning and sentence splitting (no external NLP models)."""
import html
import re

_TAG = re.compile(r"<[^>]+>")
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+|<br\s*/?>", re.I)
_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    text = html.unescape(text or "")
    text = text.replace("<br />", "\n").replace("<br>", "\n")
    text = _TAG.sub(" ", text)
    return text


def sentences(text: str, min_chars: int = 12, max_chars: int = 400) -> list:
    out = []
    for s in _SPLIT.split(clean(text)):
        s = _WS.sub(" ", s).strip()
        if min_chars <= len(s) <= max_chars:
            out.append(s)
    return out
