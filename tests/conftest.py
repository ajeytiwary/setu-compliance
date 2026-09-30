"""Test isolation: every test runs against a throwaway SQLite DB.

Without this file, tests that call ``init_db()`` and write shipments /
suppliers / evidence directly (``test_pilot_dashboard.py``,
``test_risk_drilldown.py``, ``test_supplier_remediation.py``) pollute the
shared demo database at ``data/eurosetu.db``. That pollution inflated the
demo KPIs (book value, revenue-at-risk, drilldown rows) and broke the
client walkthrough.

The autouse fixture below monkeypatches ``app.db.DB_PATH`` to a per-test
temp file. ``connect()`` resolves ``DB_PATH`` at call time (it is not
imported anywhere else), so every module that goes through
``app.db.connect()`` — including the FastAPI routes and the pilot /
risk-drilldown / evidence-network helpers — is automatically isolated.
"""
import pytest

from app import db


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Point the app at a fresh temp DB for the duration of one test."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield