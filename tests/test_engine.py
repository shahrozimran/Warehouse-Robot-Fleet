import pytest
from backend.engine import simulate,resolve_moves,generate_orders
from backend.models import RunRequest
from backend.catalog import SHELF_CELLS

def safe_frames(run):
    previous=None
    for frame in run['frames']:
        positions={r['id']:tuple(r['position']) for r in frame['robots']}
        assert len(set(positions.values()))==len(positions)
        blocked=SHELF_CELLS|{tuple(c) for c in frame['blocked_cells']}
        assert all(c not in blocked for c in positions.values())
        for r in frame['robots']:
            assert 0<=r['battery']<=100
            if previous:
                before=previous[r['id']];after=positions[r['id']]
                assert abs(before[0]-after[0])+abs(before[1]-after[1])<=1
                for other in positions:
                    if other!=r['id']:assert not (after==previous[other] and positions[other]==before and after!=before)
        previous=positions

@pytest.mark.parametrize('scenario',['standard','peak','blocked','low_battery'])
@pytest.mark.parametrize('policy',['fifo','nearest','auction'])
def test_all_default_policies_and_scenarios_complete_without_collisions(policy,scenario):
    run=simulate(RunRequest(policy=policy,scenario=scenario))
    safe_frames(run)
    assert run['metrics']['completed']==24
    assert run['metrics']['status']=='completed'
    assert all(o['completed_at']>=o['assigned_at']>=o['release'] for o in run['orders'])
    for order in run['orders']:
        picked=next(e for e in run['events'] if e['kind']=='picked' and e['order_id']==order['id'])
        assert picked['tick']<order['completed_at']
    if scenario=='low_battery':assert run['metrics']['charge_sessions']>=3
    if scenario=='blocked':assert any(f['blocked_cells'] for f in run['frames'])

@pytest.mark.parametrize('seed',[7,99,101])
def test_dense_fleet_respects_collision_and_battery_invariants(seed):
    run=simulate(RunRequest(seed=seed,fleet_size=10,order_count=36,scenario='peak',max_ticks=600))
    safe_frames(run)
    assert run['metrics']['completed']>0
    assert run['metrics']['makespan']<=600

def test_resolver_handles_swaps_stationary_chains_and_duplicate_destinations():
    positions={'a':(1,1),'b':(2,1),'c':(3,1)}
    result=resolve_moves(positions,{'a':(2,1),'b':(1,1),'c':(2,1)},['a','b','c'])
    assert result==positions
    result=resolve_moves(positions,{'a':(2,1),'b':(3,1),'c':(4,1)},['a','b','c'])
    assert result=={'a':(2,1),'b':(3,1),'c':(4,1)}
    result=resolve_moves(positions,{'a':(1,2),'b':(1,2),'c':(3,1)},['b','a','c'])
    assert result['b']==(1,2) and result['a']==(1,1)

def test_repeatability_and_equal_exogenous_orders():
    a=RunRequest(seed=23,order_count=8,fleet_size=2)
    assert simulate(a)==simulate(a)
    assert generate_orders(a)==generate_orders(a.model_copy(update={'policy':'fifo'}))

def test_limits_are_truthful_and_waves_not_released_early():
    run=simulate(RunRequest(order_count=80,fleet_size=2,max_ticks=100,scenario='peak'))
    assert run['metrics']['status']=='tick_limit'
    assert run['metrics']['completed']<80
    for order in run['orders']:
        for frame in run['frames']:
            if frame['tick']<order['release']:assert frame['order_statuses'][order['id']]=='scheduled'
