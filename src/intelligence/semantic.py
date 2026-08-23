"""Semantic interpretation of transaction notes.

This is intentionally a small, deterministic semantic layer for V2.4.
It turns natural-language note patterns into evidence without making the
final categorization decision. A learned NLP model can replace this module
later without changing the decision engine.
"""

from __future__ import annotations

import re
from typing import Any

SEMANTIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "Health & Fitness": (r"\bmedicine(?:s)?\b", r"\btablet(?:s)?\b", r"\bpharmacy\b", r"\bdoctor(?:'s)?\b", r"\bhospital\b"),
    "Groceries": (r"\bvegetables?\b", r"\bgrocer(?:y|ies)\b", r"\bkirana\b", r"\bmilk\b", r"\bration\b"),
    "Food & Dining": (r"\btea\b", r"\bchai\b", r"\bcoffee\b", r"\blunch\b", r"\bdinner\b", r"\bbreakfast\b", r"\bmeal\b", r"\bcanteen\b", r"\brestaurant\b", r"\bfood\b"),
    "Travel & Transport": (r"\bauto\b", r"\brickshaw\b", r"\bcab\b", r"\buber\b", r"\bola\b", r"\bpetrol\b", r"\bfuel\b", r"\bride\b", r"\bticket\b"),
    "Housing / Rent": (r"\brent\b", r"\blandlord\b", r"\broom\s+rent\b"),
    "Education": (r"\bcollege\b", r"\bsemester\b", r"\btuition\b", r"\bfee(?:s)?\b", r"\bstationery\b", r"\bnotebook(?:s)?\b"),
    "Transfer / Personal": (r"\bmy\s+share(?:\s+of\s+(?:the\s+)?)?(?:dinner|bill|food)\b", r"\bmy\s+part\b", r"\bsplit\s+(?:the\s+)?(?:bill|dinner|food)\b", r"\bpay(?:ing)?\s+back\b", r"\bpaid\s+back\b", r"\bmoney\s+i\s+owed\b", r"\bsent\s+(?:money\s+)?(?:to|for)\s+(?:my\s+)?friend\b", r"\btransferred\s+(?:money\s+)?(?:to|for)\s+(?:my\s+)?friend\b", r"\breimbursement\b"),
    "Shopping": (r"\bclothes?\b", r"\bshopping\b", r"\bkurti\b", r"\bhousehold\b", r"\bhardware\b"),
    "Bills & Utilities": (r"\brecharge\b", r"\belectricity\s+bill\b", r"\bwater\s+bill\b", r"\binternet\s+bill\b"),
    "Entertainment": (r"\bmovie\b", r"\bnetflix\b", r"\bspotify\b", r"\bconcert\b"),
}

NEGATION_PATTERNS = (r"\bno\s+(?:need|purchase|buying)\b", r"\bdidn['’]?t\s+buy\b", r"\bnot\s+(?:for|a)\b")


def _normalize(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def semantic_note_evidence(note: Any) -> dict[str, Any]:
    """Return semantic candidates and their strength without choosing a winner."""
    text = _normalize(note)
    if not text:
        return {"category": None, "candidates": [], "confidence": 0.0, "reason": "No note provided."}
    if any(re.search(pattern, text) for pattern in NEGATION_PATTERNS):
        return {"category": None, "candidates": [], "confidence": 0.0, "reason": "Note contains a negation pattern; semantic category inference is unsafe."}

    matches: list[tuple[str, int, str]] = []
    for category, patterns in SEMANTIC_PATTERNS.items():
        category_matches = [pattern for pattern in patterns if re.search(pattern, text)]
        if category_matches:
            matches.append((category, len(category_matches), category_matches[0]))
    if not matches:
        return {"category": None, "candidates": [], "confidence": 0.0, "reason": "No meaningful semantic category signal found."}

    matches.sort(key=lambda item: item[1], reverse=True)
    candidates = [(category, count) for category, count, _ in matches]
    if len(matches) > 1 and matches[0][1] == matches[1][1]:
        return {"category": None, "candidates": candidates, "confidence": 0.0, "reason": "Multiple categories have equally strong semantic evidence."}

    top = matches[0]
    confidence = 0.92 if top[1] >= 2 else 0.90
    return {"category": top[0], "candidates": candidates, "confidence": confidence, "reason": f"Semantic note pattern matched {top[0]} evidence."}
