import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
from contextlib import contextmanager, closing
from .common import checked_id


class OperationJournal:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, hash TEXT NOT NULL, status TEXT NOT NULL, stage TEXT, submitted INTEGER DEFAULT 0, result TEXT, updated REAL)')
            columns={row[1] for row in db.execute('PRAGMA table_info(operations)')}
            for name in ('params','steps'):
                if name not in columns: db.execute(f'ALTER TABLE operations ADD COLUMN {name} TEXT')
            db.execute("UPDATE operations SET status='uncertain' WHERE status IN ('intent','running')")

    @contextmanager
    def _db(self):
        with closing(sqlite3.connect(self.path,timeout=10)) as db:
            with db: yield db

    def begin(self,operation_id,params):
        checked_id(operation_id)
        encoded=json.dumps(params,sort_keys=True,separators=(',',':'),allow_nan=False)
        digest=hashlib.sha256(encoded.encode()).hexdigest()
        with self.lock,self._db() as db:
            row=db.execute('SELECT hash FROM operations WHERE id=?',(operation_id,)).fetchone()
            if row:
                if row[0]!=digest: raise ValueError('Operation ID reused with different parameters')
                return self.get(operation_id)
            db.execute('INSERT INTO operations (id,hash,status,stage,updated,params,steps) VALUES (?,?,?,?,?,?,?)',
                (operation_id,digest,'intent','preflight',time.time(),encoded,'[]'))
        return self.get(operation_id)

    def stage(self,operation_id,name,*,hardware_submitted):
        with self.lock,self._db() as db:
            ident=checked_id(operation_id)
            steps=json.loads(db.execute('SELECT steps FROM operations WHERE id=?',(ident,)).fetchone()[0] or '[]')
            steps.append({'name':name,'status':'started','hardware_submitted':bool(hardware_submitted),'started':time.time()})
            db.execute("UPDATE operations SET status='running', stage=?, submitted=MAX(submitted,?), updated=?, steps=? WHERE id=?",(name,int(hardware_submitted),time.time(),json.dumps(steps),ident))

    def complete_stage(self,operation_id,name):
        with self.lock,self._db() as db:
            ident=checked_id(operation_id)
            steps=json.loads(db.execute('SELECT steps FROM operations WHERE id=?',(ident,)).fetchone()[0] or '[]')
            if steps and steps[-1]['name']==name and steps[-1]['status']=='started':
                steps[-1].update(status='completed',completed=time.time())
            db.execute('UPDATE operations SET steps=?, updated=? WHERE id=?',(json.dumps(steps),time.time(),ident))

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
            row=db.execute('SELECT status,stage,submitted,result,updated,params,steps FROM operations WHERE id=?',(checked_id(operation_id),)).fetchone()
        if row is None: raise ValueError('Unknown operation ID')
        return {'operation_id':operation_id,'status':row[0],'stage':row[1],
            'hardware_submitted':bool(row[2]),'result':json.loads(row[3]) if row[3] else None,'updated':row[4],
            'params':json.loads(row[5]) if row[5] else None,'steps':json.loads(row[6] or '[]')}
