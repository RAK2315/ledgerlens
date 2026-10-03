"""Draft text from the model (Groq), cached on disk by prompt, with the template as the fallback. Code decides the numbers; the model only words them."""
from __future__ import annotations

import hashlib
import json
import os

import httpx

from .. import settings
from . import templates

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM = (
    "You write short, plain business messages for the accounts team of an Indian company. "
    "Use only the facts you are given. Do not add amounts, dates, section numbers, law references or promises that are not in the facts. "
    "Keep every rupee amount and invoice number exactly as given. No em dashes, no emoji, no capital-letter words for emphasis. "
    "Body under 130 words, polite and direct, ending with the sign-off given. "
    'Reply with JSON only: {"subject": "...", "body": "..."}'
)


def _cache_path(prompt: str):
    digest = hashlib.sha256((settings.llm_model() + "\n" + prompt).encode()).hexdigest()[:24]
    return settings.cache_dir() / "drafts" / f"{digest}.json"


def _keeps_the_facts(text: dict, facts: dict) -> bool:
    """Reject model output that lost the record number or the amount."""
    body = f"{text.get('subject', '')} {text.get('body', '')}"
    return bool(text.get("subject")) and bool(text.get("body")) and facts["record"] in body and facts["amount"] in body and "—" not in body


def _ask(prompt: str) -> dict:
    response = httpx.post(
        GROQ_URL, timeout=20,
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": settings.llm_model(), "temperature": 0.2, "response_format": {"type": "json_object"}, "reasoning_effort": "low", "max_tokens": 700,
              "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]},
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def write(finding: dict, party_name: str | None) -> dict:
    """A Draft for a Finding: kind, recipient, subject, body and source (llm, cache or template)."""
    base = templates.build(finding, party_name)
    mode = settings.llm_mode()
    if mode == "template_only":
        return {**base, "source": "template"}
    facts = templates.facts(finding, party_name)
    prompt = json.dumps({"message_kind": base["kind"], "to": base["recipient"], "facts": facts, "sign_off": templates.SIGN_OFF,
                         "plain_version_to_improve": base["body"]}, sort_keys=True)
    path = _cache_path(prompt)
    if path.exists():
        return {**base, **json.loads(path.read_text(encoding="utf-8")), "source": "cache"}
    if mode != "live":
        return {**base, "source": "template"}
    try:
        text = _ask(prompt)
    except (httpx.HTTPError, KeyError, ValueError):
        return {**base, "source": "template"}
    if not _keeps_the_facts(text, facts):
        return {**base, "source": "template"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"subject": text["subject"], "body": text["body"]}, indent=1), encoding="utf-8")
    return {**base, "subject": text["subject"], "body": text["body"], "source": "llm"}
