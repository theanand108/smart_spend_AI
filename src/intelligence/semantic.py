"""Semantic interpretation of transaction notes.

V2.6 uses a layered approach:
- high-precision purpose overrides for safety-critical ambiguities,
- a small supervised NLP model for learned semantic evidence,
- deterministic keyword/phrase evidence as a transparent fallback.

The ML model is evidence, not the final transaction decision. Confidence and
history are handled by the transaction-intelligence layer.
"""

from __future__ import annotations

import re
from typing import Any

from .semantic_ml import learned_semantic_evidence

SEMANTIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "Health & Fitness": (
        r"\bmedicine(?:s)?\b", r"\btablet(?:s)?\b", r"\bpharmacy\b",
        r"\bdoctor(?:'s)?\b", r"\bhospital\b", r"\bmedical\b",
    ),
    "Groceries": (
        r"\bvegetables?\b", r"\bgrocer(?:y|ies)\b", r"\bkirana\b",
        r"\bmilk\b", r"\bration\b",
    ),
    "Food & Dining": (
        r"\btea\b", r"\bchai\b", r"\bcoffee\b", r"\blunch\b",
        r"\bdinner\b", r"\bbreakfast\b", r"\bmeal\b", r"\bcanteen\b",
        r"\brestaurant\b", r"\bfood\b", r"\bdining\b", r"\bcake\b",
        r"\bbakery\b",
    ),
    "Travel & Transport": (
        r"\bauto\b", r"\brickshaw\b", r"\bcab\b", r"\buber\b",
        r"\bola\b", r"\bpetrol\b", r"\bfuel\b", r"\btravel\b",
        r"\bride\b", r"\bticket\b",
    ),
    "Housing / Rent": (r"\brent\b", r"\blandlord\b", r"\broom\s+rent\b"),
    "Education": (
        r"\bcollege\s+(?:fee|fees|tuition|payment)\b",
        r"\bsemester\b", r"\btuition\b", r"\bfee(?:s)?\b",
        r"\bstationery\b", r"\bnotebook(?:s)?\b",
    ),
    "Shopping": (
        r"\bclothes?\b", r"\bshopping\b", r"\bkurti\b", r"\bhousehold\b",
        r"\bhardware\b", r"\bextension\s+board\b", r"\bplumbing\b",
    ),
    "Bills & Utilities": (
        r"\brecharge\b", r"\belectricity\s+bill\b", r"\bwater\s+bill\b",
        r"\binternet\s+bill\b",
    ),
    "Entertainment": (
        r"\bmovie\b", r"\bnetflix\b", r"\bspotify\b", r"\bconcert\b",
    ),
    "Transfer / Personal": (
        r"\blent\b", r"\blend(?:ing)?\b", r"\bloan(?:ed)?\b",
        r"\bborrow(?:ed)?\b", r"\bowe(?:d)?\b", r"\bpay(?:ing)?\s+back\b",
        r"\bpaid\s+back\b", r"\breturned\s+(?:the\s+)?(?:money|loan|borrowed\s+money)\b",
        r"\brefund(?:ed)?\b", r"\breimbursement\b", r"\bpayback\b",
        r"\bmoney\s+i\s+owed\b", r"\bpersonal\s+transfer\b",
        r"\bgave\s+(?:money|cash)\b",
        r"\bmonthly\s+(?:allowance|pocket\s+money)\b",
        r"\bsent\s+(?:money\s+)?(?:to|for)\s+(?:my\s+)?(?:friend|brother|sister|father|mother|dad|mom)\b",
        r"\btransferred\s+(?:money\s+)?(?:to|for)\s+(?:my\s+)?(?:friend|brother|sister|father|mother|dad|mom)\b",
    ),
}

