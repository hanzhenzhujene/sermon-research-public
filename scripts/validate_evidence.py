#!/usr/bin/env python3
"""Validate public evidence projection, typed counts, joins and export boundaries."""
from pathlib import Path
from collections import Counter
from datetime import date
import csv, hashlib, json, re, subprocess, sys
from project_evidence import project, csv_value
ROOT=Path(__file__).resolve().parents[1]
BASELINE={
'catalogue':'73c4e721c85560aa9dadf2c6d38002c8a686885dc14732f84f2e2609cd000dcc',
'feasibility':'9ed1bc0fc1c8b9fa57baeb93209bbf7311a591fd0f643f2c88cc56c312edf56c',
'extensions':'cec9cab1945ba4dcced84e40c58c8b1e14b86fe0998ddfc5d6ee53aa41968977',
'catholic':'ab0407aa59eb6aada318afc833cbe0c802f2d66ad769976f1a99960fff860e4f',
'comparison':'b969d399bc243775f7539f31c067a0a86b5bd9d149b52d9291d31c00513fb4b0'}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def safe(v):
 if isinstance(v,dict):
  for k,x in v.items():
   assert k not in {'email','phone','address','street_address','reader_id','raw_body','full_text','transcript_body','html_body','raw_snapshot','credentials','token'},k
   safe(x)
 elif isinstance(v,list):
  for x in v:safe(x)
 elif isinstance(v,str):
  assert not re.search('[\u4e00-\u9fff]',v),'Non-English prose'
  assert not re.search(r'(?i)<script|<iframe|javascript:|file://|/Users/|/workspace/|libfile_|file_000000|ghp_|github_pat_|BEGIN PRIVATE KEY|ai-preaching-comparison',v),v[:100]
  assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',v),v[:100]
  if v.startswith(('http:','https:')):assert v.startswith('https://') and '\n' not in v

def csv_parity(path,rows):
 with path.open(encoding='utf-8-sig',newline='') as f:found=list(csv.DictReader(f))
 fields=list(dict.fromkeys(k for r in rows for k in r));expected=[{k:csv_value(r.get(k)) for k in fields} for r in rows]
 assert found==expected,path

