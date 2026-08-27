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
        r"\bmedicine(?:s)?\b",
        r"\btablet(?:s)?\b",
        r"\bpharmacy\b",
        r"\bdoctor(?:'s)?\b",
        r"\bhospital\b",
        r"\bmedical\b",
        r"\bclinic\b",
        r"\bcheckup\b",
        r"\bdiagnostic\b",
        r"\bdiagnostic scan\b",
        r"\btherapy\b",
        r"\btherapist\b",
        r"\bphysiotherapist\b",
        r"\bchiropractor\b",
        r"\bnutritionist\b",
        r"\bvaccination\b",
        r"\bdental\b",
        r"\bdentist\b",
        r"\bmultivitamin(?:s)?\b",
        r"\bfirst aid\b",
        r"\bbandage(?:s)?\b",
        r"\bantiseptic\b",
        r"\bfitness studio\b",
        r"\bpersonal trainer\b",
        r"\bpilates\b",
        r"\bswimming class\b",
        r"\bmarathon\b",
        r"\bglucose monitor\b",
        r"\bbp monitor\b",
        r"\bspectacles\b",
    ),

    "Groceries": (
        r"\bvegetables?\b",
        r"\bveggies\b",
        r"\bgrocer(?:y|ies)\b",
        r"\bkirana\b",
        r"\bmilk\b",
        r"\bration\b",
        r"\blentils?\b",
        r"\bpulses?\b",
        r"\bspices?\b",
        r"\bcooking oil\b",
        r"\bghee\b",
        r"\bflour\b",
        r"\bsugar\b",
        r"\bsalt\b",
        r"\bfruit basket\b",
        r"\bpantry\b",
        r"\bcereals?\b",
        r"\bpaneer\b",
        r"\bcurd\b",
        r"\bchicken\b",
        r"\bmeat shop\b",
        r"\bfish\b",
        r"\bprawns?\b",
        r"\bbread\b",
        r"\beggs?\b",
        r"\bjam\b",
        r"\bonions?\b",
        r"\bgarlic\b",
        r"\bcoriander\b",
        r"\bmint\b",
        r"\bbigbasket\b",
        r"\bblinkit\b",
        r"\bzepto\b",
        r"\bgrocery delivery\b",
        r"\btea leaves\b",
        r"\bcoffee powder\b",
        r"\brice sacks?\b",
        r"\bbaby food\b",
        r"\bformula\b",
        r"\bhousehold cleaning consumables\b",
    ),

    "Food & Dining": (
        r"\btea\b",
        r"\bchai\b",
        r"\bcoffee(?!\s+powder)\b",
        r"\blunch\b",
        r"\bdinner\b",
        r"\bbreakfast\b",
        r"\bmeal\b",
        r"\bcanteen\b",
        r"\brestaurant\b",
        r"\bfood\b",
        r"\bdining\b",
        r"\bcake\b",
        r"\bbakery\b",
        r"\bdhaba\b",
        r"\bpizza\b",
        r"\bbiryani\b",
        r"\brolls?\b",
        r"\bsnack(?:s)?\b",
        r"\bbrunch\b",
        r"\bdessert\b",
        r"\bjuice\b",
        r"\bthai\b",
        r"\bfood court\b",
        r"\bcoffee run\b",
        r"\btapri\b",
        r"\bstreet cart\b",
        r"\bdelivery guy\b",
        r"\bcatering\b",
        r"\brestaurant bill\b",
        r"\bsports bar\b",
        r"\bpub\b",
        r"\bhotel buffet\b",
        r"\bquick bite\b",
        r"\bcravings?\b",
    ),

    "Travel & Transport": (
        r"\bauto\b",
        r"\brickshaw\b",
        r"\bcab\b",
        r"\buber\b",
        r"\bola\b",
        r"\brapido\b",
        r"\bpetrol\b",
        r"\bfuel\b",
        r"\btravel\b",
        r"\bride\b",
        r"\bticket\b",
        r"\btrain\b",
        r"\bflight\b",
        r"\bbus\b",
        r"\bmetro\b",
        r"\bfastag\b",
        r"\bparking\b",
        r"\btoll\b",
        r"\bairport shuttle\b",
        r"\brental car\b",
        r"\bbike service\b",
        r"\boil change\b",
        r"\bmechanic\b",
        r"\bpuncture\b",
        r"\bferry\b",
        r"\bcommute\b",
        r"\bsmart card\b",
        r"\broad trip\b",
    ),

    "Housing / Rent": (
        r"\brent\b",
        r"\blandlord\b",
        r"\blandlady\b",
        r"\broom rent\b",
        r"\brented room\b",
        r"\bflat\b",
        r"\bflatmate\b",
        r"\bpg owner\b",
        r"\bpg fee\b",
        r"\bhostel room\b",
        r"\baccommodation\b",
        r"\bstudio apartment\b",
        r"\bco[- ]living\b",
        r"\bcaretaker\b",
        r"\blease\b",
        r"\bnew lease\b",
        r"\bsecurity deposit\b",
    ),

    "Education": (
        r"\bcollege\s+(?:fee|fees|tuition|payment)\b",
        r"\bsemester\b",
        r"\btuition\b",
        r"\bfee(?:s)?\b",
        r"\bstationery\b",
        r"\bnotebook(?:s)?\b",
        r"\blab manual\b",
        r"\bgate exam\b",
        r"\bcoaching institute\b",
        r"\bscientific calculator\b",
        r"\bspiral binding\b",
        r"\bthesis copies\b",
        r"\bspoken english\b",
        r"\blanguage proficiency\b",
        r"\bjournal database\b",
        r"\bengineering textbooks?\b",
        r"\bdata science bootcamp\b",
        r"\bentrance exam\b",
        r"\bexam prep\b",
        r"\bphotocopy\b",
        r"\bworkshop on campus\b",
        r"\bgraph sheets?\b",
        r"\bconvocation gown\b",
        r"\bproject viva\b",
        r"\binvigilation fee\b",
        r"\bcollege id card\b",
    ),

    "Shopping": (
        r"\bclothes?\b",
        r"\bshopping\b",
        r"\bkurti\b",
        r"\bhousehold\b",
        r"\bhardware\b",
        r"\bextension board\b",
        r"\bplumbing\b",
        r"\bsneakers?\b",
        r"\blaptop bag\b",
        r"\bformal shirt\b",
        r"\bearphones?\b",
        r"\bphone cover\b",
        r"\bscreen guard\b",
        r"\btable lamp\b",
        r"\bwinter jacket\b",
        r"\bwatch\b",
        r"\bwallet\b",
        r"\bcurtains?\b",
        r"\bcushion covers?\b",
        r"\bsmartwatch\b",
        r"\bpressure cooker\b",
        r"\brouter\b",
        r"\bmakeup\b",
        r"\bstudy chair\b",
        r"\bgift\b",
        r"\btrimmer\b",
        r"\bbedsheets?\b",
        r"\btowels?\b",
        r"\bsports shoes\b",
        r"\bbackpack\b",
        r"\bmixer\b",
        r"\bsunglasses\b",
        r"\bphoto frame\b",
        r"\braincoat\b",
    ),

    "Bills & Utilities": (
        r"\brecharge\b",
        r"\belectricity\s+bill\b",
        r"\bpower bill\b",
        r"\bwater\s+(?:bill|charge|tax|dues?)\b",
        r"\binternet\s+bill\b",
        r"\bbroadband\b",
        r"\bwifi\b",
        r"\bairtel\b",
        r"\bjio\b",
        r"\bpostpaid\b",
        r"\bdth\b",
        r"\bcable connection\b",
        r"\bgas cylinder\b",
        r"\bpiped gas\b",
        r"\butility dues\b",
        r"\butility payment\b",
        r"\bsociety maintenance\b",
        r"\bgenerator backup charge\b",
        r"\blandline\b",
        r"\bcommon area electricity\b",
    ),

    "Entertainment": (
        r"\bmovie\b",
        r"\bnetflix\b",
        r"\bspotify\b",
        r"\bconcert\b",
        r"\bshow\b",
        r"\bmusic streaming\b",
        r"\bstreaming service\b",
        r"\bstand[- ]up\b",
        r"\blounge\b",
        r"\bindie game\b",
        r"\bwater park\b",
        r"\banime\b",
        r"\blaser tag\b",
        r"\barcade\b",
        r"\bpaint and sip\b",
        r"\bcricket match\b",
        r"\bgaming pass\b",
        r"\bcover charge\b",
        r"\bclub\b",
        r"\bkaraoke\b",
        r"\bboard game\b",
        r"\bescape room\b",
        r"\bcomic con\b",
        r"\bbowling\b",
        r"\baudiobook\b",
        r"\bgo karting\b",
        r"\btheatre\b",
    ),

    "Transfer / Personal": (
        r"\blent\b",
        r"\blend(?:ing)?\b",
        r"\bloan(?:ed)?\b",
        r"\bborrow(?:ed)?\b",
        r"\bowe(?:d)?\b",
        r"\bpay(?:ing)?\s+back\b",
        r"\bpaid\s+back\b",
        r"\breturned\s+(?:the\s+)?(?:money|loan|borrowed\s+money)\b",
        r"\brefund(?:ed)?\b",
        r"\breimbursement\b",
        r"\breimbursed\b",
        r"\bpayback\b",
        r"\bmoney\s+i\s+owed\b",
        r"\bpersonal\s+transfer\b",
        r"\bupi transfer to\b",
        r"\btransferred .* to (?:my )?(?:friend|brother|sister|father|mother|dad|mom|grandma|grandmother|relative|classmate|flatmate|roommate)\b",
        r"\bsent .* to (?:my )?(?:friend|brother|sister|father|mother|dad|mom|grandma|grandmother|relative|classmate|flatmate|roommate)\b",
        r"\bgave .* (?:birthday|wedding) gift\b",
        r"\bgift amount\b",
        r"\bmonthly allowance\b",
        r"\bpocket money\b",
        r"\bhousehold kitty\b",
        r"\bsavings contribution\b",
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

    # Multiple independent rule categories are a genuine ambiguity. Do not let
    # the model manufacture certainty in this case.
    categories = {category for category, _, _ in matches}
    if len(categories) > 1:
        return _result(None, learned.get("candidates", []), 0.0, "Multiple category signals conflict; learned inference is not allowed to pick a winner.")

    if learned["category"] and learned["confidence"] >= 0.72:
        if not matches:
            return _result(
                learned["category"],
                learned["candidates"],
                learned["confidence"],
                learned["reason"],
            )

        # A single generic keyword can be misleading (for example, "ticket"
        # appears in transport notes but also in entertainment notes). Let a
        # strong learned prediction override that weak surface clue.
        if (
            len(matches) == 1
            and matches[0][1] == 1
            and learned["category"] != matches[0][0]
            and learned["confidence"] >= 0.82
        ):
            return _result(
                learned["category"],
                learned["candidates"],
                learned["confidence"],
                "Learned NLP evidence is stronger than a single generic keyword clue.",
            )

    if not matches:
        # An abstaining ML model is deliberately exposed as no semantic
        # candidates. Probability rankings are internal evidence, not a
        # user-facing category guess.
        return _result(
            None,
            [],
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
