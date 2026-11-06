#!/usr/bin/env python3
"""Project reviewed Catholic source metadata; no source or media requests.

Usage: python3 scripts/project_catholic.py INPUT_DIRECTORY
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from project_extensions import write_csv

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = '2022-11-30'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def verify_package(source):
    manifest = read(source/'manifest.json')
    assert len(manifest['files']) == 5
    for item in manifest['files']:
        path = source/item['name']
        assert path.resolve().is_relative_to(source.resolve())
        raw = path.read_bytes()
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], item['name']

LIMITS = {
    'YALE2022-003': [
        'A local homily archive has not been identified. Historical coverage remains unknown.',
        'The Father Vidal archive in Ave Maria, Florida belongs to a different parish.',
        'Parish and diocesan lists agree on the pastor but differ on one vicar. Neither list identifies the 2022 or 2025 event speakers.',
    ],
    'YALE2022-098': [
        'A parish homily route has not been established. This is not evidence that no archive exists.',
        'A partner-parish leadership page returned 404; its search description was not accepted as appointment evidence.',
        'No 2022 or 2025 homily item was inspected.',
    ],
    'YALE2022-101': [
        'The official bilingual name and Salinas location fit the historical listing, but the exact name match remains unconfirmed.',
        'The linked media pages supplied no dated 2022 or 2025 item.',
        'The Spanish name does not establish sermon language, and current clergy names do not identify historical homilists.',
    ],
    'YALE2022-109': [
        'An official homily route exists; its 2022 and 2025 coverage remains unknown.',
        'The parish describes multiple speakers. The playlist is labelled English, but individual historical items have not been checked.',
        'The 2022 written parish note is not a verified sermon.',
    ],
    'YALE2022-116': [
        'The two June 2022 roster dates precede the current pastor’s announced July arrival.',
        'A common parish does not establish the same homilist, service time or recording format.',
        'The 2022 Easter streaming schedule describes planned services; no corresponding recording was recovered.',
    ],
    'YALE2022-127': [
        'The identified written homily is dated 2020, outside the two comparison years.',
        'Unavailable Facebook content does not establish that archives are absent or private.',
        'A current pastor listing and one 2020 homily do not establish continuous tenure or identify the 2022 and 2025 speakers.',
    ],
    'YALE2022-131': [
        'Parish and diocesan clergy lists conflict. Neither is used to assign historical sermon speakers.',
        'The Ingels succession and Jaeger retirement dates remain unknown. Jaeger’s earlier July 2008 appointment does not resolve the current conflict.',
        'No 2022 or 2025 video or manuscript was verified.',
    ],
    'YALE2022-137': [
        'The official parish advertises a Sunday 9 a.m. livestream; historical archive coverage remains unknown.',
        'The historical spelling “St. Pioux X” has not been independently linked to the candidate parish.',
        'No 2022 or 2025 transcript, language or homilist was verified.',
    ],
}
ROUTE_OUTCOMES = {
    'YALE2022-003': [
        'Parish page read; no homily archive identified. “From Our Pastor” is a biography.',
        'Pastor biography read; no dated sermon item.',
    ],
    'YALE2022-098': [
        'Parish page read; no homily archive identified. Its featured video concerns a papal prayer campaign, not a local sermon.',
        'No readable bulletin content returned; no dated bulletin item inspected.',
    ],
    'YALE2022-101': [
        'HTTP 502; no dated items inspected.',
        'Channel title and generic page footer only; no dated video metadata or media acquired.',
    ],
    'YALE2022-109': [
        'Parish describes Sunday homilies by Fr. Edgar, deacons and visiting priests; no dated item inspected.',
        'Request rate-limited; playlist dates and items were not inspected.',
        'A dated catechesis staffing note signed Fr. Jeff is visible. It is not a verified homily.',
    ],
    'YALE2022-116': [
        'Parish advertises one streamed weekend Mass with a variable schedule and links previous streams. No dated inventory inspected.',
        'Request rate-limited; no dated video metadata acquired.',
    ],
    'YALE2022-127': [
        'A Father Shields written homily is labelled September 27, 2020. The page links Facebook for online Mass.',
        'Request rate-limited; no dated items inspected.',
        'Generic platform footer only; no dated video metadata inspected.',
    ],
    'YALE2022-131': [
        'Parish page links YouTube; no dated 2022 or 2025 item inspected.',
        'Request rate-limited; no dated items inspected.',
        'Initial navigation was visible; the later page read returned HTTP 404. No text acquired.',
    ],
    'YALE2022-137': [
        'Parish page embeds a named eCatholic archive; no dated items inspected.',
        'Player page supplied no dated item metadata. No media requested; date range remains unknown.',
    ],
}

def project(source):
    verify_package(source)
    raw_reviews = read(source/'western-catholic-screen.json')
    raw_sources = read(source/'catholic-written-sources.json')
    raw_items = read(source/'catholic-written-items.json')
    baseline = {r['id']:r for r in read(ROOT/'data/extensions.json')['roster']['records']}
    identity_labels = {'strong_current_name_locality':'Current official name and locality supported', 'probable_unconfirmed':'Probable match; historical identity unconfirmed'}
    route_labels = {'homily_specific_route':'Homily-specific route', 'mass_stream_route':'Whole-Mass streaming route', 'unresolved':'Sermon route not identified'}
    conflicts = raw_reviews['summary']['current_official_listing_conflicts']
    changes = raw_reviews['summary']['documented_between_or_within_target_year_clergy_change']
    reviews = []
    for r in raw_reviews['records']:
        b = baseline[r['candidate_id']]
        assert (r['source_church_name'],r['source_county'],r['source_state'],r['roster_reported_2022_dates']) == (b['name'],b['county'],b['state'],b['dates'])
        c = r['current_identity']
        identity = {'name':c['official_name'],'spanish_name':c.get('official_spanish_name'),'locality':c['locality'],
                    'status':c['status'],'official_url':c['official_url'],'diocese':c['diocese'],
                    'diocese_url':c['diocese_url'],'evidence':c.get('evidence')}
        clergy = [{'source_url':x['url'],'date':x['source_date'],'names_roles':x['names_roles'],
                   'date_status':x['date_status'],'turnover_note':x.get('turnover_note')} for x in r['clergy_evidence']]
        routes = []
        assert len(r['routes']) == len(ROUTE_OUTCOMES[r['candidate_id']])
        for x,outcome in zip(r['routes'],ROUTE_OUTCOMES[r['candidate_id']]):
            routes.append({'type':x['type'],'url':x['url'],'outcome':outcome,
                           'target_year_items_inspected':x['target_year_items_inspected'],
                           'qualifying_sermon':x.get('qualifying_sermon_item')})
        other = [{'date':x['date'],'kind':x['kind'],'title':x['title'],
                  'author':x.get('author_as_displayed') or x.get('speaker_as_displayed'),
                  'source_url':x['url'],'date_basis':x['date_basis'],
                  'qualifying_target_year_sermon':False} for x in r['other_dated_items']]
        reviews.append({
            'id':r['candidate_id'],'name':r['source_church_name'],'county':r['source_county'],'state':r['source_state'],
            'dates':r['roster_reported_2022_dates'],'source_url':r['source_dataset_url'],'file_url':r['source_file_url'],
            'checked_on':r['checked_on'],'identity_tier':r['identity_match_tier'],
            'identity_label':identity_labels[r['identity_match_tier']],
            'route_tier':r['archive_route_tier'],'route_label':route_labels[r['archive_route_tier']],
            'year_coverage':{'2022':None,'2025':None},'current_identity':identity,
            'clergy_evidence':clergy,'clergy_conflict':r['candidate_id'] in conflicts,
            'documented_clergy_change':r['candidate_id'] in changes,
            'routes':routes,'other_dated_items':other,'limits':LIMITS[r['candidate_id']],
            'rights':'Bulk collection, transcript export and sermon redistribution rights have not been established.',
            'roster_dates_status':'These three dates come from the historical Tally. No original sermon was newly matched to them in this review.',
        })
    sources = []
    for r in raw_sources['sources']:
        sources.append({
            'id':r['source_id'],'name':r['church'],'city':r['city'],'state':r['state'],'tradition':r['tradition'],
            'official_url':r['official_url'],'archive_url':r['archive_url'],'speaker_name':r['speaker_name'],
            'speaker_role':r['speaker_role'],'speaker_source_urls':r['speaker_evidence_urls'],
            'counts':{'2022':r['counts']['2022'],'2025':r['counts']['2025'],
                      'body_observations':r['counts']['selected_body_observations'],
                      'distinct_2022_dates':r['counts'].get('2022_distinct_dates')},
            'coverage':r['coverage_status'],'affiliation':r['historical_affiliation'],
            'comparability':r['comparability'],'limits':r['cautions'],'rights':r['rights_status'],
            'rights_url':r['rights_source_url'],'pair':r.get('same_feast_pair'),
            'matching_status':r['matching_status'],'baseline_church_id':None,'historical_roster_id':None,
        })
    # These are researcher descriptions of selected PDFs, never manuscript text.
    body_summaries = {
        ('catholic-irvine-tony','2022-01-08'):'Two pages of homily prose on baptism, including questions to listeners, catechism and Scripture quotations.',
        ('catholic-irvine-tony','2022-12-11'):'Two pages of homily prose on joy, prophecy and repentance. A local penance-service announcement names St Thomas More; the text is signed Deacon Tony.',
        ('catholic-irvine-tony','2025-01-12'):'Homily prose followed by substantial baptismal-rite wording and a list of ritual elements. It combines author prose with quoted liturgy.',
        ('catholic-irvine-tony','2025-02-09'):'Three pages on calling, trust and World Marriage Day, including Scripture and sacramental teaching. Apparent character substitutions require checking before text analysis.',
        ('catholic-ave-maria-florida-vidal','2025-07-27'):'Three pages of developed homily prose with numbered sections, Scripture and catechism references, and a conclusion.',
        ('catholic-ave-maria-florida-vidal','2025-05-09'):'Three-page written address to graduates, with acknowledgements, three developed points and a conclusion.',
        ('catholic-ave-maria-florida-vidal','2022-07-24'):'Four-page PDF: liturgical readings on page one; a named, dated homily begins on page two and continues through page four.',
        ('catholic-ave-maria-florida-vidal','2022-01-02'):'Three pages of developed homily prose with headings, scriptural references, a cited passage and a closing exhortation.',
    }
    items = []
    for r in raw_items['items']:
        observed = r['selected_body_observed']
        date_basis = r.get('date_basis')
        if date_basis:
            date_basis = date_basis.replace('tool/PDF document title','PDF document title').replace('extracted PDF body','inspected PDF body')
        items.append({
            'id':'catholic-item:'+hashlib.sha256(r['source_url'].encode()).hexdigest()[:16],
            'source_id':r['source_id'],'date':r['date_as_recorded'],'title':r['title_as_displayed'],
            'source_url':r['source_url'],'archive_url':r['archive_url'],'format':r['format'],
            'body_observed':observed,'publication_date':r['publication_date'],
            'attribution_scope':r['speaker_attribution_scope'],'pages':r.get('pages'),
            'date_basis':date_basis,'body_summary':body_summaries.get((r['source_id'],r['date_as_recorded'])) if observed else None,
            'byline':r.get('byline_as_displayed'),'byline_basis':r.get('byline_basis'),
            'event_observation':r.get('event_as_observed'),'cutoff':r['relative_to_2022_11_30'],
            'delivery_date':None,
        })
    return {
        'checked_on':'2026-11-06','cutoff':CUTOFF,
        'counts':{
            'roster_reviews':len(reviews),'supported_current_matches':6,'probable_matches':2,
            'homily_routes':2,'mass_stream_routes':4,'unresolved_routes':2,'unknown_year_cells':16,
            'roster_date_rows':24,'roster_dates_before_cutoff':23,'roster_dates_on_or_after_cutoff':1,
            'freshly_matched_target_sermons':0,'supplemental_written_sources':len(sources),
            'written_item_links':len(items),'selected_body_observations':sum(x['body_observed'] for x in items),
            'full_texts_hosted':0,'clergy_conflicts':len(conflicts),'documented_clergy_changes':len(changes),
        },
        'scope':'Eight Catholic groups in the historical Yale roster located in Western states. These reviews are a subset of the 150 historical entities, not additional churches or a census of western Catholic parishes.',
        'roster_reviews':reviews,'sources':sources,'items':items,
        'limits':[
            'The 24 historical Tally dates are not 24 newly matched sermons. Both target-year coverage fields remain unknown for all eight groups.',
            'Current parish identity, current clergy role and historical event speaker are separate claims.',
            'The two supplementary written sources are outside the eight roster reviews. They are not merged into the 150 historical entities or 86 supported identities.',
            '49 PDF links were observed, and eight selected bodies were inspected for metadata and genre. No manuscript bodies, recordings or captions are hosted.',
            'The November 30, 2022 cutoff is descriptive and does not establish AI use or non-use.',
        ],
    }

def write_outputs(data):
    (ROOT/'data/catholic.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    names = {r['id']:r['name'] for r in data['sources']}
    write_csv(ROOT/'data/catholic-written-items.csv',
        ['ID','Source ID','Church','Recorded date','Title','Format','Selected body inspected','Publication date','Pages','Date basis','Author as printed','Byline evidence','Attribution scope','Event or rite observation','Researcher summary','Relative to 2022-11-30','Verified delivery date','Original PDF','Archive'],
        [[r['id'],r['source_id'],names[r['source_id']],r['date'],r['title'],r['format'],str(r['body_observed']).lower(),r['publication_date'],r['pages'],r['date_basis'],r['byline'],r['byline_basis'],r['attribution_scope'],r['event_observation'],r['body_summary'],r['cutoff'],r['delivery_date'],r['source_url'],r['archive_url']] for r in data['items']])
    write_csv(ROOT/'data/catholic-roster-screens.csv',
        ['Historical ID','Historical church name','Historical county','Historical state','Historical source dates','Current identity assessment','Candidate current name','Candidate locality','Diocese','Route assessment','2022 coverage','2025 coverage','Clergy listing conflict','Documented clergy change','Limits','Historical dataset','Official parish','Official diocese','Observed route URLs'],
        [[r['id'],r['name'],r['county'],r['state'],' | '.join(r['dates']),r['identity_label'],r['current_identity']['name'],r['current_identity']['locality'],r['current_identity']['diocese'],r['route_label'],'Unknown','Unknown',str(r['clergy_conflict']).lower(),str(r['documented_clergy_change']).lower(),' | '.join(r['limits']),r['source_url'],r['current_identity']['official_url'],r['current_identity']['diocese_url'],' | '.join(x['url'] for x in r['routes'])] for r in data['roster_reviews']])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_directory',type=Path)
    args=parser.parse_args()
    data=project(args.input_directory)
    write_outputs(data)
    print('Projected eight historical-roster reviews and two separate written sources: 49 PDF links, eight selected body observations; no full text.')
