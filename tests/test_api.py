import csv,io
from fastapi.testclient import TestClient
from backend.api import app

def test_api_persists_run_export_and_history():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['app']=='warehouse-robot-fleet'
        catalog=client.get('/api/catalog').json()
        assert len(catalog['policies'])==3 and len(catalog['layout']['shelves'])==8
        r=client.post('/api/runs',json={'order_count':8,'fleet_size':3}).json()
        assert client.get('/api/runs/'+r['id']).json()==r
        assert len(client.get('/api/runs').json())==1
        exported=client.get('/api/runs/'+r['id']+'/export?format=csv')
        assert len(list(csv.DictReader(io.StringIO(exported.text))))==8
        assert client.get('/api/overview').json()['orders_completed']==r['metrics']['completed']

def test_api_validation_and_not_found():
    with TestClient(app) as client:
        for body in [{'policy':'wrong'},{'fleet_size':11},{'max_ticks':999999},{'seed':-1},{'order_count':0},{'command':'shell'}]:
            assert client.post('/api/runs',json=body).status_code==422
        assert client.get('/api/runs/missing').status_code==404
        assert client.get('/api/runs?limit=10000').status_code==422

def test_policy_comparison_and_mismatched_conditions():
    with TestClient(app) as client:
        result=client.post('/api/comparisons',json={'order_count':8}).json()
        assert result['fair_conditions'] and len(result['runs'])==3
        assert client.get('/api/overview').json()['runs']==3
        saved=client.post('/api/compare',json={'run_ids':[r['id'] for r in result['runs']]}).json()
        assert saved['fair_conditions']
        different=client.post('/api/runs',json={'order_count':8,'seed':99}).json()
        assert not client.post('/api/compare',json={'run_ids':[different['id'],result['runs'][0]['id']]}).json()['fair_conditions']
        assert len(client.get('/api/mcp').json()['tools'])==9
