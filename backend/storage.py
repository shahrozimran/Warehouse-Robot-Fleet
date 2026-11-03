import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
@contextmanager
def connection():
    path=Path(os.environ.get('WAREHOUSE_DB',str(ROOT/'data'/'warehouse.sqlite3')))
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path,timeout=30) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, batch_id TEXT, payload TEXT NOT NULL, summary TEXT NOT NULL)')
        yield db
def summary(run):
    return {k:v for k,v in run.items() if k not in ('frames','events','heatmap','orders')}
def insert(db,run):
    db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run['id'],run['created_at'],run.get('batch_id'),json.dumps(run,separators=(',',':')),json.dumps(summary(run))))
def get_run(run_id):
    with connection() as db:row=db.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
    if not row:raise ValueError(f'Run {run_id} not found.')
    return json.loads(row['payload'])
def list_runs(limit=100,offset=0):
    with connection() as db:rows=db.execute('SELECT summary FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
    return [json.loads(r['summary']) for r in rows]
def overview():
    with connection() as db:
        total=db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
        orders=db.execute("SELECT COALESCE(SUM(json_extract(summary,'$.metrics.completed')),0) FROM runs").fetchone()[0]
        distance=db.execute("SELECT COALESCE(SUM(json_extract(summary,'$.metrics.distance')),0) FROM runs").fetchone()[0]
    return {'runs':total,'orders_completed':orders,'distance':distance}
