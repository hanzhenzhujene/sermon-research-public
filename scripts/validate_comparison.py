#!/usr/bin/env python3
"""Validate public comparison metadata, exact joins, uncertainty and safe exports.

Usage: python3 scripts/validate_comparison.py [INPUT_DIRECTORY]
The optional locally supplied package enables both-manifest and deterministic
projection checks. No source site, media or network access is performed.
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
from collections import Counter
from pathlib import Path

import project_comparison as projection
from project_extensions import safe_cell
from validate_extensions import safety, sunday_dates

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / 'data' / name).read_text(encoding='utf-8-sig'))


def public_safety(value, path='root'):
    safety(value, path)
    if isinstance(value, dict):
        blocked = {'evidence_locator', 'observation_provenance', 'source_reconciliation',
                   'review_scope', 'independent_review', 'raw_tool_output', 'reader_lines',
                   'reader_link', 'private_notes', 'workflow_notes', 'body_text', 'caption_text'}
        assert not blocked.intersection(value), 'Nonpublic field: ' + path
        for key, child in value.items():
            public_safety(child, path + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            public_safety(child, path + '[' + str(i) + ']')
    elif isinstance(value, str):
        assert '<' not in value and '>' not in value, 'HTML-like content: ' + path
        assert not re.search(r'\breader\s+(?:id|link|line)s?\b|\bturn\d+(?:search|view|fetch)\d+\b', value, re.I), 'Reader locator: ' + path
        assert not re.search(r'\b(?:within_budget|not_read_within_budget)\b', value), 'Workflow status: ' + path
        assert not any(old in value for old in projection.SPACING if not value.startswith('https://')), 'Uncorrected spacing: ' + path


def schema_check(data):
    """Reject even innocuous-looking unreviewed keys, not just known secret names."""
    p = projection
    observation = p.OBSERVATION
    profile = p.PROFILE | {'rights': p.PROFILE['rights'] | p.fields('interpretation open_reuse_grant_found')}
    conflict = p.CONFLICT | p.fields('baseline_target_id bulletin_observation_period') | {
        'additional_bulletin_observation': p.ADDENDUM | p.fields('observation_period'),
    }
    schema = {
        'checked_on': None,
        'counts': p.fields('written_sources primary_written_sources priority_gap_sources supplementary_written_sources separate_recording_sources seattle_event_urls seattle_writing_urls seattle_raw_homily_candidates seattle_candidates_after_quarantine seattle_sunday_urls_raw seattle_sunday_urls_after_quarantine seattle_candidate_sundays_raw seattle_candidate_sundays_after_quarantine seattle_non_sunday_candidates seattle_calendar_rows seattle_body_target_observations fourth_joined_targets new_churches full_texts_hosted'),
        'decisions': p.fields('question count_definition limits') | {
            'counts': p.DECISION_COUNTS,
            'items': [p.DECISION | p.fields('detail_view detail_id')],
            'separate_recording_route': p.RECORDING | p.fields('detail_view detail_id'),
        },
        'seattle': {
            'profile': profile, 'calendar': p.CALENDAR, 'events': [p.EVENT],
            'screen_update': p.fields('coverage speaker_evidence next_action'),
            'writings': [p.WRITING | {'body_observation': observation}],
            'observations': [observation],
            'unsuccessful_requests': [p.fields('attempted_url discovery_basis outcome evidence_of_absence scope')],
            'media_caveats': [p.MEDIA], 'presider_homilist_caveat': p.PRESIDER,
        },
        'fourth': p.FOURTH | {
            'earlier_service_time_note': None,
            'conflicts_2022': [conflict],
            'targets_2025': [p.TARGET | p.fields('baseline_target_id')],
        },
    }
    assert p.select(data, schema) == data, 'Unexpected public field or unnormalized display text'
    assert set(data) == {'checked_on', 'counts', 'decisions', 'seattle', 'fourth'}


def validate_decisions(data):
    decisions = data['decisions']
    items = decisions['items']
    assert len(items) == len({r['id'] for r in items}) == 6
    assert {r['id'] for r in items} == set(projection.DETAIL_MAP)
    assert Counter(r['priority'] for r in items) == {
        'primary_written_comparison': 2, 'priority_gap_resolution': 1, 'supplementary_written_source': 3,
    }
    assert decisions['counts'] == {
        'written_sources_meeting_this_limited_threshold': 6,
        'written_source_traditions': {'mainline_protestant': 3, 'roman_catholic': 3},
        'separate_orthodox_recording_source': 1, 'combined_usable_church_total': None,
    }
    assert 'before November 30' in decisions['count_definition']
    assert '2022' in decisions['count_definition'] and '2025' in decisions['count_definition']
    assert 'source-feasibility threshold' in decisions['count_definition']
    f = read('feasibility.json')
    existing = {'feasibility': {r['id'] for r in f['screens'] + f['supplemental']},
                'catholic': {r['id'] for r in read('catholic.json')['sources']}}
    for row in items:
        assert (row['detail_view'], row['detail_id']) == projection.DETAIL_MAP[row['id']]
        assert row['detail_id'] in existing[row['detail_view']]
        before, after = row['before_example'], row['after_example']
        assert '2022-01-01' <= before['recorded_date'] < '2022-11-30'
        assert '2025-01-01' <= after['recorded_date'] <= '2025-12-31'
        for example in [before, after]:
            dt.date.fromisoformat(example['recorded_date'])
            assert example['speaker'] in row['named_authors'] and example['url'].startswith('https://')
        assert row['institution_link'] and row['rights'] and row['next_step']
    by_id = {r['id']: r for r in items}
    assert by_id['memorial-sudbury-vandermeulen']['before_example']['publication_date'] == '2022-05-30'
    assert by_id['memorial-sudbury-vandermeulen']['after_example']['publication_date'] == '2025-07-15'
    assert 'occasional preacher' in by_id['memorial-sudbury-vandermeulen']['institution_link']
    assert 'deacon' in by_id['catholic-irvine-tony']['institution_link']
    assert 'February 17, 2025' in by_id['catholic-irvine-tony']['institution_link']
    assert 'no date in the inspected body' in by_id['catholic-irvine-tony']['before_example']['date_basis']
    assert 'conflict' in by_id['st-james-seattle']['before_example']['date_basis'].lower()
    assert 'May 1' in by_id['st-james-seattle']['before_example']['date_basis']
    separate = decisions['separate_recording_route']
    assert separate['id'] == separate['detail_id'] == 'holy_trinity_sf'
    assert separate['detail_view'] == 'feasibility' and separate['id'] not in by_id
    assert separate['id'] in existing['feasibility']
    assert '39 of 52 calendar Sundays in 2022 and 47 of 52 in 2025' in separate['count_scope']
    orthodox = read('extensions.json')['orthodox']['annual']
    assert [(r['year'], r['entries'], r['sundays_observed'], r['sundays_total']) for r in orthodox] == [(2022, 47, 39, 52), (2025, 50, 47, 52)]
    limits = ' '.join(decisions['limits'])
    for phrase in ['licensed', 'national sample', '86', '150', '12', '47', 'AI adoption', 'surviving text version']:
        assert phrase in limits, 'Missing decision limit: ' + phrase


def validate_seattle(data):
    seattle = data['seattle']
    events, writings, observations = seattle['events'], seattle['writings'], seattle['observations']
    calendar = seattle['calendar']
    assert len(events) == len({r['source_url'] for r in events}) == len({r['id'] for r in events}) == 130
    assert Counter(r['index_dates'][0][:4] for r in events) == {'2022': 70, '2025': 60}
    assert all(r['evidence_level'] == 'event_index_link' and r['recording_playability_verified'] is False and r['homilist_verified'] is False and r['transcript_availability'] is None for r in events)
    assert len(writings) == len({r['source_url'] for r in writings}) == len({r['id'] for r in writings}) == 48
    assert Counter(r['kind'] for r in writings) == {'homily_candidate': 46, 'other_writing': 2}
    assert sum(r['index_observations'] for r in writings) == 57
    candidates = [r for r in writings if r['kind'] == 'homily_candidate']
    after = [r for r in candidates if not r['quarantined_index_date']]
    sunday = [r for r in candidates if r['sunday']]
    sunday_after = [r for r in after if r['sunday']]
    assert (len(candidates), len(after), len(sunday), len(sunday_after)) == (46, 45, 40, 39)
    assert (len({r['index_date'] for r in sunday}), len({r['index_date'] for r in sunday_after})) == (39, 38)
    assert len([r for r in candidates if not r['sunday']]) == 6
    assert all(r['sunday'] == (dt.date.fromisoformat(r['index_date']).weekday() == 6) for r in writings)
    assert all(r['full_text_retained'] is False for r in writings)
    obs_by_url = {r['source_url']: r for r in observations}
    assert len(observations) == len(obs_by_url) == 12
    assert sum(r['body_observed'] for r in writings) == 11
    assert all(r['body_observed'] is True and r['delivery_date'] is None and r['video_played'] is False and r['transcript_verified'] is False for r in observations)
    for row in writings:
        assert row['body_observation'] == (obs_by_url.get(row['source_url']) if row['body_observed'] else None)
        assert row['author_basis'] == ('inspected_body_byline' if row['body_observed'] else 'named_index_section_only')
    prefix = 'https://www.stjames-cathedral.org/Pubs/Pastor/'
    june = next(r for r in writings if r['source_url'] == prefix + '2025/25june15.aspx')
    assert june['quarantined_index_date'] and june['index_date'] == '2025-06-15'
    june_body = june['body_observation']
    assert june_body['normalized_body_label_date'] == '2025-10-19'
    assert june_body['duplicate_content_candidate_url'] == prefix + '2025/25oct19.aspx'
    assert june_body['independent_sermon_count_allowed'] is False and june_body['date_conflict']
    august = next(r for r in writings if r['source_url'] == prefix + '2025/25aug10.aspx')
    assert august['named_author'] == 'Gary F. Lazzeroni' and august['cross_author_index_conflict']
    assert august['body_observation']['index_author_conflict']
    assert august['body_observation']['video_link_observed'] is None, 'Omitted video flag became false'
    assert len(august['body_observation']['venue_labels']) == 2
    early = obs_by_url[prefix + '2022/22may1.aspx']
    assert early['normalized_body_label_date'] == '2022-05-02' and early['delivery_date'] is None
    assert early['mixed_speaker'] and early['additional_voice'] == 'Sarah Riggio'
    assert early['segmentation_needed'] and early['date_conflict']
    assert early['linked_media_metadata']['date_in_title'] == '2022-05-01'
    assert prefix + '2022/22may1.aspx' not in {r['source_url'] for r in writings}
    profile = seattle['profile']
    update = seattle['screen_update']
    assert len(update['coverage']) == 2
    for phrase in ['130', '70 in 2022', '60 in 2025', '52 Sundays']:
        assert phrase in update['coverage'][0]
    for phrase in ['48 writing URLs', '46 homily candidates', '39 Sundays', '45 candidates', '38 Sundays', 'Six candidates are non-Sunday', '40 to 39', '2022 written coverage is unknown']:
        assert phrase in update['coverage'][1]
    assert all(phrase in update['speaker_evidence'] for phrase in ['July 1, 2025', 'emeritus', 'Gary F. Lazzeroni', 'presider', 'homilist'])
    assert all(phrase in update['next_action'] for phrase in ['2022 written inventory', 'author', 'service type', 'season'])
    timeline = {(r['name'], r['role']): r for r in profile['author_timeline']}
    assert timeline[('Michael G. Ryan', 'Pastor')]['end'] == '2025-06-30'
    assert timeline[('Michael G. Ryan', 'Pastor Emeritus')]['start'] == '2025-07-01'
    assert timeline[('Gary F. Lazzeroni', 'Pastor')]['start'] == '2025-07-01'
    assert obs_by_url[prefix + '2025/25aug31-mgr.aspx']['printed_role'] == 'Pastor Emeritus'
    assert 'not twelve independent homilies' in ' '.join(profile['risks'])
    assert profile['rights']['open_reuse_grant_found'] is False
    caveat = seattle['presider_homilist_caveat']
    assert (caveat['date'], caveat['service'], caveat['presider'], caveat['homilist']) == ('2025-10-19', '10:00am', 'Gary F. Lazzeroni', 'Michael G. Ryan')
    assert caveat['additional_service_homilist']['service'] == '12 noon'
    assert caveat['additional_service_homilist']['homilist'] == 'Deacon Scott Aikin'
    media = seattle['media_caveats']
    assert len(media) == 1 and media[0]['date'] == '2025-05-25' and media[0]['service'] == '10:00am Mass'
    assert 'partial' in media[0]['visible_notice_summary']
    assert '8:00am' in media[0]['manuscript_watch_source'] and '28:40' in media[0]['manuscript_watch_source']
    assert '10:00am' in media[0]['caution'] and '8:00am' in media[0]['caution']
    assert all(r['evidence_of_absence'] is False for r in seattle['unsuccessful_requests'])

    sundays = calendar['sundays']
    assert len(sundays) == len({r['date'] for r in sundays}) == 104
    for year in [2022, 2025]:
        rows = [r for r in sundays if r['date'].startswith(str(year))]
        expected_dates = sunday_dates(year)
        assert {r['date'] for r in rows} == expected_dates and len(rows) == 52
        counts = calendar['counts'][str(year)]
        assert counts['calendar_sundays'] == counts['sundays_with_any_event_label'] == 52
        assert counts['event_index_urls'] == (70 if year == 2022 else 60)
        assert counts['sundays_with_single_day_event_label'] == (51 if year == 2022 else 52)
        if year == 2022:
            assert all(counts[key] is None for key in ['sundays_with_homily_candidate_links', 'written_index_unobserved_sundays', 'sundays_with_candidate_after_known_quarantine'])
            assert all(r['selected_indexed_bodies_observed'] is None and r['written_status'] == 'not_enumerated' and r['written_homily_candidate_urls'] == [] for r in rows)
        else:
            assert counts['sundays_with_homily_candidate_links'] == 39 and counts['sundays_with_candidate_after_known_quarantine'] == 38
            assert set(counts['written_index_unobserved_sundays']) == expected_dates - {r['index_date'] for r in sunday}
        for row in rows:
            indexed_events = [r for r in events if row['date'] in r['index_dates']]
            assert set(row['event_index_urls']) == {r['source_url'] for r in indexed_events}
            assert set(row['event_index_basis']) == {r['date_basis'] for r in indexed_events}
            indexed = [r for r in candidates if r['index_date'] == row['date']]
            assert set(row['written_homily_candidate_urls']) == {r['source_url'] for r in indexed}
            assert set(row['candidate_links_after_known_quarantine']) == {r['source_url'] for r in indexed if not r['quarantined_index_date']}
            assert set(row['quarantined_written_urls']) == {r['source_url'] for r in indexed if r['quarantined_index_date']}
            assert set(row['named_authors']) == {r['named_author'] for r in indexed}
            if year == 2025:
                assert row['selected_indexed_bodies_observed'] == sum(r['body_observed'] for r in indexed)
    monthly = calendar['monthly_2025']
    assert len(monthly) == 12 and {r['month'] for r in monthly} == {f'2025-{n:02}' for n in range(1, 13)}
    for month in monthly:
        rows = [r for r in candidates if r['index_date'].startswith(month['month'])]
        expected_sundays = sunday_dates(2025, int(month['month'][-2:]))
        assert month['calendar_sundays'] == month['event_index_sundays'] == len(expected_sundays)
        assert month['written_candidate_urls'] == len(rows)
        assert month['written_candidate_sundays'] == len({r['index_date'] for r in rows if r['sunday']})
        assert month['quarantined_candidate_urls'] == sum(r['quarantined_index_date'] for r in rows)
        assert month['ryan_candidate_urls'] == sum(r['named_author'] == 'Michael G. Ryan' for r in rows)
        assert month['gary_candidate_urls'] == sum(r['named_author'] == 'Gary F. Lazzeroni' for r in rows)
    assert sum(r['written_candidate_urls'] for r in monthly) == 46
    assert sum(r['written_candidate_sundays'] for r in monthly) == 39
    assert sum(r['quarantined_candidate_urls'] for r in monthly) == 1
    expected_profile = {
        'event_urls': 130, 'event_urls_2022': 70, 'event_urls_2025': 60, 'written_2025_link_positions': 57,
        'written_2025_unique_urls': 48, 'written_2025_non_homily_exclusions': 2, 'written_2025_homily_candidates': 46,
        'written_2025_candidate_sundays': 39, 'selected_2022_body_observations': 1, 'selected_2025_body_observations': 11,
        'full_texts_hosted': 0, 'combined_distinct_body_target_urls': 12, 'known_wrong_date_content_targets': 1,
        'written_2025_candidates_after_known_quarantine': 45, 'written_2025_candidate_sundays_after_known_quarantine': 38,
    }
    assert profile['counts'] == expected_profile


def validate_fourth(data):
    fourth = data['fourth']
    assert fourth['earlier_service_time_note'] == 'The earlier manuscript-header checks did not confirm 2025 service times. Later dated bulletins provide advertised service-slot evidence for 11 of 13 targets; actual delivery and the manuscript’s service instance remain unverified.'
    old, targets = fourth['conflicts_2022'], fourth['targets_2025']
    baseline = read('feasibility.json')['fourth']
    assert baseline['counts'] == {'annual_records': 107, 'targets': 33, 'body_renderings': 32, 'no_inspected_conflict': 28, 'discrepancies': 4, 'unavailable': 1, 'full_texts_retained': 0}
    assert len(old) == 4 and len(targets) == 13
    all_rows = old + targets
    assert len({r['id'] for r in all_rows}) == len({r['baseline_target_id'] for r in all_rows}) == len({r['text_link_url'] for r in all_rows}) == 17
    by_url = {r['item_url']: r for r in baseline['target_checks']}
    for row in all_rows:
        original = by_url[row['text_link_url']]
        assert original['id'] == row['baseline_target_id']
        assert original['source_url'] == row['source_archive_url']
    assert {r['text_link_url'] for r in old} == {r['item_url'] for r in baseline['target_checks'] if r['status'] == 'discrepancy'}
    assert {r['text_link_url'] for r in targets} == {r['item_url'] for r in baseline['target_checks'] if r['year'] == 2025}
    for row in old:
        original, saved = by_url[row['text_link_url']], row['original_values_unchanged']
        assert original['status'] == 'discrepancy' and saved['inspection_status'] == 'source_discrepancy'
        for new_key, old_key in {
            'date_as_indexed': 'date', 'speaker_as_indexed': 'speaker', 'service_slots_as_indexed': 'index_service_time',
            'visible_manuscript_title': 'detail_title', 'returned_document_title': 'detail_document_title',
            'visible_event_date_iso': 'detail_date', 'visible_speaker': 'detail_speaker', 'visible_service_slot': 'detail_service_time',
        }.items():
            assert saved[new_key] == original[old_key], 'Original Fourth conflict changed: ' + new_key
    expected_classifications = {
        '2022-06-19': 'event_identity_supported_but_linked_manuscript_identity_conflicts',
        '2022-07-10': 'linked_4pm_materials_conflict_with_10am_index_slot',
        '2022-07-24': 'july24_event_supported_manuscript_header_date_still_conflicted',
        '2022-09-25': 'document_title_metadata_defect_without_demonstrated_event_mismatch',
    }
    assert {r['original_values_unchanged']['date_as_indexed']: r['classification'] for r in old} == expected_classifications
    for row in targets:
        original = by_url[row['text_link_url']]
        assert original['status'] == 'no_conflict' and row['original_inspection_status_unchanged'] == 'pass_match'
        assert (row['event_date_as_indexed'], row['speaker_as_indexed'], row['original_service_slots_as_indexed'], row['original_manuscript_visible_service_slot'], row['original_visible_manuscript_title']) == (original['date'], original['speaker'], original['index_service_time'], original['detail_service_time'], original['detail_title'])
    assert sum(r['event_enrichment_status'] == 'corroborated_dated_bulletin' for r in targets) == 11
    assert sum(r['bulletin_service_slots'] == ['9:30 a.m.', '11:00 a.m.'] for r in targets) == 6
    targets_by_date = {r['event_date_as_indexed']: r for r in targets}
    may = targets_by_date['2025-05-11']
    assert may['original_service_slots_as_indexed'] == '9:30 a.m.'
    assert 'Confirmation' in may['occasion_detail'] and '11:00 only' in may['occasion_detail'] and '9:30' in may['occasion_detail']
    january = targets_by_date['2025-01-05']
    assert january['original_visible_manuscript_title'] == 'Epiphanies and Revelations'
    assert january['bulletin_sermon_title'] == 'Epiphanies and Ongoing Revelations'
    assert january['title_variation_note']
    for date in ['2025-09-14', '2025-08-10']:
        row = targets_by_date[date]
        assert all(row[key] is None for key in ['bulletin_url', 'bulletin_date', 'bulletin_speaker', 'bulletin_occasion', 'bulletin_sermon_title'])
        assert row['bulletin_service_slots'] == row['bulletin_scripture_readings'] == []
    assert 'September 21' in targets_by_date['2025-09-14']['link_warning']
    september = next(r for r in old if r['original_values_unchanged']['date_as_indexed'] == '2022-09-25')
    assert all(september[key] is None for key in ['bulletin_event_date', 'bulletin_speaker', 'bulletin_occasion', 'bulletin_title'])
    assert september['bulletin_service_slots'] == september['bulletin_readings'] == []
    assert september['confidence']['additional_bulletin_event_corroboration'] == 'not_obtained'
    assert september['bulletin_observation_period'].startswith('Earlier observation:')
    assert september['unknowns'][0].startswith('Earlier observation:')
    later = september['additional_bulletin_observation']
    assert later['observation_period'].startswith('Later observation:')
    assert (later['event_date'], later['service_slots'], later['speaker'], later['sermon_title']) == ('2022-09-25', ['4:00 p.m.'], 'Nanette Sawyer', 'Listen to the Prophets')
    assert 'January 1, 2017' in september['original_values_unchanged']['returned_document_title']
    assert 'not exact delivery' in later['limit']
    assert len(fourth['additional_readings_evidence']) == 6
    bulletin_rows = {r['bulletin_url']: r for r in all_rows if r['bulletin_url']}
    for reading in fourth['additional_readings_evidence']:
        row = bulletin_rows[reading['source_url']]
        assert reading['additional_observation'] in row.get('bulletin_readings', row.get('bulletin_scripture_readings'))
    assert fourth['counts'] == {'existing_2022_conflicts': 4, 'existing_2025_targets': 13, '2025_dated_bulletin_enrichments': 11, '2025_without_new_bulletin_enrichment': 2, 'shared_two_service_bulletins': 6, 'new_churches': 0, 'new_acquired_texts': 0}
    assert 'service plan' in ' '.join(fourth['limits']) and 'duplicate manuscript' in ' '.join(fourth['limits'])


def validate_exports(data):
    expected_sizes = {'comparison-sources.csv': 7, 'seattle-events.csv': 130, 'seattle-written.csv': 48, 'seattle-sundays.csv': 104, 'fourth-event-evidence.csv': 17}
    for name, (headers, expected) in projection.csv_tables(data).items():
        with (ROOT / 'data' / name).open(encoding='utf-8-sig', newline='') as stream:
            actual = list(csv.reader(stream))
        assert actual[0] == headers and len(actual) - 1 == expected_sizes[name]
        assert actual[1:] == [[safe_cell(v) for v in row] for row in expected], 'CSV/JSON parity: ' + name
        assert all(len(row) == len(headers) for row in actual)
        for row in actual[1:]:
            for value in row:
                assert not value.lstrip().startswith(('=', '+', '-', '@')), 'Formula cell: ' + name
            pointer = row[-1]
            assert pointer.startswith('data/comparison.json#/')
            target = data
            for part in pointer.split('#/', 1)[1].split('/'):
                target = target[int(part)] if isinstance(target, list) else target[part]
            assert isinstance(target, dict), 'Broken detail pointer: ' + name
    # Exercise CSV escaping with adversarial spreadsheet payloads and quoting.
    for value in ['=1+1', '+SUM(A1:A2)', '-1+2', '@SUM(1)', ' \t=CMD()', '\n+1', '\r@x']:
        assert safe_cell(value).startswith("'")
    payload = ['a,b', 'a"b', 'a\nb', '=1+1', None]
    buf = io.StringIO(newline='')
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow([safe_cell(v) for v in payload])
    assert next(csv.reader(io.StringIO(buf.getvalue(), newline=''))) == ['a,b', 'a"b', 'a\nb', "'=1+1", '']
    for value in [{'reader_id': 'private'}, {'evidence_locator': 'private'}, '<script>alert(1)</script>', '<img src=x onerror=alert(1)>', 'javascript:alert(1)', 'file:///Users/example', 'reader lines 1–2', '/Users/private']:
        try:
            public_safety(value)
        except AssertionError:
            continue
        raise AssertionError('Safety test accepted: ' + repr(value))
    assert projection.select({'title': 'Allowed', 'raw_body': 'Do not publish', 'unreviewed': {'x': 1}}, projection.fields('title')) == {'title': 'Allowed'}


def main(source=None):
    projection.verify_baselines()
    data = read('comparison.json')
    schema_check(data)
    public_safety(data)
    assert data['checked_on'] == '2026-11-06'
    assert data['counts'] == {
        'written_sources': 6, 'primary_written_sources': 2, 'priority_gap_sources': 1,
        'supplementary_written_sources': 3, 'separate_recording_sources': 1,
        'seattle_event_urls': 130, 'seattle_writing_urls': 48, 'seattle_raw_homily_candidates': 46,
        'seattle_candidates_after_quarantine': 45, 'seattle_sunday_urls_raw': 40,
        'seattle_sunday_urls_after_quarantine': 39, 'seattle_candidate_sundays_raw': 39,
        'seattle_candidate_sundays_after_quarantine': 38, 'seattle_non_sunday_candidates': 6,
        'seattle_calendar_rows': 104, 'seattle_body_target_observations': 12,
        'fourth_joined_targets': 17, 'new_churches': 0, 'full_texts_hosted': 0,
    }
    base, feasibility, extensions = read('catalogue.json'), read('feasibility.json'), read('extensions.json')
    assert (len(base['churches']), len(base['items']), len(feasibility['screens']), len(extensions['roster']['records'])) == (86, 47, 12, 150)
    validate_decisions(data)
    validate_seattle(data)
    validate_fourth(data)
    validate_exports(data)
    if source is not None:
        assert projection.project(source) == data, 'Saved JSON differs from verified allowlist projection'
        expected_json = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        assert (ROOT / 'data/comparison.json').read_text(encoding='utf-8') == expected_json
        print('Both input manifests verified; saved JSON is the deterministic allowlist projection.')
    projection.verify_baselines()
    print('Comparison validation passed: four baseline hashes; 2/1/3 decisions plus separate Orthodox; Seattle 130/48/46/45 URLs, 40/39 Sunday URLs across 39/38 Sundays, 104 calendar rows, 12 inspected targets; 17 exact Fourth joins and temporal caveats; five CSV parity checks; formula/HTML/public-field rejection tests.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_directory', nargs='?', type=Path)
    args = parser.parse_args()
    main(args.input_directory)
