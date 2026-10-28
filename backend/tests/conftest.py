import os
import tempfile
from pathlib import Path

# Les écritures CRUD des tests vont dans un journal temporaire, jamais dans data/.
_journal = Path(tempfile.mkdtemp()) / "journal-crud.rq"
os.environ["ENERGYHOME_JOURNAL"] = str(_journal)
