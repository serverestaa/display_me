# tools/reset_db.py
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "test.db"

if DB_PATH.exists():
    DB_PATH.unlink()
    print("test.db removed ✅")
else:
    print("test.db not found (already gone)")

from database import engine, Base
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Database schema refreshed")