PURPOSE_OVERRIDES: tuple[tuple[str, str], ...] = (
    (r"(?:refund|refunded|reimbursement|reimbursed|repayment|repay|payback|paid\s+back|returned)\b", "Transfer / Personal"),
    (r"(?:split|share)\s+(?:the\s+)?(?:dinner|bill|food|meal)\s+(?:repayment|refund|reimbursement)", "Transfer / Personal"),
    (r"(?:paid|sent|gave|transferred)\s+.*\bfor\s+(?:travel|trip|journey)\b", "Transfer / Personal"),
    (r"(?:my\s+)?share\s+of\s+(?:the\s+)?(?:dinner|bill|food|meal)", "Food & Dining"),
    (r"split\s+(?:the\s+)?(?:bill|dinner|food|meal)", "Food & Dining"),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|toward)\s+(?:the\s+)?(?:medicine|medical|pharmacy)", "Health & Fitness"),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|to get)\s+(?:the\s+)?(?:vegetables?|groceries?|milk|ration)", "Groceries"),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|to get)\s+(?:the\s+)?(?:dinner|lunch|breakfast|food|meal)", "Food & Dining"),
)

NEGATION_PATTERNS = (
    r"\bno\s+(?:need|purchase|buying)\b",
    r"\bdidn['’]?t\s+buy\b",
    r"\bnot\s+(?:for|a)\b",
)

WEAK_NOTE_WORDS = {
    "ok", "home", "personal", "payment", "stuff", "monthly", "urgent",
    "for", "the", "gift", "something", "done", "important", "cash",
    "needed", "paid", "transfer",
}


def _normalize(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _result(
    category: str | None,
    candidates: list[tuple[str, Any]],
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "candidates": candidates,
        "confidence": confidence,
        "reason": reason,
    }


def semantic_note_evidence(note: Any) -> dict[str, Any]:
    """Extract transaction-purpose evidence from a natural-language note."""
    text = _normalize(note)
    if not text:
        return _result(None, [], 0.0, "No note provided.")

    if any(re.search(pattern, text) for pattern in NEGATION_PATTERNS):
        return _result(None, [], 0.0, "Note contains a negation pattern; semantic inference is unsafe.")

    for pattern, category in PURPOSE_OVERRIDES:
        if re.search(pattern, text):
            return _result(category, [(category, 2)], 0.96, f"Explicit transaction purpose indicates {category}.")

    # Very short/general notes are intentionally excluded from learned inference.
    # They contain little semantic signal and are better handled as Unknown.
    tokens = set(re.findall(r"[a-z]+", text))
    if tokens and not (tokens - WEAK_NOTE_WORDS):
        return _result(None, [], 0.0, "Note is too weak to identify transaction purpose.")

    matches: list[tuple[str, int, str]] = []
    for category, patterns in SEMANTIC_PATTERNS.items():
        category_matches = [pattern for pattern in patterns if re.search(pattern, text)]
        if category_matches:
            matches.append((category, len(category_matches), category_matches[0]))

    # Let the learned model resolve notes that are outside the hand-written
    # vocabulary. This is the key transition from keyword memorization to
    # learned language patterns while keeping transparent rules as a fallback.
    learned = learned_semantic_evidence(text)
    if learned["category"] and learned["confidence"] >= 0.72:
        if not matches:
            return _result(
                learned["category"],
                learned["candidates"],
                learned["confidence"],
                learned["reason"],
            )

        # If deterministic evidence is internally conflicting, a sufficiently
        # separated learned prediction may resolve the conflict.
        categories = {category for category, _, _ in matches}
        if len(categories) > 1 and learned["category"] not in categories:
            return _result(None, learned["candidates"], 0.0, "Rule evidence conflicts with the learned model; no category selected.")
        if len(categories) > 1 and learned["category"] in categories:
            return _result(
                learned["category"],
                learned["candidates"],
                learned["confidence"],
                "Learned NLP evidence resolves conflicting surface-level clues.",
            )

    if not matches:
        return _result(
            None,
            learned.get("candidates", []),
            0.0,
            learned.get("reason", "No meaningful semantic category signal found."),
        )

    matches.sort(key=lambda item: item[1], reverse=True)
    candidates = [(category, count) for category, count, _ in matches]
    if len(matches) > 1 and matches[0][1] == matches[1][1]:
        return _result(None, candidates, 0.0, "Multiple categories have equally strong semantic evidence.")

    top = matches[0]
    confidence = 0.92 if top[1] >= 2 else 0.90
    return _result(top[0], candidates, confidence, f"Semantic note pattern matched {top[0]} evidence.")
