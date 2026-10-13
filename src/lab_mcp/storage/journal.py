import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
from .common import checked_id


class OperationJournal:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, hash TEXT NOT NULL, status TEXT NOT NULL, stage TEXT, submitted INTEGER DEFAULT 0, result TEXT, updated REAL)')
            db.execute("UPDATE operations SET status='uncertain' WHERE status IN ('intent','running')")

    def _db(self):
        return sqlite3.connect(self.path,timeout=10)

    def begin(self,operation_id,params):
        checked_id(operation_id)
        encoded=json.dumps(params,sort_keys=True,separators=(',',':'),allow_nan=False)
        digest=hashlib.sha256(encoded.encode()).hexdigest()
        with self.lock,self._db() as db:
            row=db.execute('SELECT hash FROM operations WHERE id=?',(operation_id,)).fetchone()
            if row:
                if row[0]!=digest: raise ValueError('Operation ID reused with different parameters')
                return self.get(operation_id)
            db.execute('INSERT INTO operations (id,hash,status,stage,updated) VALUES (?,?,?,?,?)',
                (operation_id,digest,'intent','preflight',time.time()))
        return self.get(operation_id)

    def stage(self,operation_id,name,*,hardware_submitted):
        with self.lock,self._db() as db:
            db.execute("UPDATE operations SET status='running', stage=?, submitted=MAX(submitted,?), updated=? WHERE id=?",(name,int(hardware_submitted),time.time(),checked_id(operation_id)))

    def finish(self,operation_id,result):
        self._finish(operation_id,'succeeded',result)

    def fail(self,operation_id,error):
        self._finish(operation_id,'failed',error)

    def _finish(self,ident,status,result):
        with self.lock,self._db() as db:
            db.execute('UPDATE operations SET status=?, result=?, updated=? WHERE id=?',
                (status,json.dumps(result,allow_nan=False),time.time(),checked_id(ident)))

    def get(self,operation_id):
        with self.lock,self._db() as db:
            row=db.execute('SELECT status,stage,submitted,result,updated FROM operations WHERE id=?',(checked_id(operation_id),)).fetchone()
        if row is None: raise ValueError('Unknown operation ID')
        return {'operation_id':operation_id,'status':row[0],'stage':row[1],
            'hardware_submitted':bool(row[2]),'result':json.loads(row[3]) if row[3] else None,'updated':row[4]}
