from backend import service,storage
from backend.models import ComparisonRequest
if __name__=='__main__':
    if storage.overview()['runs']:print('Existing experiments found; no demo data added.')
    else:
        result=service.run_comparison(ComparisonRequest())
        print('Saved three measured baseline shifts: FIFO, nearest pickup and fleet auction.')
