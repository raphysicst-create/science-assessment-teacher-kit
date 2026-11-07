"""Source checkbox alphabet shared by item parsing and evidence indexing."""

import re

SELECTED_BOXES = frozenset("■☑✅✓✔þ▣☒●√")
UNSELECTED_BOXES = frozenset("□☐○")
BRACKET_SELECTED = r"\[\s*[VvⅤⅴ]\s*\]"
BRACKET_EMPTY = r"\[\s*\]"
SELECTED_MARKER = r"(?:" + BRACKET_SELECTED + r"|gfedcb|[" + "".join(sorted(SELECTED_BOXES)) + r"])"
BOX_CHARACTERS = "".join(sorted(SELECTED_BOXES | UNSELECTED_BOXES))
BOX_RE = re.compile(
    BRACKET_SELECTED + "|" + BRACKET_EMPTY + r"|gfedcb|gfedc|[" + BOX_CHARACTERS + r"]", re.I
)


def marker_state(marker: str) -> str:
    if (
        marker.lower() == "gfedcb"
        or marker in SELECTED_BOXES
        or re.fullmatch(BRACKET_SELECTED, marker)
    ):
        return "checked"
    if (
        marker.lower() == "gfedc"
        or marker in UNSELECTED_BOXES
        or re.fullmatch(BRACKET_EMPTY, marker)
    ):
        return "unchecked"
    return "unknown"
