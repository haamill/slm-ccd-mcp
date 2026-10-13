import uuid
import pytest
from lab_mcp.storage.journal import OperationJournal


def test_duplicate_operation_payload(tmp_path):
    journal=OperationJournal(tmp_path/'operations.sqlite')
    ident=str(uuid.uuid4()); params={'op':'show','gray':4}
    journal.begin(ident,params)
    journal.finish(ident,{'status':'succeeded','value':4})
    assert journal.begin(ident,params)['result']['value']==4
    with pytest.raises(ValueError): journal.begin(ident,{'op':'show','gray':5})


def test_restart_preserves_uncertain(tmp_path):
    path=tmp_path/'operations.sqlite'; ident=str(uuid.uuid4())
    OperationJournal(path).begin(ident,{'op':'show'})
    resumed=OperationJournal(path)
    assert resumed.get(ident)['status']=='uncertain'
