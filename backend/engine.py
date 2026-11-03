"""Deterministic fleet simulation with discrete, simultaneous, collision-checked moves.

Grid units, ticks and battery percentages are educational model parameters.
No learned policy, LLM call, external service, or real robot hardware is involved.
"""
from collections import deque
from functools import lru_cache
from random import Random
from .catalog import WIDTH,HEIGHT,SHELVES,SHELF_CELLS,DOCKS,CHARGERS,COLORS,SCENARIOS

def neighbors(cell):
    x,y=cell
    return [(nx,ny) for nx,ny in [(x+1,y),(x,y-1),(x-1,y),(x,y+1)] if 1<=nx<WIDTH-1 and 1<=ny<HEIGHT-1]

@lru_cache(maxsize=30000)
def pathfind(start,goal,blocked):
    if start==goal:return (start,)
    if goal in blocked:return ()
    queue=deque([start]);parents={start:None}
    while queue:
        current=queue.popleft()
        for cell in neighbors(current):
            if cell in blocked or cell in parents:continue
            parents[cell]=current
            if cell==goal:
                path=[cell]
                while parents[path[-1]] is not None:path.append(parents[path[-1]])
                return tuple(reversed(path))
            queue.append(cell)
    return ()

def resolve_moves(positions,proposals,priority):
    """Resolve vertex conflicts, head-on swaps and chains blocked by stationary robots.

    Following into a vacated cell is permitted; continuous interpolation preserves
    spacing. A head-on two-robot swap is never permitted. Longer rotations are safe.
    """
    owner={cell:i for i,cell in positions.items()};rank={i:n for n,i in enumerate(priority)}
    moves=dict(proposals)
    claims={}
    for i,target in moves.items():claims.setdefault(target,[]).append(i)
    for target,ids in claims.items():
        if len(ids)>1:
            stationary=next((i for i in ids if positions[i]==target),None)
            winner=stationary if stationary is not None else min(ids,key=lambda i:rank[i])
            for i in ids:
                if i!=winner:moves[i]=positions[i]
    for i,target in list(moves.items()):
        other=owner.get(target)
        if other is not None and other!=i and moves[other]==positions[i]:
            moves[i]=positions[i];moves[other]=positions[other]
    changed=True
    while changed:
        changed=False
        for i,target in list(moves.items()):
            other=owner.get(target)
            if target!=positions[i] and other is not None and moves[other]==positions[other]:
                moves[i]=positions[i];changed=True
    return moves

