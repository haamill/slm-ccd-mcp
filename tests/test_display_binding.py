import pytest
from lab_mcp.models import SLMConfig
from lab_mcp.devices.hdslm import select_roles


def test_same_serial_rect_binding():
    cfg={'slm1':SLMConfig(serial='same',desktop_xy=(0,0),panel_wh=(4,2)),
         'slm2':SLMConfig(serial='same',desktop_xy=(4,0),panel_wh=(4,2))}
    displays=[{'index':1,'sn':'same','name':'HDSLM','x':0,'y':0,'width':4,'height':2},
              {'index':2,'sn':'same','name':'HDSLM','x':4,'y':0,'width':4,'height':2}]
    selected=select_roles(cfg,displays)
    assert selected['slm1']['index']==1 and selected['slm2']['index']==2
    with pytest.raises(Exception): select_roles(cfg,displays+[displays[0]])
    displays[0]['name']='Ordinary Desktop'
    assert select_roles(cfg,displays)['slm1'] is None
