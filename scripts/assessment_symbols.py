"""Source checkbox alphabet shared by item parsing and evidence indexing."""

import re

SELECTED_BOXES = frozenset("■☑✅✓✔þ▣☒●√")
UNSELECTED_BOXES = frozenset("□☐○")
SELECTED_MARKER = r"(?:gfedcb|[" + "".join(sorted(SELECTED_BOXES)) + r"])"
BOX_CHARACTERS = "".join(sorted(SELECTED_BOXES | UNSELECTED_BOXES))
BOX_RE = re.compile(r"gfedcb|gfedc|[" + BOX_CHARACTERS + r"]", re.I)
