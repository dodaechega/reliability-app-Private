# 실행 중에도 일관된 SQLite 백업을 생성한다.
import os
import sqlite3
from datetime import datetime
from pathlib import Path

root = Path(os.environ['LOCALAPPDATA']) / 'ReliabilityApp'
source = root / 'data' / 'reliability.db'
if not source.exists():
    raise SystemExit('앱을 먼저 실행해 주세요.')
backup_dir = root / 'backups'
backup_dir.mkdir(exist_ok=True)
target = backup_dir / f'reliability-{datetime.now():%Y%m%d-%H%M%S-%f}.db'
with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
    with sqlite3.connect(target) as dest:
        src.backup(dest)
print(target)
os.startfile(backup_dir)
