import ctypes
from ctypes import wintypes
import os
import time


def visibility_from_records(selected,above):
    x,y,w,h=selected['rect']; blockers=[]
    for record in above:
        if not record.get('visible') or record.get('minimized'): continue
        bx,by,bw,bh=record['rect']
        if min(x+w,bx+bw)>max(x,bx) and min(y+h,by+bh)>max(y,by): blockers.append(record)
    return {**selected,'blockers':blockers,'unobscured':bool(selected.get('alive') and
        selected.get('visible') and not selected.get('minimized') and not selected.get('hung') and not blockers),
        'checked_monotonic_ns':time.monotonic_ns(),'physical_frame_readback':False}


def user32():
    library=ctypes.WinDLL('user32',use_last_error=True)
    for name in ('IsWindow','IsWindowVisible','IsIconic','IsHungAppWindow'):
        function=getattr(library,name); function.argtypes=[wintypes.HWND]; function.restype=wintypes.BOOL
    library.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    library.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    return library


def enable_owner_dpi():
    library=user32()
    library.SetThreadDpiAwarenessContext.argtypes=[ctypes.c_void_p]
    library.SetThreadDpiAwarenessContext.restype=ctypes.c_void_p
    library.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))


def window_records():
    library=user32(); records=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def callback(hwnd,unused):
        rect=wintypes.RECT(); pid=wintypes.DWORD()
        library.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if library.GetWindowRect(hwnd,ctypes.byref(rect)):
            records.append({'hwnd':int(hwnd),'pid':pid.value,'rect':(rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top),
                'alive':bool(library.IsWindow(hwnd)),'visible':bool(library.IsWindowVisible(hwnd)),
                'minimized':bool(library.IsIconic(hwnd)),'hung':bool(library.IsHungAppWindow(hwnd))})
        return True
    native_callback=callback_type(callback)
    library.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    if not library.EnumWindows(native_callback,0): raise OSError('Window enumeration failed')
    return records


def find_projection_window(expected_rect):
    matches=[r for r in window_records() if r['pid']==os.getpid() and r['rect']==tuple(expected_rect)]
    if len(matches)!=1: raise RuntimeError('Cannot uniquely identify projection window by PID and rectangle')
    return matches[0]['hwnd']


def inspect_projection_window(hwnd,expected_rect):
    above=[]
    for record in window_records():
        if record['hwnd']==hwnd:
            result=visibility_from_records(record,above)
            if record['rect']!=tuple(expected_rect): result['unobscured']=False; result['rect_mismatch']=True
            return result
        above.append(record)
    return {'alive':False,'hung':False,'unobscured':False,'checked_monotonic_ns':time.monotonic_ns()}


def monitor_topology():
    """Physical rectangles with Windows monitor interface identities, all active displays."""
    library=user32(); result=[]
    class MonitorInfo(ctypes.Structure):
        _fields_=[('cbSize',wintypes.DWORD),('rcMonitor',wintypes.RECT),('rcWork',wintypes.RECT),
            ('dwFlags',wintypes.DWORD),('szDevice',wintypes.WCHAR*32)]
    class DisplayDevice(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('DeviceName',wintypes.WCHAR*32),('DeviceString',wintypes.WCHAR*128),
            ('StateFlags',wintypes.DWORD),('DeviceID',wintypes.WCHAR*128),('DeviceKey',wintypes.WCHAR*128)]
    library.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(MonitorInfo)]
    library.EnumDisplayDevicesW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(DisplayDevice),wintypes.DWORD]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HANDLE,wintypes.HDC,ctypes.POINTER(wintypes.RECT),wintypes.LPARAM)
    errors=[]
    def callback(monitor,dc,rect,unused):
        info=MonitorInfo(); info.cbSize=ctypes.sizeof(info)
        device=DisplayDevice(); device.cb=ctypes.sizeof(device)
        if not library.GetMonitorInfoW(monitor,ctypes.byref(info)):
            errors.append('Cannot read monitor identity'); return False
        if not library.EnumDisplayDevicesW(info.szDevice,0,ctypes.byref(device),1):
            errors.append('Cannot read monitor interface'); return False
        r=rect.contents
        result.append((info.szDevice,device.DeviceID,device.DeviceKey,
            (r.left,r.top,r.right-r.left,r.bottom-r.top)))
        return True
    native_callback=callback_type(callback)
    library.EnumDisplayMonitors.argtypes=[wintypes.HDC,ctypes.c_void_p,callback_type,wintypes.LPARAM]
    if not library.EnumDisplayMonitors(None,None,native_callback,0) or errors: raise OSError('Monitor scan failed: '+str(errors))
    return sorted(result)


def monitor_rectangles(): return [record[-1] for record in monitor_topology()]
