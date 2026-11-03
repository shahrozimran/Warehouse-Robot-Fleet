from datetime import datetime,timezone
from uuid import uuid4
from .models import RunRequest,ComparisonRequest
from .catalog import POLICIES
from .engine import simulate
from . import storage

def make_run(config,batch_id=None):
    result=simulate(config)
    result.update(id=str(uuid4()),created_at=datetime.now(timezone.utc).isoformat(),batch_id=batch_id)
    return result
def run_simulation(config:RunRequest):
    result=make_run(config)
    with storage.connection() as db:storage.insert(db,result)
    return result
def compare_saved(runs):
    conditions=[tuple(r['config'][k] for k in ('scenario','fleet_size','order_count','max_ticks','seed')) for r in runs]
    ranked=sorted(runs,key=lambda r:(-r['metrics']['completed'],r['metrics']['makespan'],r['metrics']['distance']))
    return {'runs':[storage.summary(r) for r in runs],'ranking':[r['id'] for r in ranked],'fair_conditions':len(set(conditions))==1,'ranking_rule':'Most completed orders, then shortest makespan, then least distance. Same seed generates the same initial orders.'}
def run_comparison(config:ComparisonRequest):
    batch=str(uuid4())
    runs=[make_run(RunRequest(policy=p['id'],**config.model_dump()),batch) for p in POLICIES]
    with storage.connection() as db:
        for run in runs:storage.insert(db,run)
    return {'batch_id':batch,**compare_saved(runs)}
