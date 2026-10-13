import hashlib
import json
import os
from pathlib import Path
import uuid


def checked_id(value):
    try:
        canonical=str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Invalid record ID') from None
    if canonical != value:
        raise ValueError('Record ID must be a canonical UUID')
    return canonical


def write_json(path, data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('w',encoding='utf-8') as stream:
            json.dump(data,stream,ensure_ascii=False,allow_nan=False,indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def file_hash(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            result.update(chunk)
    return result.hexdigest()
