import argparse
from mcp.server.fastmcp import FastMCP
from backend.catalog import layout,SCENARIOS,POLICIES
from backend.models import RunRequest,ComparisonRequest
from backend import service,storage

mcp=FastMCP('Warehouse Robot Fleet',host='127.0.0.1',port=8103)
@mcp.tool()
def get_warehouse()->dict:
    """Get the warehouse grid, shelf obstacles, rack pickup points, shipping docks, and charging pads."""
    return layout()
@mcp.tool()
def list_scenarios()->list[dict]:
    """List baseline, wave demand, temporary aisle closure, and low-battery scenarios."""
    return SCENARIOS
@mcp.tool()
def list_policies()->list[dict]:
    """Describe FIFO, nearest-pickup and fleet-auction dispatch policies."""
    return POLICIES
@mcp.tool()
def run_simulation(policy:str='auction',scenario:str='standard',fleet_size:int=6,order_count:int=24,max_ticks:int=500,seed:int=42)->dict:
    """Run a bounded fleet simulation and save its results. No real robot is controlled. Returns metrics and run ID; retrieve frames separately."""
    return storage.summary(service.run_simulation(RunRequest(policy=policy,scenario=scenario,fleet_size=fleet_size,order_count=order_count,max_ticks=max_ticks,seed=seed)))
@mcp.tool()
def run_comparison(scenario:str='standard',fleet_size:int=6,order_count:int=24,max_ticks:int=500,seed:int=42)->dict:
    """Run all three dispatch policies with identical initial conditions and persist the results."""
    return service.run_comparison(ComparisonRequest(scenario=scenario,fleet_size=fleet_size,order_count=order_count,max_ticks=max_ticks,seed=seed))
@mcp.tool()
def list_runs(limit:int=20,offset:int=0)->list[dict]:
    """List saved experiment summaries, newest first; limit 1–100."""
    if not 1<=limit<=100 or offset<0:raise ValueError('limit must be 1–100; offset must be nonnegative')
    return storage.list_runs(limit,offset)
@mcp.tool()
def get_run(run_id:str)->dict:
    """Retrieve configuration, metrics, all orders, event log and heatmap. Use get_frame for robot positions at a particular tick."""
    return {k:v for k,v in storage.get_run(run_id).items() if k!='frames'}
@mcp.tool()
def get_frame(run_id:str,tick:int=0)->dict:
    """Inspect exact saved robot states and order statuses at one tick; tick must be within this run."""
    result=storage.get_run(run_id)
    if not 0<=tick<len(result['frames']):raise ValueError(f"tick must be 0–{len(result['frames'])-1}")
    return result['frames'][tick]
@mcp.tool()
def compare_runs(run_ids:list[str])->dict:
    """Compare 2–30 saved experiments; flag differing seeds, fleets, demand, scenario or tick bounds."""
    if not 2<=len(run_ids)<=30:raise ValueError('Provide 2–30 IDs')
    return service.compare_saved([storage.get_run(i) for i in run_ids])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Local warehouse MCP tools')
    parser.add_argument('--http',action='store_true');parser.add_argument('--port',type=int,default=8103)
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Invalid port')
    mcp.settings.port=args.port;mcp.run(transport='streamable-http' if args.http else 'stdio')
