import csv
import io
import json
from fastapi import FastAPI,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from . import service,storage
from .catalog import layout,POLICIES,SCENARIOS
from .models import RunRequest,ComparisonRequest,SavedComparison

app=FastAPI(title='Warehouse Robot Fleet',version='1.0.0',description='Local multi-robot warehouse simulation, reproducible experiments, persistent runs and MCP tools.')
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5174','http://localhost:5174'],allow_methods=['GET','POST'],allow_headers=['Content-Type'])
@app.get('/api/health')
def health():
    with storage.connection() as db:db.execute('SELECT 1')
    return {'status':'ok','app':'warehouse-robot-fleet','database':'connected','llm_required':False}
@app.get('/api/catalog')
def catalog():return {'layout':layout(),'policies':POLICIES,'scenarios':SCENARIOS}
@app.get('/api/overview')
def overview():return storage.overview()
@app.get('/api/runs')
def runs(limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0)):return storage.list_runs(limit,offset)
def required(run_id):
    try:return storage.get_run(run_id)
    except ValueError as exc:raise HTTPException(404,str(exc)) from exc
@app.get('/api/runs/{run_id}')
def get_run(run_id:str):return required(run_id)
@app.post('/api/runs')
def create_run(request:RunRequest):return service.run_simulation(request)
@app.post('/api/comparisons')
def compare(request:ComparisonRequest):return service.run_comparison(request)
@app.post('/api/compare')
def compare_saved(request:SavedComparison):return service.compare_saved([required(i) for i in request.run_ids])
@app.get('/api/runs/{run_id}/export')
def export(run_id:str,format:str=Query('json',pattern='^(json|csv)$')):
    result=required(run_id)
    if format=='json':data,mime=json.dumps(result,indent=2),'application/json'
    else:
        output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=list(result['orders'][0]));writer.writeheader();writer.writerows(result['orders']);data,mime=output.getvalue(),'text/csv'
    return Response(data,media_type=mime,headers={'Content-Disposition':f'attachment; filename="warehouse-{run_id}.{format}"'})
@app.get('/api/mcp')
def mcp_info():
    return {'tools':['get_warehouse','list_scenarios','list_policies','run_simulation','run_comparison','list_runs','get_run','get_frame','compare_runs'],'config':{'mcpServers':{'warehouse-fleet':{'command':str(storage.ROOT/'.venv'/'Scripts'/'python.exe'),'args':[str(storage.ROOT/'mcp_server.py')]}}}}
dist=storage.ROOT/'frontend'/'dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
