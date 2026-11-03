import pytest
@pytest.fixture(autouse=True)
def isolated_db(tmp_path,monkeypatch):monkeypatch.setenv('WAREHOUSE_DB',str(tmp_path/'warehouse.sqlite3'))
