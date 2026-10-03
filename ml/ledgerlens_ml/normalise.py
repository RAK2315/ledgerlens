"""Invoice ID and party name normalisers, shared by every matcher (ML_BUILD.md 4)."""
from __future__ import annotations

import re

LOOKALIKES = {"O": "0", "I": "1", "L": "1", "S": "5"}
DOC_PREFIX = re.compile(r"^(TAX\s*INVOICE|INVOICE|INV|BILL|NO)(?=[\s/\-_.#:]|\d)[\s/\-_.#:]*")
SEPARATORS = re.compile(r"[\s/\-_.]+")
FY_TOKENS = {"2324", "2425", "2526", "2627", "FY24", "FY25", "FY26", "FY27", "FY2324", "FY2425", "FY2526", "FY2627"}
# A compact code such as VEN0420001 is a 3-digit party code followed by a 4-digit serial.
COMPACT_PARTY_CODE = re.compile(r"([A-Z]+\d{3})(\d{4})")
COMPACT_FY_SERIAL = re.compile(r"(\d{4})(\d{3,})")
TRAILING_DIGITS = re.compile(r"(\d+)$")

LEGAL_WORDS = {"PVT", "PRIVATE", "LTD", "LIMITED", "LLP", "CO", "AND"}
COMPACT_SUFFIXES = ("PRIVATELIMITED", "PVTLTD", "LIMITED", "LTD", "LLP", "ANDCO")
NARRATION_PREFIX_WORDS = {"INV", "INVOICE", "BILL", "NO"}


def _fix_lookalikes(text: str) -> str:
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch not in LOOKALIKES or i + 1 >= len(chars) or not chars[i + 1].isdigit():
            continue
        # Only inside or at the start of a digit run, so the N in INV or the O in NO12 stay letters.
        if i == 0 or not chars[i - 1].isalpha():
            chars[i] = LOOKALIKES[ch]
    return "".join(chars)


def _parts(raw: object) -> list[str]:
    """Split an ID into its runs with prefixes, separators and one financial-year token removed."""
    if not isinstance(raw, str):
        return []
    text = _fix_lookalikes(raw.upper().strip())
    while True:
        stripped = DOC_PREFIX.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    parts: list[str] = []
    for part in SEPARATORS.split(text):
        if not part:
            continue
        compact = COMPACT_PARTY_CODE.fullmatch(part)
        fy_serial = COMPACT_FY_SERIAL.fullmatch(part)
        if compact:
            parts.extend(compact.groups())
        elif fy_serial and fy_serial.group(1) in FY_TOKENS:
            parts.extend(fy_serial.groups())
        else:
            parts.append(part)
    for i, part in enumerate(parts):
        rest = parts[:i] + parts[i + 1:]
        if part in FY_TOKENS and sum(ch.isdigit() for ch in "".join(rest)) >= 3:
            return rest
    return parts


def _strip_zeros(part: str) -> str:
    match = TRAILING_DIGITS.search(part)
    if not match:
        return part
    return part[: match.start()] + (match.group(1).lstrip("0") or "0")


def normalise_invoice_id(raw: object) -> str:
    parts = _parts(raw)
    if not parts:
        return ""
    return "".join(parts[:-1]) + _strip_zeros(parts[-1])


def id_serial(raw: object) -> str:
    """The final numeric run of an ID without leading zeros, or an empty string."""
    parts = _parts(raw)
    match = TRAILING_DIGITS.search(parts[-1]) if parts else None
    if not match:
        return ""
    return match.group(1).lstrip("0") or "0"


def normalise_party_name(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    text = raw.upper().replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    words = text.split()
    if len(words) == 1:
        # Bank feeds often drop the spaces: BHARATSYSTEMSPVTLTD.
        for suffix in COMPACT_SUFFIXES:
            if words[0].endswith(suffix) and len(words[0]) > len(suffix) + 2:
                words[0] = words[0][: -len(suffix)]
                break
    while words and words[-1] in LEGAL_WORDS:
        words.pop()
    return " ".join(words)


def narration_id_tokens(narration: object) -> list[str]:
    """Invoice references quoted in a bank narration of the form MODE/UTR/NAME/REF[,REF]."""
    if not isinstance(narration, str):
        return []
    segments = narration.split("/")
    if len(segments) < 4:
        return []
    tokens = []
    for token in "/".join(segments[3:]).split(","):
        token = token.strip()
        words = token.upper().split()
        if not any(ch.isdigit() for ch in token):
            continue
        if any(word.isalpha() and word not in NARRATION_PREFIX_WORDS for word in words):
            continue
        tokens.append(token)
    return tokens
