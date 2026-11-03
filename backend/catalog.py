WIDTH, HEIGHT = 28, 20
SHELVES = [{'id':f'R{i+1:02}', 'x':x, 'y':y, 'width':2, 'height':3, 'pickup':[x-1,y+1], 'zone': 'A' if y<8 else 'B'} for i,(x,y) in enumerate((x,y) for y in [4,10] for x in [5,10,15,20])]
DOCKS = [{'id':f'D{i+1}', 'position':[25,y]} for i,y in enumerate([4,9,14])]
CHARGERS = [{'id':f'C{i+1:02}','position':[2+2*i,17]} for i in range(10)]
SHELF_CELLS = frozenset((s['x']+dx,s['y']+dy) for s in SHELVES for dx in range(2) for dy in range(3))
POLICIES = [
    {'id':'fifo','name':'First in, first out','short':'FIFO','color':'#b59bf4','description':'Dispatch robots in ID order to the oldest released order. Predictable queue discipline.'},
    {'id':'nearest','name':'Nearest pickup','short':'Nearest','color':'#5dcdb4','description':'Each available robot takes the closest reachable pickup. Short initial travel, local decisions.'},
    {'id':'auction','name':'Fleet auction','short':'Auction','color':'#efa86c','description':'Assign the best fleet-wide robot/order bid using total route length, urgency, and completed workload.'},
]
SCENARIOS = [
    {'id':'standard','name':'Steady shift','tag':'BASELINE','description':'A full batch of orders, clear aisles, and charged robots.','battery':100,'wave':False,'closure':False},
    {'id':'peak','name':'Peak fulfillment','tag':'ORDER WAVES','description':'Orders arrive in waves every 25 ticks, with tighter deadlines.','battery':100,'wave':True,'closure':False},
    {'id':'blocked','name':'Aisle disruption','tag':'DYNAMIC ROUTING','description':'Maintenance closes part of aisle 12 from tick 45 to 110. Robots replan around it.','battery':100,'wave':False,'closure':True},
    {'id':'low_battery','name':'Charging pressure','tag':'ENERGY TEST','description':'Some robots begin with depleted batteries and must recharge before accepting work.','battery':24,'wave':False,'closure':False},
]
COLORS = ['#63d4b2','#ad9bef','#eeaa72','#70b9ed','#e68bab','#d8d779','#82c8cb','#c6a07c','#a5d28a','#b29cc8']
def layout():
    return {'width':WIDTH,'height':HEIGHT,'shelves':SHELVES,'docks':DOCKS,'chargers':CHARGERS,'blocked_cells':[list(c) for c in sorted(SHELF_CELLS)]}
