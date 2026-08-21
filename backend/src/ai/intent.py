"""Intent detection for the QStock assistant.

Routing is deliberately conservative: questions asking for live inventory
state go to SQL, while explanatory/procedural questions stay in general chat.
The rules cover both English and French because the product supports both UI
languages.
"""

from dataclasses import dataclass
from enum import Enum
import re


class Intent(str, Enum):
    INVENTORY_SQL = "inventory_sql"
    GENERAL_CHAT = "general_chat"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float
    reason: str


_DATA_ACTION_RE = re.compile(
    r"\b("
    r"show|list|find|search|which|who|what|when|where|how many|count|"
    r"compare|statistics|stats|highest|lowest|most|least|borrowed|available|"
    r"maintenance|overdue|stock|inventory|items?|users?|transactions?|requests?|"
    r"affiche|afficher|liste|lister|trouve|trouver|recherche|rechercher|"
    r"quel(?:le)?s?|qui|combien|compte|comparer|statistiques?|plus|moins|"
    r"emprunte(?:s|e)?|disponible(?:s)?|maintenance|retard(?:s)?|stock|"
    r"inventaire|article(?:s)?|utilisateur(?:s)?|transaction(?:s)?|demande(?:s)?|"
    r"où|ou|emplacement|emplacements"
    r")\b",
    re.IGNORECASE,
)

# Existence questions are live-data requests even when they contain no
# explicit inventory noun. The item name itself is resolved later by the
# deterministic query planner (e.g. "scissors" -> canonical "Ciseaux").
_EXISTENCE_RE = re.compile(
    r"(?:"
    r"\bdo\s+(?:we|you)\s+have\b|"
    r"\bdoes\s+qstock\s+have\b|"
    r"\bis\s+there\b|"
    r"\bare\s+there\b|"
    r"\bavons[- ]nous\b|"
    r"\bavez[- ]vous\b|"
    r"\best[- ]ce\s+qu['’]on\s+a\b|"
    r"\best[- ]ce\s+que\s+nous\s+avons\b|"
    r"\by\s+a(?:-t-il|-t il|-il| il)\b"
    r")",
    re.IGNORECASE,
)

_GENERAL_RE = re.compile(
    r"\b("
    r"what can you do|help|explain|how do you work|what is low stock|"
    r"what does low stock mean|what is available|what does available mean|"
    r"inventory status|statuses|status mean|examples?|"
    r"que peux[- ]tu faire|aide|explique|comment fonctionnes[- ]tu|"
    r"qu'est[- ]ce que le stock faible|que signifie le stock faible|"
    r"qu'est[- ]ce qui est disponible|que signifie disponible|"
    r"statut(?:s)? de l'inventaire|que signifie le statut|exemples?"
    r")\b",
    re.IGNORECASE,
)

_PROCEDURAL_RE = re.compile(
    r"\bhow (?:do|can|could|should) (?:i|we|you)\b|\bhow to\b|"
    r"\bcomment (?:puis[- ]je|peut[- ]on|faire|emprunter|demander|retourner)\b|"
    r"\bcomment .*\b(?:emprunter|demander|retourner|utiliser)\b",
    re.IGNORECASE,
)

_FOLLOW_UP_RE = re.compile(
    r"\b("
    r"only|those|ones|them|that|these|available|borrowed|dell|hp|apple|"
    r"lenovo|maintenance|overdue|current|now|this month|which are|who has|"
    r"seulement|ceux|celles|ceux[- ]ci|celles[- ]ci|ce|cette|ces|"
    r"disponibles?|emprunte(?:s|e)?|dell|hp|apple|lenovo|maintenance|"
    r"retard(?:s)?|actuel(?:le)?s?|maintenant|ce mois[- ]ci|lesquels|"
    r"lesquelles|qui a"
    r")\b",
    re.IGNORECASE,
)


def classify_intent(message: str, has_history: bool = False) -> IntentResult:
    """Classify whether a message needs live SQL retrieval or general chat."""
    text = " ".join((message or "").strip().split())
    lowered = text.lower()

    if not text:
        return IntentResult(Intent.GENERAL_CHAT, 1.0, "empty message")

    has_data_action = bool(_DATA_ACTION_RE.search(lowered))
    is_existence = bool(_EXISTENCE_RE.search(lowered))
    is_general = bool(_GENERAL_RE.search(lowered))

    if is_existence:
        return IntentResult(Intent.INVENTORY_SQL, 0.95, "asks whether an inventory item exists")

    if is_general and not has_data_action:
        return IntentResult(Intent.GENERAL_CHAT, 0.92, "general assistant question")

    if _PROCEDURAL_RE.search(lowered) and not any(
        token in lowered
        for token in (
            "show", "list", "my", "current", "this month",
            "affiche", "afficher", "liste", "combien", "maintenant", "ce mois",
        )
    ):
        return IntentResult(Intent.GENERAL_CHAT, 0.85, "asks about a process/how-to, not live data")

    if is_general and not any(
        token in lowered
        for token in (
            "item", "user", "borrow", "how many", "show", "list", "which",
            "article", "utilisateur", "emprunt", "combien", "affiche", "liste", "quel",
        )
    ):
        return IntentResult(Intent.GENERAL_CHAT, 0.74, "general inventory concept")

    if has_data_action:
        return IntentResult(Intent.INVENTORY_SQL, 0.9, "asks for live inventory data")

    if has_history and _FOLLOW_UP_RE.search(lowered):
        return IntentResult(Intent.INVENTORY_SQL, 0.78, "follow-up to previous data question")

    return IntentResult(Intent.GENERAL_CHAT, 0.62, "no live data request detected")