def generate_orders(config):
    rng=Random(config.seed)
    scenario=next(s for s in SCENARIOS if s['id']==config.scenario)
    orders=[]
    for i in range(config.order_count):
        rack=rng.choice(SHELVES);dock=rng.choice(DOCKS)
        release=(i//8)*25 if scenario['wave'] else 0
        priority=rng.choice([1,1,2,3])
        orders.append({'id':f'ORD-{i+1:03}','sku':f'SKU-{101+SHELVES.index(rack)*7}','rack_id':rack['id'],'pickup':rack['pickup'][:],'dock_id':dock['id'],'dock':dock['position'][:],'priority':priority,'release':release,'due':release+(85 if scenario['wave'] else 115)+rng.randrange(45),'status':'queued' if release==0 else 'scheduled','robot_id':None,'assigned_at':None,'completed_at':None})
    return orders

def simulate(config):
    scenario=next(s for s in SCENARIOS if s['id']==config.scenario)
    orders=generate_orders(config)
    robots=[]
    for i in range(config.fleet_size):
        home=tuple(CHARGERS[i]['position'])
        initial=(18+(i%3)*7 if i%2==0 else 65) if scenario['id']=='low_battery' else 100
        robots.append({'id':f'AMR-{i+1:02}','color':COLORS[i],'position':home,'home':home,'battery':float(initial),'status':'idle','order_id':None,'target':home,'carrying':False,'timer':0,'distance':0,'completed':0,'wait':0,'working_ticks':0,'charge_sessions':0,'path':[],'route_plan':[], 'plan_goal':None, 'recent':[], 'reason':'Ready for dispatch.'})
    frames=[];events=[];visits=[[0]*WIDTH for _ in range(HEIGHT)]
    conflicts=0;charge_ticks=0;completion_times=[];on_time=0
    lookup={o['id']:o for o in orders}
    def event(t,kind,message,robot=None,order=None):
        events.append({'tick':t,'kind':kind,'message':message,'robot_id':robot,'order_id':order})
    def path(start,goal,blocked):return pathfind(tuple(start),tuple(goal),frozenset(blocked))
    def distance(a,b,blocked):
        p=path(a,b,blocked);return len(p)-1 if p else 10000
    def required(robot,order,blocked):
        cells=distance(robot['position'],order['pickup'],blocked)+distance(order['pickup'],order['dock'],blocked)+distance(order['dock'],robot['home'],blocked)
        return max(26,cells*.4+12)
    def snapshot(t,blocks):
        states=[]
        for r in robots:
            states.append({k:([*v] if k in ('position','home','target') else v) for k,v in r.items() if k not in ('timer','route_plan','plan_goal','recent')})
        frames.append({'tick':t,'robots':states,'order_statuses':{o['id']:o['status'] for o in orders},'blocked_cells':[list(c) for c in sorted(blocks)],'completed':sum(o['status']=='completed' for o in orders),'queued':sum(o['status']=='queued' for o in orders),'active':sum(o['status'] in ('assigned','picked') for o in orders),'distance':sum(r['distance'] for r in robots)})
    snapshot(0,set())
    finished=0
    for tick in range(1,config.max_ticks+1):
        occupied={r['position'] for r in robots}
        # A closure only becomes active on unoccupied cells; no robot is crushed.
        closure={(12,y) for y in range(3,11) if (12,y) not in occupied} if scenario['closure'] and 45<=tick<110 else set()
        blocked=SHELF_CELLS|closure
        if scenario['closure'] and tick==45:event(tick,'aisle_closed','Maintenance closes aisle 12; occupied cells are deferred until vacated.')
        if scenario['closure'] and tick==110:event(tick,'aisle_open','Maintenance complete. Aisle 12 reopened.')
        for o in orders:
            if o['status']=='scheduled' and o['release']<=tick:
                o['status']='queued';event(tick,'order_released',f"{o['id']} released to the queue.",order=o['id'])
        # Complete service tasks before allocating the next movement step.
        service_ids=set()
        for r in robots:
            if r['status']=='charging':
                service_ids.add(r['id']);r['battery']=min(100,r['battery']+3.5);charge_ticks+=1
                if r['battery']>=90:r['status']='idle';r['reason']='Charge threshold reached; available for work.';event(tick,'charged',f"{r['id']} charged to {r['battery']:.0f}%.",r['id'])
            elif r['status'] in ('picking','dropping'):
                service_ids.add(r['id']);r['timer']-=1;r['working_ticks']+=1;r['battery']=max(0,r['battery']-.05)
                if r['timer']<=0:
                    o=lookup[r['order_id']]
                    if r['status']=='picking':
                        r['status']='to_dock';r['target']=tuple(o['dock']);r['carrying']=True;o['status']='picked';r['reason']=f"Collected {o['sku']}; heading to {o['dock_id']}.";event(tick,'picked',r['reason'],r['id'],o['id'])
                    else:
                        o['status']='completed';o['completed_at']=tick;r['completed']+=1;r['carrying']=False;r['order_id']=None;r['status']='idle';r['reason']=f"{o['id']} handed off at {o['dock_id']}.";completion_times.append(tick-o['release']);on_time+=tick<=o['due'];event(tick,'delivered',r['reason'],r['id'],o['id'])
        queued=[o for o in orders if o['status']=='queued']
        idle=[r for r in robots if r['status'] in ('idle','returning') and r['id'] not in service_ids]
        # Low-charge robots return to their own dedicated charger, avoiding pad contention.
        eligible=[]
        for r in idle:
            minimum=min((required(r,o,blocked) for o in queued),default=26)
            if r['battery']<minimum:
                r['status']='to_charge';r['target']=r['home'];r['reason']='Battery reserve insufficient for a complete pick, delivery, and charger return.'
            else:eligible.append(r)
        def assign(r,o):
            r['order_id']=o['id'];r['target']=tuple(o['pickup']);r['status']='to_pick';r['reason']=f"{config.policy} dispatch: collect {o['id']} at {o['rack_id']}.";o.update(status='assigned',robot_id=r['id'],assigned_at=tick);event(tick,'assigned',r['reason'],r['id'],o['id'])
        if config.policy=='auction':
            while eligible and queued:
                bids=[]
                for r in eligible:
                    for o in queued:
                        if r['battery']<required(r,o,blocked):continue
                        route=distance(r['position'],o['pickup'],blocked)+distance(o['pickup'],o['dock'],blocked)
                        score=route+max(0,tick+route+4-o['due'])*2-o['priority']*3+r['completed']*1.5
                        bids.append((score,r['id'],o['id'],r,o))
                if not bids:break
                *_,r,o=min(bids,key=lambda b:b[:3]);assign(r,o);eligible.remove(r);queued.remove(o)
        else:
            for r in eligible:
                candidates=[o for o in queued if r['battery']>=required(r,o,blocked)]
                if not candidates:continue
                if config.policy=='fifo':o=min(candidates,key=lambda o:(o['release'],o['id']))
                else:o=min(candidates,key=lambda o:(distance(r['position'],o['pickup'],blocked),o['id']))
                assign(r,o);queued.remove(o)
        for r in robots:
            if r['status']=='idle' and r['position']!=r['home']:
                r['status']='returning';r['target']=r['home'];r['reason']='Returning to staging to keep delivery docks clear.'
        positions={r['id']:r['position'] for r in robots};proposals=dict(positions)
        for r in robots:
            if r['id'] in service_ids:continue
            if r['status'] not in ('to_pick','to_dock','to_charge','returning'):continue
            if r['battery']<=0:
                r['status']='stranded';r['reason']='Battery exhausted; run will report unfinished work.';event(tick,'stranded',r['reason'],r['id']);continue
            goal=r['target']
            avoid={pos for rid,pos in positions.items() if rid!=r['id'] and pos!=goal}
            planned=r['route_plan']
            if not planned or r['plan_goal']!=goal or planned[0]!=r['position'] or any(c in blocked for c in planned):
                planned=path(r['position'],goal,blocked)
            if r['wait']>=2:
                detour=path(r['position'],goal,blocked|avoid)
                if detour:planned=detour
            recent=r['recent']
            if recent.count(r['position'])>=3 and len(set(recent))>1:
                # Escape repeated movement cycles by excluding recently traversed
                # cells while building a stable detour, not by moving randomly.
                history=set(recent)-{r['position'],goal}
                detour=path(r['position'],goal,blocked|avoid|history)
                if detour:planned=detour
            r['route_plan']=planned;r['plan_goal']=goal
            r['path']=[list(c) for c in planned[:12]]
            if len(planned)>1:proposals[r['id']]=planned[1]
        order=sorted(robots,key=lambda r:(-r['wait'],(int(r['id'][-2:])+tick)%config.fleet_size))
        moves=resolve_moves(positions,proposals,[r['id'] for r in order])
        for r in robots:
            rid=r['id'];old=r['position'];new=moves[rid]
            if new!=old:
                r['position']=new
                if len(r['route_plan'])>1 and r['route_plan'][1]==new:r['route_plan']=r['route_plan'][1:]
                r['distance']+=1;r['battery']=max(0,r['battery']-.4);r['wait']=0;r['working_ticks']+=int(r['order_id'] is not None);visits[new[1]][new[0]]+=1
            elif proposals[rid]!=old:
                conflicts+=1;r['wait']+=1;r['battery']=max(0,r['battery']-.015)
                if r['wait']==5:event(tick,'traffic_wait',f"{rid} yields; shared cells and head-on swaps are reserved safely.",rid)
            elif r['status']!='charging':r['battery']=max(0,r['battery']-.008)
            if r['id'] in service_ids:continue
            if r['position']==r['target']:
                if r['status']=='to_pick':r['status']='picking';r['timer']=2;r['reason']='At rack access cell; picking takes two ticks.'
                elif r['status']=='to_dock':r['status']='dropping';r['timer']=2;r['reason']='At shipping dock; handoff takes two ticks.'
                elif r['status']=='to_charge':r['status']='charging';r['charge_sessions']+=1;r['reason']='Charging on dedicated pad.';event(tick,'charging',f'{rid} begins charging.',rid)
                elif r['status']=='returning':r['status']='idle';r['reason']='At staging; ready for the next order.'
            r['recent']=(r['recent']+[r['position']])[-10:]
            r['battery']=round(r['battery'],5)
        # These invariants are enforced in production as well as tested.
        assert len(set(r['position'] for r in robots))==len(robots),'Robot cell collision'
        assert all(r['position'] not in blocked for r in robots),'Robot entered an obstacle'
        snapshot(tick,closure);finished=tick
        if all(o['status']=='completed' for o in orders):break
    delivered=[o for o in orders if o['status']=='completed']
    metrics={'completed':len(delivered),'total_orders':len(orders),'completion_rate':round(len(delivered)/len(orders)*100,1),'makespan':finished,'average_cycle':round(sum(completion_times)/len(completion_times),2) if completion_times else None,'on_time_rate':round(on_time/len(delivered)*100,1) if delivered else 0,'distance':sum(r['distance'] for r in robots),'wait_events':conflicts,'charge_sessions':sum(r['charge_sessions'] for r in robots),'charge_ticks':charge_ticks,'utilization':round(sum(r['working_ticks'] for r in robots)/(finished*len(robots))*100,1),'throughput':round(len(delivered)/finished*100,2),'status':'completed' if len(delivered)==len(orders) else 'tick_limit','collision_count':0}
    event(finished,'run_finished',f"{len(delivered)}/{len(orders)} orders completed in {finished} ticks.")
    return {'config':config.model_dump(),'metrics':metrics,'orders':orders,'frames':frames,'events':events,'heatmap':visits}
