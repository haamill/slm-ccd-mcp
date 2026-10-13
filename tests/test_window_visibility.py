from lab_mcp.devices.windows import visibility_from_records


def test_occluded_and_minimized_are_not_unobscured():
    selected={'hwnd':1,'rect':(0,0,4,2),'alive':True,'visible':True,'minimized':False,'hung':False}
    assert visibility_from_records(selected,[])['unobscured']
    blocker={'rect':(1,0,1,1),'visible':True,'minimized':False}
    assert not visibility_from_records(selected,[blocker])['unobscured']
    selected['minimized']=True
    assert not visibility_from_records(selected,[])['unobscured']
