from __future__ import annotations

import os
import sqlite3
from pathlib import Path

url = os.getenv("DATABASE_URL", "sqlite:///resume_analyzer.db")
db_path = Path(url.removeprefix("sqlite:///"))
if not db_path.is_absolute():
    db_path = Path.cwd() / db_path
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")
for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(f"TABLE {name}")
    for row in conn.execute(f"PRAGMA table_info([{name}])"):
        print("  COLUMN", row[1], "type=" + str(row[2]), "notnull=" + str(row[3]), "pk=" + str(row[5]))
    for row in conn.execute(f"PRAGMA foreign_key_list([{name}])"):
        print("  FK", row[3], "->", row[2] + "." + row[4], "on_delete=" + str(row[6]))
    for row in conn.execute(f"PRAGMA index_list([{name}])"):
        print("  INDEX", row[1], "unique=" + str(row[2]))
    count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print("  ROWS", count)
conn.close()
