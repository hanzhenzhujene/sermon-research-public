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


BASELINE_HASHES = {'church_ids': '895a088e8a7568f514ba093ed3396f772e20393af78d3c6bd54883350c9df9b7', 'people': 'f7357e0f4a8fca46e3ea3d9079907d0b82974fd9094bc42434a553bebaa1e757', 'items': 'f4c7674d2dfe1188a947b4614d9adfcfe184a673b27524c49251b8bb675d8271', 'sources': '5b6f42217015bd96c8576cb1776bee785e7b760fbddb9b2569b41369051903bc'}
def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert fingerprint(sorted(r['id'] for r in data['churches']))==BASELINE_HASHES['church_ids']
assert fingerprint(sorted([(r['id'],r['people']) for r in data['churches']]))==BASELINE_HASHES['people']
assert fingerprint(data['items'])==BASELINE_HASHES['items']
assert fingerprint(data['sources'])==BASELINE_HASHES['sources']
assert sum(r['affiliation']!='Not established' for r in data['churches'])==43
expected_affiliations={
 'overture:572ac890-84a4-4e0b-85a7-7e107a5ed598':'Catholic Church',
 'overture:27992171-cb68-4126-805c-a9704e5abf81':'Catholic Church',
 'overture:36853d24-8092-47ee-9215-787b4037b34e':'Catholic Church',
 'overture:ec2df8ef-2e53-41bd-9416-f8b567ee28d5':'Anglican Church in North America (ACNA)',
 'overture:3a3976a6-d823-478b-9f5b-dee8f2cbf92b':'United Methodist Church'}
for id,body in expected_affiliations.items():
    r=next(r for r in data['churches'] if r['id']==id)
    assert r['affiliation']==body and r['affiliation_checked_on']=='2026-11-06'
    assert r['checked_on']=='2026-11-05' and r['affiliation_note'] and r['affiliation_organization']
for id in ['overture:12969480-3ceb-4438-aa40-af0e52e1dd5a','overture:07110af6-945e-4898-b24b-97b47cc0fb97','overture:720fd86d-ad7b-40b9-b999-f6ea639f3ae2','overture:921cf7f7-ec6b-4d5e-b0c0-8f0bfd8fe7e1']:
    r=next(r for r in data['churches'] if r['id']==id)
    assert r['affiliation']=='Not established' and r['affiliation_note']
f=json.loads((ROOT/'data/feasibility.json').read_text())
fembedded=json.loads(re.search(r'<script id="feasibility-data" type="application/json">(.*?)</script>',html.decode(),re.S)[1])
assert fembedded==f and f['counts']==snapshot['feasibility_counts']
inspect(f)
from project_feasibility import inspect_public
inspect_public(f)
from collections import Counter
assert len(f['screens'])==12 and len(f['supplemental'])==3
assert len({r['id'] for r in f['screens']+f['supplemental']})==15
assert Counter(r['category'] for r in f['screens'])=={'priority_text':2,'supplemental_text':1,'platform_export':3,'recording_candidate':1,'deferred_panel':5}
ids={r['id'] for r in data['churches']}
assert sum(r['directory_id'] in ids for r in f['screens'])==1
for filename,n in [('collection-feasibility.csv',12),('supplemental-leads.csv',3)]:
    with (ROOT/'data'/filename).open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.reader(stream))
    assert len(rows)==n+1 and all(len(r)==len(rows[0]) for r in rows)
    assert all(not re.match(r'^\s*[=+@-]',cell) for row in rows for cell in row)
a,t=f['fourth']['annual_records'],f['fourth']['target_checks']
assert len(a)==107 and len(t)==33 and sum(r['body_visible'] is True for r in t)==32
assert Counter(r['status'] for r in t)=={'no_conflict':28,'discrepancy':4,'unavailable':1}
assert all(r['confirmed_service_time'] is None for r in t if r['year']==2025 or r['status']!='no_conflict')
assert len([r for r in a if r.get('check_id')])==33
assert {r['check_id'] for r in a if r.get('check_id')}=={r['id'] for r in t}
a,t=f['thomas']['annual_records'],f['thomas']['october_observations']
assert len(a)==88 and len(t)==9 and Counter(r['status'] for r in t)=={'readable':8,'unavailable':1}
assert len([r for r in a if r.get('check_id')])==9
assert {r['check_id'] for r in a if r.get('check_id')}=={r['id'] for r in t}
for r in t:
    matches=[x for x in a if x['date']==r['date'] and x['title']==r['title']]
    assert len(matches)==1 and matches[0]['check_id']==r['id']
unknown=next(r for r in t if r['status']=='unavailable')
assert unknown['earlier_observation'] and unknown['passages'] is None and unknown['liturgical_label'] is None
conflict=next(r for r in a if r['title']=='Listen to My Voice')
assert conflict['index_date']=='May 9, 2022' and conflict['date']=='2022-05-08'
pairs=f['thomas']['passage_pairs'];assert len(pairs)==3 and sum(r['same_passage'] for r in pairs)==1
assert all(r['same_passage']==(r['pre_passages']==r['post_passages']) for r in pairs)
assert all(r['source_links'] and r['next_action'] for r in f['screens']+f['supplemental'])
assert not re.search(r'[\u3400-\u9fff]',json.dumps(f,ensure_ascii=False))
for fixture in [{'body':'restricted'}, {'address':'private'}, {'note':'/Users/private/file'}, {'note':'person@example.com'}]:
    try:inspect_public(fixture)
    except AssertionError:pass
    else:raise AssertionError('Privacy rejection fixture was accepted')
print('PASS: baseline IDs, 86 churches, 41 clergy roles, 47 items and 83 sources preserved; 5 affiliation changes; 12 screens + 3 leads; nested 107/33 and 88/9 checks, exceptions, rights, CSVs, notices and public-data boundaries agree.')
extensions=json.loads((ROOT/'data/extensions.json').read_text())
extensions_embedded=json.loads(re.search(r'<script id="extensions-data" type="application/json">(.*?)</script>',html.decode(),re.S)[1])
assert extensions_embedded==extensions, 'Extension JSON differs from website'
assert snapshot['extension_counts']==extensions['counts'], 'Extension snapshot counts differ'
inspect(extensions)
print('PASS: extension data, embedded website data and snapshot counters agree.')
