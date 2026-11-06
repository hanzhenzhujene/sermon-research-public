#!/usr/bin/env python3
"""Check Catholic metadata joins, dates, evidence limits and public exports."""
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path
from validate_extensions import safety

ROOT=Path(__file__).resolve().parents[1]
CUTOFF='2022-11-30'

def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))

def rows(name):
    with (ROOT/'data'/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def main():
    for name,digest in [
        ('data/catalogue.json','73c4e721c85560aa9dadf2c6d38002c8a686885dc14732f84f2e2609cd000dcc'),
        ('data/extensions.json','cec9cab1945ba4dcced84e40c58c8b1e14b86fe0998ddfc5d6ee53aa41968977'),
        ('data/feasibility.json','9ed1bc0fc1c8b9fa57baeb93209bbf7311a591fd0f643f2c88cc56c312edf56c'),
    ]:
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Prior evidence changed: '+name
    c=read('data/catholic.json');e=read('data/extensions.json');base=read('data/catalogue.json')
    assert (len(base['churches']),len(base['items']),len(base['sources']),sum(len(x['people']) for x in base['churches']))==(86,47,83,41)
    assert len(e['roster']['records'])==150 and len(e['roster']['events'])==450
    reviews=c['roster_reviews'];sources=c['sources'];items=c['items'];counts=c['counts']
    expected={'YALE2022-003','YALE2022-098','YALE2022-101','YALE2022-109','YALE2022-116','YALE2022-127','YALE2022-131','YALE2022-137'}
    assert len(reviews)==8 and {r['id'] for r in reviews}==expected
    by_id={r['id']:r for r in e['roster']['records']}
    for r in reviews:
        b=by_id[r['id']]
        assert (r['name'],r['county'],r['state'],r['dates'])==(b['name'],b['county'],b['state'],b['dates']),r['id']
        assert b['tradition']=='Catholic'
        assert r['source_url']==b['source_url'] and r['file_url']==b['file_url']
        assert r['year_coverage']=={'2022':None,'2025':None},'Unknown coverage must not become zero'
        assert len(r['dates'])==3
        for item in r['other_dated_items']:
            assert item['qualifying_target_year_sermon'] is False
    assert Counter(r['identity_tier'] for r in reviews)=={'strong_current_name_locality':6,'probable_unconfirmed':2}
    assert Counter(r['route_tier'] for r in reviews)=={'homily_specific_route':2,'mass_stream_route':4,'unresolved':2}
    assert sum(len(r['year_coverage']) for r in reviews)==16
    historical_dates=[date for r in reviews for date in r['dates']]
    assert len(historical_dates)==24
    assert sum(date<CUTOFF for date in historical_dates)==23 and sum(date>=CUTOFF for date in historical_dates)==1
    assert {r['id'] for r in reviews if r['clergy_conflict']}=={'YALE2022-003','YALE2022-131'}
    assert {r['id'] for r in reviews if r['documented_clergy_change']}=={'YALE2022-109','YALE2022-116'}
    reviewed={r['id']:r for r in reviews}
    assert reviewed['YALE2022-101']['name']=='Santa Maria Navidad Catholic Church'
    assert reviewed['YALE2022-101']['current_identity']['name']=='St. Mary of the Nativity Catholic Church'
    assert reviewed['YALE2022-137']['name']=='St. Pioux X Catholic Church'
    assert reviewed['YALE2022-137']['current_identity']['name']=='St. Pius X Catholic Church'
    for cid in ['YALE2022-098','YALE2022-101','YALE2022-109','YALE2022-127']:
        assert any(x['turnover_note'] for x in reviewed[cid]['clergy_evidence']),'Lost tenure limit '+cid
    assert '2023' in ' '.join(x['turnover_note'] or '' for x in reviewed['YALE2022-109']['clergy_evidence'])
    loveland=reviewed['YALE2022-116']
    assert any(x['date']=='2022-04-29' and 'July' in x['names_roles'][0]['role'] for x in loveland['clergy_evidence'])
    assert sum(day<'2022-07-01' for day in loveland['dates'])==2
    non_sermon=[x for r in reviews for x in r['other_dated_items']]
    assert len(non_sermon)==5 and sum(x['kind']=='Written homily' for x in non_sermon)==1
    assert next(x for x in non_sermon if x['kind']=='Written homily')['date']=='2020-09-27'
    # The two official staff lists are separate claims; conflicting people are not flattened.
    paul=reviewed['YALE2022-131']['clergy_evidence']
    assert any(p['name']=='Fr. Kyle Ingels' and p['role']=='Pastor' for p in paul[0]['names_roles'])
    assert any(p['name']=='Msgr. Robert E. Jaeger' and p['role']=='Listed as pastor' for p in paul[1]['names_roles'])
    assert len(sources)==2 and len({s['id'] for s in sources})==2
    assert all(s['baseline_church_id'] is None and s['historical_roster_id'] is None for s in sources)
    assert len(items)==len({r['id'] for r in items})==len({r['source_url'] for r in items})==49
    source_by_id={s['id']:s for s in sources}
    assert all(r['source_id'] in source_by_id for r in items)
    assert sum(r['body_observed'] for r in items)==8
    assert all(r['publication_date'] is None and r['delivery_date'] is None for r in items)
    for r in items:
        assert r['id']=='catholic-item:'+hashlib.sha256(r['source_url'].encode()).hexdigest()[:16]
        assert r['cutoff']==('before' if r['date']<CUTOFF else 'on_or_after'),r['title']
        assert r['archive_url']==source_by_id[r['source_id']]['archive_url']
        if r['body_observed']:
            assert r['pages'] in (2,3,4) and r['body_summary']
        else:
            assert r['pages'] is None and r['body_summary'] is None and r['byline'] is None and r['event_observation'] is None
    assert Counter(r['cutoff'] for r in items)=={'before':44,'on_or_after':5}
    for sid,expected_years in [('catholic-irvine-tony',{'2022':7,'2025':2}),('catholic-ave-maria-florida-vidal',{'2022':38,'2025':2})]:
        selected=[r for r in items if r['source_id']==sid]
        assert Counter(r['date'][:4] for r in selected)==expected_years
        assert sum(r['body_observed'] for r in selected)==source_by_id[sid]['counts']['body_observations']==4
        assert {str(y):n for y,n in expected_years.items()}=={y:source_by_id[sid]['counts'][y] for y in expected_years}
    tony=source_by_id['catholic-irvine-tony'];vidal=source_by_id['catholic-ave-maria-florida-vidal']
    assert tony['speaker_name']=='Tony Patronite' and tony['speaker_role']=='Historical deacon; died 2025-02-17'
    assert 'Historical pastor' in vidal['speaker_role'] and '2026-10-19' in vidal['speaker_role']
    florida=[r for r in items if r['source_id']==vidal['id']]
    dates2022=[r['date'] for r in florida if r['date'][:4]=='2022']
    assert len(set(dates2022))==35 and sum(n>1 for n in Counter(dates2022).values())==3
    assert (min(dates2022),max(dates2022))==('2022-01-01','2022-10-09')
    dates2025=sorted(dt.date.fromisoformat(r['date']) for r in florida if r['date'][:4]=='2025')
    assert (dates2025[1]-dates2025[0]).days==79
    assert any(r['date']=='2025-05-09' and 'Baccalaureate Mass' in (r['event_observation'] or '') for r in florida)
    assert any(r['date']=='2022-07-24' and 'Extraordinary Form' in (r['event_observation'] or '') for r in florida)
    tony_items=[r for r in items if r['source_id']==tony['id']]
    conflict=next(r for r in tony_items if r['date']=='2025-02-09')
    assert '2026' in conflict['source_url'] and '2025-02-09' in conflict['date_basis'] and '2026' in conflict['date_basis']
    assert next(r for r in tony_items if r['date']=='2022-12-11')['cutoff']=='on_or_after'
    assert 'no date' in next(r for r in tony_items if r['date']=='2022-01-08')['date_basis']
    csv_items=rows('catholic-written-items.csv');csv_reviews=rows('catholic-roster-screens.csv')
    assert len(csv_items)==49 and len(csv_reviews)==8
    assert [x['ID'] for x in csv_items]==[r['id'] for r in items]
    assert [x['Historical ID'] for x in csv_reviews]==[r['id'] for r in reviews]
    for r,x in zip(items,csv_items):
        assert (r['date'],r['title'],r['source_url'],r['event_observation'] or '',str(r['body_observed']).lower(),r['cutoff'])==(x['Recorded date'],x['Title'],x['Original PDF'],x['Event or rite observation'],x['Selected body inspected'],x['Relative to 2022-11-30'])
        assert x['Verified delivery date']=='' and x['Publication date']==''
    for r,x in zip(reviews,csv_reviews):
        assert (r['name'],r['county'],r['state'],' | '.join(r['dates']))==(x['Historical church name'],x['Historical county'],x['Historical state'],x['Historical source dates'])
        assert x['2022 coverage']==x['2025 coverage']=='Unknown'
    assert counts=={
        'roster_reviews':8,'supported_current_matches':6,'probable_matches':2,'homily_routes':2,'mass_stream_routes':4,
        'unresolved_routes':2,'unknown_year_cells':16,'roster_date_rows':24,'roster_dates_before_cutoff':23,
        'roster_dates_on_or_after_cutoff':1,'freshly_matched_target_sermons':0,'supplemental_written_sources':2,
        'written_item_links':49,'selected_body_observations':8,'full_texts_hosted':0,'clergy_conflicts':2,'documented_clergy_changes':2,
    }
    safety(c)
    for row in csv_items+csv_reviews:
        for cell in row.values():
            assert not cell.lstrip().startswith(('=','+','-','@')),'Unescaped CSV formula'
    serialized=json.dumps(c,ensure_ascii=False)
    assert 'tool/PDF' not in serialized and 'stopped exact' not in serialized.lower()
    print('PASS: eight exact historical joins; 6/2 identity tiers, 2/4/2 routes, 16 unknown year cells; 49 PDF links/eight selected bodies; 7/2 + 38/2 counts; 35 Florida dates/79-day gap; conflicts, turnover, rites, cutoff and CSV safety; all prior data unchanged.')

if __name__=='__main__':
    main()
