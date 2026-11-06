#!/usr/bin/env python3
"""Validate the public snapshot offline; this script never fetches source pages."""
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_bytes()
snapshot=json.loads((ROOT/'snapshot.json').read_text())
data=json.loads((ROOT/'data/catalogue.json').read_text())
embedded=json.loads(re.search(r'<script id="public-data" type="application/json">(.*?)</script>',html.decode(),re.S)[1])
assert embedded==data, 'JSON differs from the website'
assert hashlib.sha256(html).hexdigest()==snapshot['index_sha256'], 'HTML checksum differs'
assert data['counts']==snapshot['counts'], 'Snapshot counts differ'
for key,n in [('churches',86),('items',47),('sources',83)]:
    assert len(data[key])==n
    assert len({r['id'] for r in data[key]})==n
    with (ROOT/'data'/f'{key}.csv').open(newline='',encoding='utf8') as f:
        rows=list(csv.reader(f))
    assert len(rows)==n+1
    assert all(len(r)==len(rows[0]) for r in rows)
    assert all(not cell.startswith(('=','+','@')) for row in rows for cell in row), 'Unsafe spreadsheet value'
assert sum(bool(c['people']) for c in data['churches'])==28
assert sum(len(c['people']) for c in data['churches'])==41
assert sum(c['eligible_sermons'] for c in data['churches'])==0
assert len({c['state'] for c in data['churches']})==44
assert data['counts']['full_texts_hosted']==0 and snapshot['full_texts_included'] is False

forbidden={'body','full_text','transcript','segments','email','phone','address','response_snapshot','response_sha256','source_sha256','journal','search'}
def inspect(value):
    if isinstance(value,dict):
        assert not forbidden.intersection(value), 'Private/corpus field in public data'
        for k,v in value.items():
            if k!='licenses':inspect(v)
    elif isinstance(value,list):
        for x in value:inspect(x)
    elif isinstance(value,str):
        assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|/Users/|\.cache/|github\.com/hanzhenzhujene/ai-preaching-comparison',value)
        if value.startswith(('https://','http://')):
            p=urlsplit(value)
            assert not p.username and not p.password
            assert p.hostname not in ('localhost','127.0.0.1')
            assert not any(re.search(r'token|secret|password|view_only|auth|signature',k,re.I) for k in parse_qs(p.query))
inspect(data)
for entry,name in zip(data['licenses'],['CDLA-Permissive-2.0.txt','Apache-2.0.txt','Foursquare-NOTICE.txt','us-atlas-ISC.txt']):
    assert (ROOT/'notices'/name).read_text()==entry['text']
assert not re.search(r'<(?:script[^>]+src=|iframe|audio|video)',html.decode())
print('PASS: 86 churches, 41 clergy roles at 28 churches, 47 item records, 83 sources; no full texts. Public JSON, CSV files, HTML hash and notices agree.')
