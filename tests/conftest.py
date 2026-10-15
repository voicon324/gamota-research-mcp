from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import pytest


@pytest.fixture
def database(tmp_path):
    from gamota_research.db import Database

    db = Database(tmp_path / "research.sqlite3")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def repository(database):
    from gamota_research.repository import ResearchRepository

    return ResearchRepository(database)
