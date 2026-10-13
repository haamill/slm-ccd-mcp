import threading
import time
import numpy as np
import pytest
from lab_mcp.models import FrameRecord, CaptureRequest
from lab_mcp.devices.frame_queue import FreshFrameQueue
from lab_mcp.errors import LabError
from test_camera_settings import make_adapter


def frame(counter,when):
    return FrameRecord(np.array([[counter]],dtype=np.uint16),
        {'host_frame_counter':counter,'host_monotonic_ns':when,'origin_xy':[0,0]})


def test_freshness_threshold_and_three_discards():
    queue=FreshFrameQueue(12); boundary=time.monotonic_ns(); saved=[]
    def producer():
        while not queue.active: time.sleep(.001)
        queue.publish(frame(1,boundary-1))
        for counter in range(2,7):
            time.sleep(.002); queue.publish(frame(counter,boundary+counter*1000000))
    thread=threading.Thread(target=producer); thread.start()
    result=queue.collect(CaptureRequest(settle_s=0.,timeout_s=1.),boundary,1,saved.append)
    thread.join()
    assert [f.metadata['host_frame_counter'] for f in saved]==[5]
    assert [f['host_frame_counter'] for f in result['discarded']]==[2,3,4]


def test_timeout_returns_partial_metadata():
    with pytest.raises(LabError) as error:
        FreshFrameQueue().collect(CaptureRequest(settle_s=0.,timeout_s=.01),time.monotonic_ns(),1,lambda _:None)
    assert error.value.details['saved_frames']==0


def test_disconnect_wakes_waiter():
    queue=FreshFrameQueue()
    def producer():
        while not queue.active: time.sleep(.001)
        queue.publish_error(RuntimeError('device disconnected'))
    thread=threading.Thread(target=producer); thread.start()
    with pytest.raises(LabError): queue.collect(CaptureRequest(timeout_s=1.),time.monotonic_ns(),1,lambda _:None)
    thread.join()


def test_capture_budget_prechecked():
    adapter,c=make_adapter()
    try:
        adapter.connect()
        with pytest.raises(ValueError): adapter.capture(CaptureRequest(timeout_s=.01),time.monotonic_ns(),lambda _:None)
    finally: adapter.disconnect()


def test_roi_preserves_sensor_coordinates():
    from lab_mcp.devices.toupcam import crop_raw
    raw=np.arange(8,dtype=np.uint16).reshape(2,4)
    clipped,origin=crop_raw(raw,(1,1,2,1))
    np.testing.assert_array_equal(clipped,[[5,6]])
    assert origin==[1,1]


def test_invalid_frame_shape_fails():
    from lab_mcp.devices.toupcam import crop_raw
    with pytest.raises(ValueError): crop_raw(np.zeros((2,4),dtype=np.uint16),(3,0,2,1))
