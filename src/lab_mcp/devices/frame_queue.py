from collections import deque
import threading
import time
from ..errors import LabError


class FreshFrameQueue:
    def __init__(self,max_pending=3):
        self.condition=threading.Condition(); self.pending=deque(maxlen=max_pending)
        self.error=None; self.active=False; self.dropped=0

    def publish(self,frame):
        with self.condition:
            if not self.active: return
            if len(self.pending)==self.pending.maxlen: self.dropped+=1
            self.pending.append(frame); self.condition.notify_all()

    def publish_error(self,error):
        with self.condition:
            self.error=error; self.condition.notify_all()

    def check_ready(self):
        with self.condition:
            if self.error: raise LabError('unavailable',f'CCD stream error: {self.error}')

    def collect(self,request,boundary_ns,exposure_us,on_frame):
        threshold=int(boundary_ns+(request.settle_s+exposure_us/1e6)*1e9)
        deadline=time.monotonic()+request.timeout_s
        discarded=[]; saved=[]; last_counter=-1
        with self.condition:
            self.pending.clear(); self.dropped=0; self.active=True
        try:
            while len(saved)<request.frames:
                with self.condition:
                    if self.error: raise self.error
                    remaining=deadline-time.monotonic()
                    if remaining<=0: raise TimeoutError('Timed out waiting for fresh RAW frames')
                    if not self.pending:
                        self.condition.wait(min(remaining,.25)); continue
                    frame=self.pending.popleft()
                meta=frame.metadata
                if meta['host_monotonic_ns']<threshold or meta['host_frame_counter']<=last_counter: continue
                last_counter=meta['host_frame_counter']
                if len(discarded)<request.discard_frames:
                    discarded.append(meta); continue
                on_frame(frame); saved.append(meta)
        except Exception as exc:
            raise LabError('capture_failed',str(exc),stage='capture',details={
                'saved_frames':len(saved),'frames':saved,'discarded':discarded,
                'freshness_threshold_ns':threshold,'dropped_queue_frames':self.dropped}) from exc
        finally:
            with self.condition: self.active=False; self.pending.clear()
        return {'frames':saved,'discarded':discarded,'freshness_threshold_ns':threshold,
            'screen_done_monotonic_ns':boundary_ns,'dropped_queue_frames':self.dropped,
            'timing':'software conservative; no exact exposure-start synchronization'}
