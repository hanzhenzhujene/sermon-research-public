#!/usr/bin/env python3
"""Validate separate public extensions without fetching sources or media."""
import csv
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))

def fail(condition, message):
    assert condition, message

def sunday_dates(year, month=None):
    day = dt.date(year, 1, 1)
    result = set()
    while day.year == year:
        if day.weekday() == 6 and (month is None or day.month == month):
            result.add(day.isoformat())
        day += dt.timedelta(days=1)
    return result

def csv_rows(name):
    with (ROOT/'data'/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def normalized_title(value):
    return re.sub(r'[^a-z0-9]+', '', value.casefold())

def safety(value, path='root'):
    blocked_keys = {'email','phone','street_address','latitude','longitude','coordinates','password','token','credential','credentials','raw_body','body','transcript','full_text','reader_id','workflow','reviewer'}
    if isinstance(value, dict):
        fail(not blocked_keys.intersection(value), 'Nonpublic field at '+path)
        for k,v in value.items(): safety(v,path+'.'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value): safety(v,path+'['+str(i)+']')
    elif isinstance(value,str):
        fail(not re.search(r'[\u3400-\u9fff]',value), 'Non-English prose at '+path)
        fail(not any(x in value for x in ['/Users/','/workspace/','libfile_','reader://','siwc_bypass','BEGIN PRIVATE KEY','github.com/hanzhenzhujene/ai-preaching-comparison']), 'Private/internal text at '+path)
        fail(not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',value), 'Contact address at '+path)
        fail(len(value)<2500, 'Unexpected body-length field at '+path)
        if value.startswith(('http://','https://','javascript:','data:','file:')):
            u=urlsplit(value)
            fail(u.scheme=='https' and bool(u.netloc) and not u.username and not u.password, 'Unsafe source URL at '+path)
            fail(not re.search(r'(?:token|signature|sig|password|key)=',u.query,re.I), 'Credential-like URL at '+path)

def main():
    e=read('data/extensions.json');d=read('data/catalogue.json');f=read('data/feasibility.json')
    fail(hashlib.sha256((ROOT/'data/catalogue.json').read_bytes()).hexdigest()=='73c4e721c85560aa9dadf2c6d38002c8a686885dc14732f84f2e2609cd000dcc', 'Original identity/item/source catalogue changed')
    fail((len(d['churches']),len(d['items']),len(d['sources']))==(86,47,83),'Baseline totals changed')
    fail(sum(len(x['people']) for x in d['churches'])==41,'Clergy total changed')
    fail(len(f['screens'])==12 and len(f['supplemental'])==3,'Feasibility populations changed')
    for name,digest in [('fourth','2ba8945efbf2e87f13b5ea4ea886b45f24e4e07de05ab183d12e04ad5e931add'),('thomas','c2c0120ab3b16ab5ed210d6f5960b4de20640817f834bb592fe2b787e67ade37')]:
        fail(hashlib.sha256(json.dumps(f[name],sort_keys=True,ensure_ascii=False).encode()).hexdigest()==digest,name+' evidence changed')
    r=e['roster'];churches=r['records'];events=r['events'];by_id={x['id']:x for x in churches}
    fail(len(churches)==len(by_id)==150,'Historical entity count/IDs')
    fail(len(events)==len({x['id'] for x in events})==450,'Historical date-row count/IDs')
    fail(len({(x['name'].casefold(),x['county'],x['state']) for x in churches})==150,'Name/locality entity uniqueness')
    fail(len({(x['county'],x['state']) for x in churches})==50,'County/state count')
    states=Counter(x['state'] for x in churches)
    fail(len(states)==31 and 'District of Columbia' in states,'30 states plus DC')
    fail(Counter(x['tradition'] for x in churches)=={'Catholic':50,'Evangelical Protestant':50,'Mainline Protestant':50},'Tradition counts')
    fail(states==r['summary']['states'] and Counter(x['denomination'] for x in churches)==r['summary']['denominations'],'Roster summary parity')
    fail(all(x['church_id'] in by_id for x in events),'Orphan historical event')
    fail(set(Counter(x['church_id'] for x in events).values())=={3},'Three rows per entity')
    for church in churches:
        rows=[x for x in events if x['church_id']==church['id']]
        fail(sorted(x['date'] for x in rows)==sorted(church['dates']),'Church/event date join '+church['id'])
        fail(len(church['dates'])==church['event_count']==3,'Church date count')
        fail(church['before_cutoff_count']==sum(x<CUTOFF for x in church['dates']),'Church cutoff count')
        fail(church['speaker'] is None and church['official_url'] is None,'Unverified roster identities promoted')
    fail(all(x['speaker'] is None and x['sermon_url'] is None for x in events),'Unverified event speaker/URL promoted')
    dates=Counter(x['date'] for x in events)
    fail(dates==r['summary']['date_counts'],'Source date summary')
    fail((sum(n for day,n in dates.items() if day<CUTOFF),dates.get(CUTOFF,0),sum(n for day,n in dates.items() if day>CUTOFF))==(444,0,6),'Historical cutoff counts')
    fail((dates['2022-06-26'],dates['2022-11-05'],dates['2022-11-06'])==(150,3,147),'Deliberate date strata')
    fail(r['summary']['date_range']==[min(dates),max(dates)],'Date range')
    overlap=e['overlap']
    fail(overlap['candidate_count']==1 and overlap['accepted_matches']==0 and overlap['actual_overlap'] is None,'Overlap uncertainty lost')
    fail(overlap['candidate']['id']=='YALE2022-133' and 'Morris County' in overlap['candidate']['historical_locality'] and 'Passaic County' in overlap['candidate']['decision'],'Rejected county collision lost')
    fail(by_id['YALE2022-133']['county']=='Morris County','Collision lookup')
    o=e['orthodox'];items=o['records'];items_by_id={x['id']:x for x in items}
    fail(len(items)==len(items_by_id)==97,'Holy Trinity items/IDs')
    fail(Counter(x['year'] for x in items)=={2022:47,2025:50},'Holy Trinity annual items')
    fail(all(x['delivery_date'] is None and x['upload_date'] is None and x['duration'] is None for x in items),'Unverified media facts promoted')
    fail(all(x['is_sunday']==(dt.date.fromisoformat(x['date']).weekday()==6) for x in items),'Sunday classification')
    for a in o['annual']:
        rows=[x for x in items if x['year']==a['year']]; date_set={x['date'] for x in rows};sundays=sunday_dates(a['year'])
        fail(len(rows)==a['entries'] and len(date_set)==a['unique_dates'],'Annual metadata count')
        fail(len(sundays)==a['sundays_total']==52,'Calendar denominator')
        fail(len(date_set&sundays)==a['sundays_observed'],'Literal Sunday numerator')
        fail(sorted(sundays-date_set)==a['unobserved_sundays'],'Unobserved Sunday dates')
        fail(Counter(x['speaker_display'] or 'unknown' for x in rows)==a['speaker_counts'],'Speaker counts')
        fail(sum(x['speaker_as_stated'] is None for x in rows)==a['unknown_speakers'],'Unknown speaker count')
        fail(sum(x['type']=='youth sermon' for x in rows)==a['youth_items'],'Youth item count')
        fail({day:n for day,n in Counter(x['date'] for x in rows).items() if n>1}==a['same_date_entries'],'Repeated dates')
    fail([x['sundays_observed'] for x in o['annual']]==[39,47],'Annual Sunday totals')
    fail(len(o['monthly'])==24,'Monthly coverage records')
    for m in o['monthly']:
        rows=[x for x in items if x['date'].startswith(m['month'])]; date_set={x['date'] for x in rows}
        sundays=sunday_dates(m['year'],int(m['month'][-2:]))
        fail(len(rows)==m['entries'] and len(date_set)==m['unique_dates'],'Monthly records')
        fail(len(sundays)==m['sundays_total'] and sorted(date_set&sundays)==m['observed_sunday_dates'],'Monthly Sunday denominator/numerator')
        fail(sorted(sundays-date_set)==m['unobserved_sundays'],'Monthly missing dates')
    for s in o['speaker_comparison']:
        pre=[x for x in items if x['date']<CUTOFF and x['speaker_directory_name']==s['speaker']]
        post=[x for x in items if x['year']==2025 and x['speaker_directory_name']==s['speaker']]
        months=sorted({x['date'][5:7] for x in pre});same=[x for x in post if x['date'][5:7] in months]
        fail((len(pre),len(post),len(same))==(s['pre_count'],s['post_count'],s['same_month_count']),'Speaker subset counts')
        fail({x['id'] for x in pre}==set(s['pre_ids']) and {x['id'] for x in post}==set(s['post_ids']),'Speaker subset joins')
        fail(months==s['pre_months'] and Counter(x['type'] for x in pre)==s['pre_types'] and Counter(x['type'] for x in same)==s['same_month_types'],'Speaker calendar and genre caveat')
    aris=next(x for x in o['speaker_comparison'] if x['speaker']=='Aris Metrakos')
    fail(aris['pre_months']==['01','02','03','04','05','06'] and aris['pre_types']['youth sermon']==7,'Aris calendar/genre imbalance')
    earlier=next(x for x in f['screens'] if x['id']=='holy_trinity_sf')['observations']
    fail(len(earlier)==o['earlier_october_count']==8,'Earlier October count')
    for row in earlier:
        matches=[x for x in items if x['date']==row['date'] and normalized_title(x['title'])==normalized_title(row['title'])]
        fail(len(matches)==1,'October observation does not join exactly '+row['title'])
        fail(matches[0]['speaker_as_stated']==row['speaker'],'October attribution changed')
    fail(len([x for x in items if x['date'][5:7]=='10'])==8,'Nested October set')
    conflicts=[x for x in items if x['filename_date'] and x['filename_date']!=x['date']]
    fail(len(conflicts)==7,'Filename/date conflicts must remain visible')
    combined=next(x for x in items if x['type']=='combined sermon and reminders')
    fail(combined['speaker_as_stated']=='His Eminence' and combined['speaker_directory_name'] is None and combined['additional_attribution']['role']=='reminders','Reminders attribution promoted to sermon speaker')
    studies=e['studies'];fail(len(studies)==len({x['id'] for x in studies})==6,'Study note count')
    fail(next(x for x in studies if x['id']=='mokski-2024')['status']=='Unverified discovery lead','Harvard discovery status')
    fail(all(x['speaker_panel_ready'] is not True for x in studies),'Unverified longitudinal panel claim')
    for filename,records,id_key in [('published-study-churches.csv',churches,'id'),('published-study-events.csv',events,'id'),('holy-trinity-archive.csv',items,'id')]:
        csv_data=csv_rows(filename)
        fail(len(csv_data)==len(records),filename+' row parity')
        fail([x['ID'] for x in csv_data]==[x[id_key] for x in records],filename+' ID parity')
        for row in csv_data:
            for value in row.values():
                fail(not re.match(r'^\s*[=+@-]',value),filename+' formula injection')
    csv_roster=csv_rows('published-study-churches.csv')
    for a,b in zip(churches,csv_roster):
        fail((a['name'],a['county'],a['state'],a['tradition'],a['denomination'],' | '.join(a['dates']))==(b['Church as listed'],b['County'],b['State'],b['Source-reported tradition'],b['Source-reported denomination'],b['Source-recorded dates']),'Roster CSV field parity')
    counts=e['counts']
    fail((counts['historical_entities'],counts['historical_date_rows'],counts['orthodox_archive_items'],counts['study_notes'],counts['full_texts_hosted'])==(150,450,97,6,0),'Extension counters')
    safety(e)
    print('PASS: baseline preservation; 150/450 roster joins, strata and CSV parity; 97 archive items, 39/52 and 47/52 Sundays, eight nested October observations; speaker/calendar/genre limits; six study notes; public-field and URL safety.')

CUTOFF='2022-11-30'
if __name__=='__main__':
    main()
