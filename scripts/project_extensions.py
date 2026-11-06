#!/usr/bin/env python3
"""Project reviewed public metadata into separate study-roster and archive views.

Usage: python3 scripts/project_extensions.py INPUT_DIRECTORY
Only explicitly selected fields are published. No source-body or media acquisition.
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = '2022-11-30'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def safe_cell(value):
    value = '' if value is None else str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value

def write_csv(path, headers, rows):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(headers)
    writer.writerows([[safe_cell(v) for v in row] for row in rows])
    path.write_text(out.getvalue(), encoding='utf-8')

def verify_package(source):
    manifest = read(source / 'manifest.json')
    assert len(manifest['files']) == 12
    for item in manifest['files']:
        path = source / item['path']
        assert path.resolve().is_relative_to(source.resolve())
        raw = path.read_bytes()
        assert len(raw) == item['bytes'], item['path']
        assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']

def project(source):
    verify_package(source)
    roster = read(source / 'published-study-churches.json')
    events = read(source / 'published-study-events.json')
    summary = read(source / 'published-study-summary.json')
    raw_orthodox = read(source / 'orthodox-annual-items.json')
    coverage = read(source / 'orthodox-annual-coverage.json')
    subsets = read(source / 'orthodox-speaker-date-subsets.json')
    calendars = read(source / 'orthodox-speaker-calendar-caveat.json')
    crosswalk = read(source / 'external-roster-crosswalk.json')
    studies = read(source / 'existing-research-audit.json')
    churches = [{
        'id': r['candidate_id'], 'name': r['church_name'], 'county': r['county'],
        'state': r['state'], 'tradition': r['tradition'], 'denomination': r['denomination'],
        'dates': r['sermon_dates'], 'event_count': r['event_count'],
        'before_cutoff_count': r['strictly_before_2022_11_30_event_count'],
        'county_source_label': r['county_source_label'],
        'source_url': r['source_dataset'], 'file_url': r['source_file'],
        'speaker': None, 'official_url': None, 'current_identity_status': 'Not independently checked',
    } for r in roster['records']]
    event_rows = [{
        'id': r['event_id'], 'church_id': r['church_candidate_id'],
        'date': r['source_recorded_date'], 'date_label': r['source_date_label'],
        'sermon_url': r['original_sermon_url'], 'speaker': r['individual_speaker'],
    } for r in events['records']]
    orthodox_rows = [{
        'id': r['item_id'], 'year': r['year'], 'title': r['title_as_displayed'],
        'date': r['date_iso_from_display'], 'date_label': r['date_label_as_displayed'],
        'archive_heading': r['heading_as_displayed'], 'date_basis': r['date_semantics'],
        'is_sunday': r['is_calendar_sunday'], 'speaker_as_stated': r['speaker_as_stated'],
        'speaker_directory_name': r['speaker_normalized'],
        'speaker_display': r['speaker_normalized'] or r['speaker_as_stated'],
        'speaker_evidence': r['speaker_evidence'], 'directory_url': r['speaker_directory_source'],
        'directory_caveat': r['speaker_directory_caveat'],
        'additional_attribution': r['additional_attribution'], 'guest_label': r['explicit_guest_label'],
        'type': r['service_or_item_type'], 'source_url': r['archive_url'],
        'media_url': r['media_url_observed'], 'filename': r['media_filename'],
        'filename_date': r['filename_date_like_prefix'], 'delivery_date': None,
        'upload_date': r['upload_date'], 'duration': r['duration'], 'notes': r['metadata_flags'],
    } for r in raw_orthodox['records']]
    annual = [{
        'year': r['year'], 'entries': r['visible_entries'],
        'unique_dates': r['unique_displayed_dates'], 'first_date': r['first_displayed_date'],
        'last_date': r['last_displayed_date'], 'sundays_total': r['calendar_sundays'],
        'sundays_observed': r['observed_sunday_dates'], 'unobserved_sundays': r['unobserved_sundays'],
        'non_sunday_entries': r['nonsunday_entries'], 'same_date_entries': r['same_date_multiple_entries'],
        'speaker_counts': r['speaker_item_counts'], 'unknown_speakers': r['unknown_item_speakers'],
        'role_only_speakers': r['role_only_unresolved_speaker_items'], 'youth_items': r['youth_sermon_items'],
    } for r in coverage['annual']]
    monthly = [{
        'year': r['year'], 'month': r['month'], 'entries': r['entries'],
        'unique_dates': r['unique_displayed_dates'], 'sundays_total': r['calendar_sundays'],
        'sundays_observed': r['observed_sundays'], 'observed_sunday_dates': r['observed_sunday_dates'],
        'unobserved_sundays': r['unobserved_sundays'], 'non_sunday_dates': r['nonsunday_displayed_dates'],
    } for r in coverage['monthly']]
    comparison = []
    for r in calendars['records']:
        s = next(x for x in subsets['speaker_counts'] if x['directory_linked_name'] == r['speaker'])
        comparison.append({
            'speaker': r['speaker'], 'pre_count': r['pre_cutoff_count'], 'pre_months': r['pre_months'],
            'post_count': r['post_all_year_count'], 'same_month_count': r['post_same_calendar_months_count'],
            'pre_types': r['pre_item_types'], 'same_month_types': r['post_same_month_item_types'],
            'pre_ids': s['2022_before_cutoff_item_ids'], 'post_ids': s['2025_item_ids'],
            'full_2022_count': s['2022_full_year_items'], 'excluded_2022': s['2022_excluded_at_or_after_cutoff'],
            'limit': 'Names link candidate entries only. Calendar months, youth sermons, feast days and other service types differ; historical speaker identity and comparable delivery are not independently verified.',
        })
    # Keep published scale, accessible artifacts and local retained material in separate fields.
    reported = {
        'lendway-yale-2026': '450 Tally date rows grouped into 150 church-name/county/state entities, with three dates each.',
        'kaurov-2025': 'For Roman Catholic sources, the study reports 1,903 historically active church-linked YouTube channels, 1,013,724 collected videos and 707,584 English-captioned videos. These include whole services and other communication.',
        'pew-2019': '49,719 sermons from 6,431 churches; 38,630 church websites selected. This is published study scale, not material acquired here.',
        'pew-2021': '12,832 items; the methodology gives both 2,146 and 2,143 churches. The discrepancy remains unresolved.',
        'boussalis-coan-holman': 'The paper reports over 110,000 sermons. Its repository describes a separate 10,000-sermon token sample whose binary contents were not independently checked here.',
        'mokski-2024': 'Not verified.',
    }
    study_names = {
        'lendway-yale-2026': 'Lendway · Yale Dataverse',
        'kaurov-2025': 'Kaurov et al. · Unspoken crisis',
        'pew-2019': 'Pew · Digital Pulpit 2019',
        'pew-2021': 'Pew · Fall 2020 sermons',
        'boussalis-coan-holman': 'Boussalis, Coan & Holman',
        'mokski-2024': 'Mokski · Harvard thesis lead',
    }
    records = []
    for r in studies['records']:
        is_lead = r['id'] == 'mokski-2024'
        records.append({
            'id': r['id'], 'name': study_names[r['id']], 'citation': r['citation'], 'source_url': r['url'],
            'repository_url': r.get('repository_url'), 'period': r.get('study_period'),
            'status': 'Unverified discovery lead' if is_lead else r['artifact_type'],
            'reported_scale': reported[r['id']], 'available': r['available_now'],
            'holdings': '150 historical entity records and 450 source dates, metadata only.' if r['id']=='lendway-yale-2026' else 'Citation and source notes only; no underlying corpus acquired.',
            'rights': r.get('rights') or r.get('repository_license_observation') or 'Reuse terms not verified.',
            'linkage': r.get('linkage') or 'Church, speaker and original-item linkage not verified.',
            'next_action': r['recommended_use'], 'warning': r.get('warning') or r.get('count_warning'),
            'speaker_panel_ready': r['speaker_panel_ready'], 'checked_on': studies['checked_on'],
        })
    collision = crosswalk['reviewed_collision']
    data = {
        'checked_on': '2026-11-06',
        'counts': {'historical_entities': len(churches), 'historical_date_rows': len(event_rows),
                   'historical_states': 30, 'historical_dc': True, 'historical_county_state_pairs': 50,
                   'orthodox_archive_items': len(orthodox_rows), 'orthodox_nested_october_items': 8,
                   'study_notes': len(records), 'full_texts_hosted': 0},
        'roster': {
            'title': 'Historical published-study roster', 'citation': records[0]['citation'],
            'source_url': roster['source'], 'source_version': roster['source_version'],
            'file_url': roster['data_file_url'], 'license': roster['license'],
            'unit': roster['unit'], 'date_basis': roster['date_semantics'], 'records': churches,
            'events': event_rows, 'cutoff': CUTOFF,
            'summary': {
                'traditions': dict(sorted(Counter(r['tradition'] for r in churches).items())),
                'states': dict(sorted(Counter(r['state'] for r in churches).items())),
                'denominations': dict(sorted(Counter(r['denomination'] for r in churches).items())),
                'date_counts': summary['event_dates_iso_counts'], 'date_range': summary['source_recorded_date_range'],
                'before_cutoff': summary['strictly_before_2022_11_30_events'],
                'on_cutoff': summary['on_2022_11_30_events'], 'after_cutoff': summary['after_2022_11_30_events'],
            },
            'limits': [summary['date_warning'], summary['sample_warning'], summary['identity_warning'],
                       'Tradition and denomination labels are source-reported. Current church identities, official websites, speakers and original sermon URLs have not been independently verified for this roster.',
                       'County/state is the available location precision. No coordinates or street addresses are inferred.'],
        },
        'orthodox': {
            'id': 'holy_trinity_sf', 'name': raw_orthodox['church'], 'city': raw_orthodox['city'],
            'state': raw_orthodox['state'], 'source_url': raw_orthodox['source'], 'checked_on': '2026-11-06',
            'records': orthodox_rows, 'annual': annual, 'monthly': monthly, 'speaker_comparison': comparison,
            'cutoff': CUTOFF, 'earlier_october_count': 8,
            'screen_update': {
                'coverage': ['97 visible archive entries: 47 in 2022 and 50 in 2025. Literal dates cover 39/52 and 47/52 calendar Sundays; eight earlier October observations are included within these totals.'],
                'limits': ['Archive dates and filename dates are separate evidence; neither independently verifies delivery. Audio links were observed, not played or downloaded. No transcripts were acquired.', 'Named-speaker groups mix months and item types. Current directory name matches do not establish a historical role or a comparable same-speaker panel.'],
                'speaker_evidence': 'Item-level names are preserved. Aris and Nicholas Metrakos are linked through a current official directory; unknown names and the role-only “His Eminence” attribution remain distinct.',
            },
            'access': 'Audio link destinations were observed on the archive page. No recordings were requested, played or downloaded; no transcripts were acquired.',
            'date_basis': 'Dates are literal archive labels, not verified delivery or upload dates. Filename dates remain separate and do not correct displayed dates.',
            'directory_caveat': 'The current official directory supports Aris and Nicholas Metrakos name/parish associations, not their identity or role on every historical date. Role-only labels remain unresolved.',
            'limits': coverage['interpretive_limits'] + [
                'The eight earlier October observations are included in these 97 archive entries; do not add them.',
                'The November 30, 2022 cutoff is descriptive. It establishes neither AI use nor non-use.',
            ],
        },
        'studies': records,
        'overlap': {
            'baseline_identities': 86, 'external_entities': 150,
            'candidate_count': crosswalk['exact_name_state_candidates'], 'accepted_matches': crosswalk['accepted_entity_matches'],
            'actual_overlap': crosswalk['actual_total_overlap'], 'method': crosswalk['method'],
            'conclusion': crosswalk['conclusion'], 'candidate': {
                'id': collision['external_candidate_id'], 'name': collision['external_name'],
                'historical_locality': collision['external_locality'], 'baseline_locality': collision['baseline_locality'],
                'decision': collision['disposition'], 'source_urls': collision['sources'],
            },
        },
        'attribution': [
            {'name': 'Paul Lendway (2026), Yale Dataverse V2', 'url': roster['source'], 'note': 'Tally file 42422, version 2.0. CC0 covers only rights the depositor can waive; no third-party sermon rights are granted by this catalogue.'},
            {'name': 'Holy Trinity Greek Orthodox Church, San Francisco', 'url': raw_orthodox['source'], 'note': 'Archive metadata checked 6 November 2026. Original summaries and factual metadata only; no recording license claimed.'},
            {'name': 'Greek Orthodox Metropolis of San Francisco directory', 'url': 'https://sanfran.goarch.org/parishes/holy-trinity-greek-orthodox-church-san-francisco', 'note': 'Current parish association does not establish each historical event speaker.'},
        ],
    }
    return data

def write_outputs(data):
    (ROOT/'data/extensions.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    write_csv(ROOT/'data/published-study-churches.csv',
        ['ID','Church as listed','County','State','Source-reported tradition','Source-reported denomination','Source-recorded dates','Date rows','Dates before 2022-11-30','County label as supplied','Dataset source','Tally source','Current identity status','Speaker','Official website'],
        [[r['id'],r['name'],r['county'],r['state'],r['tradition'],r['denomination'],' | '.join(r['dates']),r['event_count'],r['before_cutoff_count'],r['county_source_label'],r['source_url'],r['file_url'],r['current_identity_status'],r['speaker'],r['official_url']] for r in data['roster']['records']])
    write_csv(ROOT/'data/published-study-events.csv',
        ['ID','Church ID','Source-recorded date','Date label as supplied','Original sermon URL','Individual speaker','Tally source'],
        [[r['id'],r['church_id'],r['date'],r['date_label'],r['sermon_url'],r['speaker'],data['roster']['file_url']] for r in data['roster']['events']])
    write_csv(ROOT/'data/holy-trinity-archive.csv',
        ['ID','Year','Displayed date','Displayed date label','Title','Speaker as stated','Directory-linked name','Speaker evidence','Additional attribution','Item type','Filename date-like prefix','Filename','Verified delivery date','Upload date','Duration','Archive URL','Observed audio URL','Directory URL','Notes','Access limit'],
        [[r['id'],r['year'],r['date'],r['date_label'],r['title'],r['speaker_as_stated'],r['speaker_directory_name'],r['speaker_evidence'],(' — '.join(str(r['additional_attribution'].get(k,'')) for k in ('text','role') if r['additional_attribution'].get(k)) if isinstance(r['additional_attribution'],dict) else (r['additional_attribution'] or '')),r['type'],r['filename_date'],r['filename'],r['delivery_date'],r['upload_date'],r['duration'],r['source_url'],r['media_url'],r['directory_url'],' | '.join(r['notes']),data['orthodox']['access']] for r in data['orthodox']['records']])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_directory', type=Path)
    args = parser.parse_args()
    result = project(args.input_directory)
    write_outputs(result)
    print('Projected 150 historical entities, 450 date rows, 97 archive observations and six study notes; metadata only.')
