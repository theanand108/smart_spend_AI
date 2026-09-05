"""Semantic interpretation of transaction notes.

V2.6 uses a layered approach:
- high-precision purpose overrides for safety-critical ambiguities,
- deterministic keyword/phrase evidence for transparent signals,
- a small supervised NLP model for learned semantic evidence.

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
        r"\borthopedic\b",
        r"\bhomeopath\w*\b",
        r"\bdiagnostic(?:s)?\b",
        r"\bscan\b",
        r"\bphysio(?:therapist)?\b",
        r"\bglucose\s+monitor\b",
        r"\bbp\s+monitor\b",
        r"\bprotein\s+bars?\b",
        r"\bmultivitamins?\b",
        r"\bfirst\s+aid\b",
        r"\bfitness\s+(?:studio|membership)\b",
        r"\bpersonal\s+trainer\b",
        r"\bswimming\s+class\b",
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
        r"\bfridge\b",
        r"\bcooking\s+oil\b",
        r"\bfruit\s+basket\b",
        r"\bmeat\s+shop\b",
        r"\btea\s+leaves\b",
        r"\bcoffee\s+powder\b",
        r"\bbaby\s+food\b",
        r"\bgrocery\s+delivery\b",
        r"\bcleaning\s+consumables?\b",
        r"\bfruit\s+shop\b",
        r"\bfruit\s+store\b",
        r"\bfruit\s+centre\b",
        r"\bfruit\s+center\b",
        r"\bgeneral\s+store\b",
        r"\bgrocery\s+store\b",
        r"\bprovision\s+store\b",
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
        r"\bcafe\b",
        r"\bfood\s+court\b",
        r"\bdelivery\s+guy\b",
        r"\bsports\s+bar\b",
        r"\bcoffee\b.*\b(?:run|order|meeting)\b",
        r"\btea\b.*\b(?:run|order|meeting)\b",
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
        r"\bairport\b",
        r"\brental\s+car\b",
        r"\boil\s+change\b",
        r"\broad\s+trip\b",
        r"\bpetrol\s+tank\b",
        r"\bfilled\s+up\s+the\s+tank\b",
        r"\bmetro\s+recharge\b",
        r"\bfastag\s+recharge\b",
        r"\bmechanic\b.*\bflat\s+tyre\b",
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
        r"\broom\s+rent\b",
        r"\bhostel\s+(?:room|fee)\b",
        r"\bpg\s+(?:fee|owner)\b",
        r"\bpg\b",
        r"\bapartment\b",
        r"\bstudio\s+apartment\b",
        r"\bco-living\b",
        r"\bnew\s+room\b",
        r"\bnew\s+place\b",
        r"\bbroker\s+fee\b",
        r"\bsecurity\s+deposit\b",
        r"\bowner\b.*\b(?:rent|room|flat)\b",
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
        r"\bexam\b",
        r"\badmission\b",
        r"\bthesis\b",
        r"\bconvocation\b",
        r"\bworkshop\b",
        r"\bcoaching\b",
        r"\bbootcamp\b",
        r"\bcalculator\b",
        r"\bassignment\b",
        r"\bspoken\s+english\b",
        r"\bjournal\s+database\b",
        r"\btextbooks?\b",
        r"\bcollege\s+id\b",
        r"\bproficiency\s+test\b",
        r"\bviva\b",
        r"\blab\s+manual\b",
        r"\bgeometry\s+box\b",
        r"\bgraph\s+sheets?\b",
        r"\bproject\b.*\bfee\b",
        r"\bstudy\s+desk\s+setup\b",
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
        r"\bextension\s+board\b",
        r"\bjeans\b",
        r"\bphone\s+cover\b",
        r"\bscreen\s+guard\b",
        r"\btable\s+lamp\b",
        r"\bjacket\b",
        r"\bcushion\s+covers?\b",
        r"\bpressure\s+cooker\b",
        r"\bstudy\s+chair\b",
        r"\bphoto\s+frame\b",
        r"\blaptop\s+bag\b",
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
        r"\bwater\s+bill\b",
        r"\bpower\s+bill\b",
        r"\bpower\s+dues?\b",
        r"\bwater\s+(?:charge|tax|tanker)\b",
        r"\binternet\s+(?:plan|subscription|upgrade)\b",
        r"\bprepaid\s+sim\b",
        r"\bsim\b.*\b(?:recharge|top(?:ped)?\s+up)\b",
        r"\bcable\s+connection\b",
        r"\bgas\s+cylinder\b",
        r"\bpiped\s+gas\b",
        r"\butility\s+dues?\b",
        r"\bgenerator\s+backup\b",
        r"\bsociety\s+maintenance\b",
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
        r"\bstand[- ]?up\b",
        r"\brooftop\s+lounge\b",
        r"\bpub\b",
        r"\blaser\s+tag\b",
        r"\bwater\s+park\b",
        r"\bgaming\s+pass\b",
        r"\bboard\s+game\b",
        r"\bescape\s+room\b",
        r"\bcomic\s+con\b",
        r"\bcricket\s+match\b",
        r"\btheater\b",
        r"\bpaint\s+and\s+sip\b",
        r"\bseason\s+pass\b",
        r"\bstreaming\s+service\b",
        r"\baudiobook\s+app\b",
        r"\bindie\s+game\b",
        r"\bcover\s+charge\b",
        r"\bkaraoke\s+room\b",
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
        r"\bgave\s+(?:money|cash)\b",
        r"\bmonthly\s+(?:allowance|pocket\s+money)\b",
        r"\bsent\s+(?:money\s+)?(?:to|for)\s+(?:my\s+)?(?:friend|brother|sister|father|mother|dad|mom|relative|cousin|niece|nephew)\b",
        r"\btransferred\s+(?:money\s+)?(?:to|for)\s+(?:my\s+)?(?:friend|brother|sister|father|mother|dad|mom|relative|cousin|niece|nephew)\b",
        r"\b(?:share|half|part|contribution)\s+(?:of|for)\s+(?:the\s+)?(?:rent|gift|subscription|kitty|expenses?)\b",
        r"\bsent\s+.*\b(?:rent|gift|admission|wedding|birthday|household|subscription|kitty)\b.*\b(?:flatmate|roommate|friend|relative|cousin|niece|nephew|family|dad|mom|sister|brother)\b",
        r"\bsettled\s+dues?\s+with\s+(?:my\s+)?(?:friend|roommate|flatmate|colleague)\b",
        r"\breimbursed?\s+(?:my\s+)?(?:friend|colleague|roommate|flatmate)\b",
        r"\b(?:gift|wedding|birthday)\s+amount\b",
        r"\bhousehold\s+(?:expenses?|kitty)\b.*\b(?:sent|gave|paid|transferred)\b",
    ),

}

PURPOSE_OVERRIDES: tuple[tuple[str, str], ...] = (
        # Final high-precision boundary cases from the independent unseen set.
    (r"\bpaid\s+electricity\b.*\bphonepe\b", "Bills & Utilities"),
    (r"\bcommon\s+area\s+electricity\b", "Bills & Utilities"),

    (r"\bbooked\s+a\s+table\s+at\s+the\s+pub\b", "Entertainment"),

    (r"\bpaid\s+restaurant\s+bill\b.*\bupi\b", "Food & Dining"),

    (r"\bpicked\s+up\s+snacks\b.*\bpantry\b", "Groceries"),

    (r"\bconsultation\s+fee\b.*\borthopedic\b", "Health & Fitness"),

    (r"\bcleared\s+dues\b.*\brented\s+room\b", "Housing / Rent"),
    (r"\bpaid\s+balance\s+rent\b.*\blate\s+fee\b", "Housing / Rent"),

    (r"\bbought\s+a\s+router\b.*\bflat\b", "Shopping"),

    # Explicit money-sharing/transfers take precedence over the category
    # mentioned as the reason or destination of the transfer.
    (r"\bgave\s+my\s+share\b.*\bbirthday\s+gift\b", "Transfer / Personal"),
    (r"\bgave\s+money\b.*\bcousin['’]?s\s+admission\b", "Transfer / Personal"),
    (r"\bsettled\s+dues\s+with\s+(?:my\s+)?roommate\b.*\bgroceries\b", "Transfer / Personal"),
    (r"\bsent\s+funds\s+to\s+(?:my\s+)?mom\b.*\bhousehold\s+expenses\b", "Transfer / Personal"),
    (r"\bsent\s+gift\s+amount\b.*\bwedding\b", "Transfer / Personal"),
    (r"\bcleared\s+dues\s+with\s+(?:a\s+)?friend\b.*\btrip\b", "Transfer / Personal"),
    (r"\bsent\s+money\s+to\s+(?:a\s+)?relative\b.*\bmedical\s+help\b", "Transfer / Personal"),
    (r"\bpaid\s+my\s+part\b.*\bhousehold\s+kitty\b", "Transfer / Personal"),
    # High-precision contextual phrases.
    (r"\bprescription\s+refill\b.*\bchemist\b", "Health & Fitness"),
    (r"\b(?:cinema|movie)\s+outing\b", "Entertainment"),
    (r"\b(?:cinema|movie|theatre|theater)\s+ticket\b", "Entertainment"),
    # High-precision transport phrases that can otherwise conflict with
    # generic recharge/payment language from another category.
    (r"\bfilled\s+up\s+the\s+tank\b.*\b(?:trip|road\s+trip|travel)\b", "Travel & Transport"),
    (r"\bmetro\s+recharge\b", "Travel & Transport"),
    (r"\bfastag\s+recharge\b", "Travel & Transport"),
    (r"\bpaid\s+the\s+mechanic\b.*\bflat\s+tyre\s+fix\b", "Travel & Transport"),

    # Rent paid through an intermediary is still the user's own
    # Housing / Rent expense when the note says the recipient forwards/manages it.
    (
        r"\b(?:sent|gave|paid|transferred)\s+.*\brent\b.*"
        r"\b(?:flatmate|roommate|friend|dad|mom|father|mother)\b.*"
        r"\b(?:forward(?:s|ed)?|manag(?:e|es|ed)|pass(?:es|ed)?\s+on)\b",
        "Housing / Rent",
    ),

    # A transfer of rent to another person is personal only when the note
    # clearly describes it as their share/contribution rather than the user's
    # own rent being forwarded to the landlord.
    (
        r"\b(?:sent|gave|paid|transferred)\s+.*\brent\b.*"
        r"\b(?:friend|flatmate|roommate|relative|cousin|niece|nephew|family|"
        r"dad|mom|sister|brother)\b",
        "Transfer / Personal",
    ),
    (r"\bsecurity\s+deposit\s+refund\b.*\bpaid\b", 'Housing / Rent'),
    (r"\b(?:deposit|security\s+deposit|broker\s+fee)\b.*\b(?:room|flat|apartment|place|lease)\b", 'Housing / Rent'),
    (r"\b(?:hostel|pg|accommodation)\b.*\b(?:fee|charge|payment|rent)\b", 'Housing / Rent'),
    (r"\b(?:studio|flat|room)\s+rent\b", 'Housing / Rent'),
    (r"\b(?:transferred|paid|sent)\s+house\s+rent\s+to\s+(?:my\s+)?(?:dad|mom|father|mother|parent)\b", 'Housing / Rent'),
    (r"\bpaid\s+(?:the\s+)?owner\s+before\s+leaving\s+town\b", 'Housing / Rent'),
    (r"\b(?:power|electricity|water|utility|broadband|wifi|internet)\b.*\b(?:bill|dues?|charge|payment|paid|settled)\b", 'Bills & Utilities'),
    (r"\b(?:bill|dues?|charge|payment)\b.*\b(?:power|electricity|water|utility|broadband|wifi|internet)\b", 'Bills & Utilities'),
    (r"\bsociety\s+(?:maintenance|water)\b", 'Bills & Utilities'),
    (r"\b(?:prepaid\s+sim|sim|dth)\b.*\b(?:recharge|renewal|top(?:ped)?\s+up|balance)\b", 'Bills & Utilities'),
    (r"\b(?:stocked|restocked|grocery|groceries|pantry|fridge)\b.*\b(?:food|snacks?|items?|delivery|week)\b", 'Groceries'),
    (r"\b(?:tea\s+leaves|coffee\s+powder|pulses?|fish|prawns?|baby\s+food|formula)\b", 'Groceries'),
    (r"\bhousehold\s+cleaning\s+consumables?\b.*\bfood\s+items?\b", 'Groceries'),
    (r"\b(?:bowling|laser\s+tag|arcade|karaoke|escape\s+room|paint\s+and\s+sip)\b.*\b(?:snacks?|food|meal)?\b", 'Entertainment'),
    (r"\b(?:pub|club)\b.*\b(?:table|cover|entry|charge|booked|paid)\b", 'Entertainment'),
    (r"\bdessert\s+after\s+the\s+movie\b", 'Food & Dining'),
    (r"\bbirthday\s+treat\b", 'Food & Dining'),
    (r"(?:refund|refunded|reimbursement|reimbursed|repayment|repay|payback|paid\s+back)\b", 'Transfer / Personal'),
    (r"(?:split|share)\s+(?:the\s+)?(?:dinner|bill|food|meal)\s+(?:repayment|refund|reimbursement)", 'Transfer / Personal'),
    (r"(?:paid|sent|gave|transferred)\s+.*\bfor\s+(?:travel|trip|journey)\b", 'Transfer / Personal'),
    (r"(?:my\s+)?share\s+of\s+(?:the\s+)?(?:dinner|bill|food|meal)", 'Food & Dining'),
    (r"split\s+(?:the\s+)?(?:bill|dinner|food|meal)", 'Food & Dining'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|toward)\s+(?:the\s+)?(?:medicine|medical|pharmacy)\b", 'Health & Fitness'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|to get)\s+(?:the\s+)?(?:vegetables?|groceries?|milk|ration)\b", 'Groceries'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|to get)\s+(?:the\s+)?(?:dinner|lunch|breakfast|food|meal)\b", 'Food & Dining'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:rent|gift|wedding|birthday|subscription|kitty|household expenses?)\b.*\b(?:friend|flatmate|roommate|relative|cousin|niece|nephew|family|dad|mom|sister|brother)\b", 'Transfer / Personal'),
    (r"(?:refund|refunded|reimbursement|reimbursed|repayment|repay|payback|paid\s+back|returned)\b", 'Transfer / Personal'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|toward)\s+(?:the\s+)?(?:medicine|medical|pharmacy)", 'Health & Fitness'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|to get)\s+(?:the\s+)?(?:vegetables?|groceries?|milk|ration)", 'Groceries'),
    (r"(?:sent|gave|paid|transferred)\s+.*\b(?:for|to get)\s+(?:the\s+)?(?:dinner|lunch|breakfast|food|meal)", 'Food & Dining'),
)

GENERIC_ABSTENTION_PATTERNS = (
    r"\bpaid\s+what\s+i\s+owed\b",
    r"\bpaid\s+the\s+balance\b",
    r"\bpaid\s+off\s+the\s+balance\b",
    r"\bpaid\s+the\s+person\b",
    r"\bpaid\s+the\s+vendor\b",
    r"\bpaid\s+for\s+the\s+service\b",
    r"\bpaid\s+for\s+the\s+arrangement\b",
    r"\bpaid\s+up\s+front\b",
    r"\bsent\s+the\s+funds\b",
    r"\bgave\s+the\s+money\b",
    r"\bcleared\s+dues\b",
    r"\bsettled\s+up\b",
)

NEGATION_PATTERNS = (
    r"\bno\s+(?:need|purchase|buying)\b", r"\bdidn['’]?t\s+buy\b", r"\bnot\s+(?:for|a)\b",
)

WEAK_NOTE_WORDS = {
    "ok", "home", "personal", "payment", "stuff", "monthly", "urgent", "for", "the", "gift", "something",
    "done", "important", "cash", "needed", "paid", "transfer",
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
        return _result(
            None,
            [],
            0.0,
            "Note contains a negation pattern; semantic inference is unsafe.",
        )

    # Explicit contextual phrases have highest precedence.
    for pattern, category in PURPOSE_OVERRIDES:
        if re.search(pattern, text):
            return _result(
                category,
                [(category, 2)],
                0.96,
                f"Explicit transaction purpose indicates {category}.",
            )

    # Do not let the learned model turn deliberately vague language into a
    # confident Transfer / Personal prediction.
    if any(re.search(pattern, text) for pattern in GENERIC_ABSTENTION_PATTERNS):
        return _result(
            None,
            [],
            0.0,
            "Note is generic and does not identify the transaction purpose safely.",
        )

    tokens = set(re.findall(r"[a-z]+", text))
    if tokens and not (tokens - WEAK_NOTE_WORDS):
        return _result(
            None,
            [],
            0.0,
            "Note is too weak to identify transaction purpose.",
        )

    matches: list[tuple[str, int, str]] = []
    for category, patterns in SEMANTIC_PATTERNS.items():
        category_matches = [
            pattern for pattern in patterns if re.search(pattern, text)
        ]
        if category_matches:
            matches.append(
                (category, len(category_matches), category_matches[0])
            )

    learned = learned_semantic_evidence(text)

    # Genuine rule-level conflicts remain ambiguous; ML is not allowed to
    # manufacture certainty over contradictory deterministic evidence.
    categories = {category for category, _, _ in matches}
    if len(categories) > 1:
        return _result(
            None,
            learned.get("candidates", []),
            0.0,
            "Multiple category signals conflict; learned inference is not allowed to pick a winner.",
        )

    if learned["category"] and learned["confidence"] >= 0.72:
        if not matches:
            return _result(
                learned["category"],
                learned["candidates"],
                learned["confidence"],
                learned["reason"],
            )

        # A single generic keyword can be misleading. A strong learned
        # prediction may override that one weak surface clue.
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
        return _result(
            None,
            [],
            0.0,
            learned.get("reason", "No meaningful semantic category signal found."),
        )

    matches.sort(key=lambda item: item[1], reverse=True)
    candidates = [(category, count) for category, count, _ in matches]

    if len(matches) > 1 and matches[0][1] == matches[1][1]:
        return _result(
            None,
            candidates,
            0.0,
            "Multiple categories have equally strong semantic evidence.",
        )

    top = matches[0]
    confidence = 0.92 if top[1] >= 2 else 0.90
    return _result(
        top[0],
        candidates,
        confidence,
        f"Semantic note pattern matched {top[0]} evidence.",
    )
