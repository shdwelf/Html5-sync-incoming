import sys
from pathlib import Path

# Make `journal_pipeline` importable no matter where unittest is launched from.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