def main():
 for n,h in BASELINE.items():assert hashlib.sha256((ROOT/'data'/f'{n}.json').read_bytes()).hexdigest()==h,n
 y=read(ROOT/'data/evidence.json');safe(y)
 if len(sys.argv)>1:assert y==project(Path(sys.argv[1]).resolve()),'Projection differs from verified input transformation'
 ds=y['decisions'];assert len(ds['items'])==7
 assert Counter(r['priority'] for r in ds['items'])=={'primary_written_comparison':2,'priority_gap_resolution':2,'supplementary_written_source':3}
 assert len({r['id'] for r in ds['items']})==7
 assert ds['separate_recording_route']['id']=='holy_trinity_sf'
 t=y['thomas'];inv=t['inventory'];q=t['candidates'];pages=t['pages'];pairs=t['comparisons'];status=t['detail_status']
 assert len(inv)==88 and Counter(r['year'] for r in inv)=={2022:43,2025:45}
 assert sum(r['cutoff_status']=='eligible' for r in inv)==40
 for year,calendar,labeled in [(2022,40,41),(2025,42,42)]:
  rows=[r for r in inv if r['year']==year]
  assert len({r['index_date'] for r in rows if date.fromisoformat(r['index_date']).weekday()==6})==calendar
  assert sum(r['stated_weekday']=='Sunday' for r in rows)==labeled
 assert sum(r['url_path_date']!=r['index_date'] for r in inv)==86
 assert all(r['url_path_date_is_verified_publication_date'] is False for r in inv)
 assert len(q)==15 and sum(r['cutoff_eligible_2022'] for r in q)==14
 assert sum(r['complete_list_equality'] is True and r['cutoff_eligible_2022'] for r in q)==10
 assert len(pages)==20 and len({p['source_url'] for p in pages})==20 and len(pairs)==10
 assert {p['record_id'] for p in pages}=={x for r in status['pairs'] for x in r['record_ids']}
 assert {p['pair_id'] for p in pairs}=={r['pair_id'] for r in status['pairs']}
 assert Counter(p['raw_labels_identical'] for p in pairs)=={True:9,False:1}
 for r in q:
  ps=[p for p in pages if p['pair_id']==r['pair_id']]
  assert len(ps)==(2 if r['candidate_rank']<=10 else 0)
  for p in ps:
   assert p['source_url'] in [r['url_2022'],r['url_2025']]
   assert p['byline']=='Adam Thomas'
 rank5=[p for p in pages if p['candidate_rank']==5]
 assert {p['liturgical_label_exact'] for p in rank5}=={'Palm/Passion Sunday C','Palm/Passion C'}
 assert Counter(p['license_observation']['status'] for p in pages)=={'notice_observed_on_this_page':7,'unknown_in_this_observation':13}
 assert all(p['readable_prose']['opening_visible'] is True and p['readable_prose']['ending_visible'] is True for p in pages)
 assert '1935' not in json.dumps(t.get('all_pairs',[])) and 'pair_classifications' not in t
 full=read(ROOT/'data/evidence/thomas/pair-classifications.json')
 assert len(full)==1935 and sum(r['cutoff_eligible_2022'] for r in full)==1800
 assert sum(r['complete_list_equality'] is None for r in full)==43
 assert sum(r['complete_list_equality'] is None and r['cutoff_eligible_2022'] for r in full)==40
 safe(full)
 for n,rows in [('inventory',inv),('candidate-queue',q),('pair-classifications',full)]:csv_parity(ROOT/'data/evidence/thomas'/f'{n}.csv',rows)
 assert read(ROOT/'data/evidence/thomas/prior-observation-caveats.json')==t['prior_caveats']
 assert read(ROOT/'data/evidence/thomas/date-metadata.json')==t['date_metadata']
 cov=y['covenant'];records=cov['records'];assert len(records)==14 and len({r['id'] for r in records})==14
 assert Counter(r['preacher']['name'] for r in records)=={'Dr. Kevin DeYoung':13,'Derek Wells':1}
 assert all(r['written_body']['available'] is True for r in records)
 assert sum(r['event_on_or_before_2022_11_30'] is True for r in records)==3
 assert sum(r['observation_basis']=='new detail observation' for r in records)==11
 assert sum(r['written_body']['ending']['page_boundary_verified'] is True for r in records)==7
 assert sum('inherited concluding prayer' in r['written_body']['ending']['status'] for r in records)==2
 assert cov['counts']['ending_not_separately_checked']==5
 facts=next(r for r in records if r['title']=='Facts Still Matter')
 assert facts['sermon_header_date']=='2025-04-28' and facts['service_label']=='Sunday Morning' and facts['sermon_event_date'] is None
 assert date.fromisoformat(facts['sermon_header_date']).weekday()==0
 f=y['fourth'];edges=f['edges'];assert len(edges)==53 and len({r['pair_id'] for r in edges})==53
 sm=[r for r in edges if r['same_calendar_month'] is True];assert len(sm)==3 and len({r['post_url'] for r in sm})==2
 no_links=f['diagnostic']['other_indexed_same_name_author_without_observed_text_links'];assert len(no_links)==6 and all(r['text_link_observed'] is False for r in no_links)
 assert all(isinstance(r['same_calendar_month'],bool) for r in edges)
 assert len(y['ai']['cases'])==4
 bossen=next(r for r in y['ai']['cases'] if r['id']=='ai-bossen-houston-2024');assert bossen['exposure']==['NON_SERMON_SERVICE_GENERATION']
 brewer=next(r for r in y['ai']['cases'] if r['id']=='ai-mockingbird-2022');assert brewer['event_date'] is None and brewer['church'] is None
 assert y['counts']['full_texts_hosted']==0
 for name,rows in [('source-decisions',ds['items']),('thomas-details',pages),('thomas-comparisons',pairs),('covenant-series',records),('fourth-matching',edges)]:csv_parity(ROOT/'data/evidence'/f'{name}.csv',rows)
 m=read(ROOT/'data/evidence/manifest.json')
 for r in m['files']:
  p=ROOT/'data'/r['path'];b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
 for fixture in ['=HYPERLINK("bad")',' +CMD','@X','-1+2']:assert csv_value(fixture).startswith("'")
 assert csv_value(False)=='false' and csv_value(None)==''
 for fixture in [{'reader_id':'x'},'person@example.com','<script>alert(1)</script>','file:///Users/private','中文']:
  try:safe(fixture)
  except AssertionError:pass
  else:raise AssertionError('Safety fixture accepted')
 subprocess.run([sys.executable,str(ROOT/'data/evidence/thomas/verify_pair_map.py')],check=True)
 print('PASS: baseline hashes; seven 2/2/3 routes; Thomas 88/1935/1800/14/10/20, raw labels, Sunday dates, nulls, rights and exports; Covenant 14/11+3/7+2+5 and Monday conflict; Fourth 53/3/2 and false flags; four bounded AI cases; manifests, English projection and privacy/formula checks.')
if __name__=='__main__':main()
