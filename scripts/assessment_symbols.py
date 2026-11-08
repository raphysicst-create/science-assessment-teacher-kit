"""Source checkbox alphabet shared by item parsing and evidence indexing."""

import re

SELECTED_BOXES = frozenset("■☑✅✓✔þ▣☒●√")
UNSELECTED_BOXES = frozenset("□☐○▢")
# PDF/HWP Wingdings text substitutions. Longest token must match first.
FONT_MARKERS = {"gfedcb": "checked", "gfedc": "unchecked"}
BRACKET_SELECTED = r"\[\s*[VvⅤⅴ" + "".join(sorted(SELECTED_BOXES)) + r"]\s*\]"
BRACKET_EMPTY = r"\[\s*\]"
BRACKET_UNSELECTED = r"\[\s*[" + "".join(sorted(UNSELECTED_BOXES)) + r"]\s*\]"
SELECTED_MARKER = r"(?:" + BRACKET_SELECTED + r"|gfedcb|[" + "".join(sorted(SELECTED_BOXES)) + r"])"
BOX_CHARACTERS = "".join(sorted(SELECTED_BOXES | UNSELECTED_BOXES))
BOX_RE = re.compile(
    BRACKET_SELECTED + "|" + BRACKET_EMPTY + "|" + BRACKET_UNSELECTED
    + r"|gfedcb(?![a-z])|gfedc(?![a-z])|["
    + BOX_CHARACTERS + r"]", re.I
)


def marker_state(marker: str) -> str:
    if (
        FONT_MARKERS.get(marker.lower()) == "checked"
        or marker in SELECTED_BOXES
        or re.fullmatch(BRACKET_SELECTED, marker)
    ):
        return "checked"
    if (
        FONT_MARKERS.get(marker.lower()) == "unchecked"
        or marker in UNSELECTED_BOXES
        or re.fullmatch(BRACKET_EMPTY, marker)
        or re.fullmatch(BRACKET_UNSELECTED, marker)
    ):
        return "unchecked"
    return "unknown"
