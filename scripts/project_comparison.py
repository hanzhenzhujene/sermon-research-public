#!/usr/bin/env python3
"""Project comparison metadata through explicit field allowlists; never fetch sources.

Usage: python3 scripts/project_comparison.py INPUT_DIRECTORY
The input is a locally reviewed metadata package. Its root and Seattle manifests
must both verify, and all four previously published JSON files must stay unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path

from project_extensions import write_csv

ROOT = Path(__file__).resolve().parents[1]
BASELINE_HASHES = {
    'catalogue.json': '73c4e721c85560aa9dadf2c6d38002c8a686885dc14732f84f2e2609cd000dcc',
    'feasibility.json': '9ed1bc0fc1c8b9fa57baeb93209bbf7311a591fd0f643f2c88cc56c312edf56c',
    'extensions.json': 'cec9cab1945ba4dcced84e40c58c8b1e14b86fe0998ddfc5d6ee53aa41968977',
    'catholic.json': 'ab0407aa59eb6aada318afc833cbe0c802f2d66ad769976f1a99960fff860e4f',
}
DETAIL_MAP = {
    'fourth-chicago-il': ('feasibility', 'fourth-chicago-il'),
    'st-marks-mystic-thomas': ('feasibility', 'stmark-mystic-ct'),
    'memorial-sudbury-vandermeulen': ('feasibility', 'memorial-sudbury-ma'),
    'st-james-seattle': ('feasibility', 'supplemental-stjames-seattle'),
    'catholic-irvine-tony': ('catholic', 'catholic-irvine-tony'),
    'catholic-ave-maria-florida-vidal': ('catholic', 'catholic-ave-maria-florida-vidal'),
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify_baselines():
    for name, digest in BASELINE_HASHES.items():
        assert hashlib.sha256((ROOT / 'data' / name).read_bytes()).hexdigest() == digest, name


def verify_package(source):
    for directory, expected in [(source, 15), (source / 'seattle', 8)]:
        manifest = read(directory / 'manifest.json')
        assert len(manifest['files']) == expected
        assert len({item['name'] for item in manifest['files']}) == expected
        for item in manifest['files']:
            path = directory / item['name']
            assert path.resolve().is_relative_to(directory.resolve()), 'Manifest path escapes input'
            raw = path.read_bytes()
            assert len(raw) == item['bytes'], item['name']
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['name']


# Correct only known joined-word errors in selected prose, never source URLs/IDs.
SPACING = {
    'andtwo': 'and two', 'suggestMay': 'suggest May', 'event-indexURLs': 'event-index URLs',
    'recordings.2025': 'recordings. 2025', 'writingURLs': 'writing URLs',
    'Sundays.2022': 'Sundays. 2022', 'calendarSundays': 'calendar Sundays',
    'Noaudio': 'No audio', 'ortranscribed': 'or transcribed',
    'historicalentities': 'historical entities', 'earliersourcescreens': 'earlier source screens',
    'itemrecords': 'item records', 'June15': 'June 15', 'October19': 'October 19',
    'May25,2025': 'May 25, 2025', 'its8am': 'its 8 a.m.', 'at10am': 'at 10 a.m.',
    '2025 10am recording': '2025 10 a.m. recording',
    'atnoon': 'at noon', 'frozen12': 'frozen 12', 'the86/150': 'the 86/150',
    'across38': 'across 38', 'rechecked2026': 'rechecked 2026', 'page2026': 'page 2026',
}


def clean(value):
    if isinstance(value, str):
        if value.startswith('https://'):
            return value
        for old, new in SPACING.items():
            value = value.replace(old, new)
    return value


def fields(names):
    return {key: None for key in names.split()}


def select(record, schema):
    """Only named fields pass; nested objects require their own explicit schema.

    None allows a scalar or a list of scalars, never an arbitrary nested object.
    A one-element schema list allows a list of explicitly projected objects.
    Absent optional fields stay absent; existing nulls stay null.
    """
    out = {}
    for key, shape in schema.items():
        if key not in record:
            continue
        value = record[key]
        if value is None:
            out[key] = None
        elif isinstance(shape, dict):
            assert isinstance(value, dict), key
            out[key] = select(value, shape)
        elif isinstance(shape, list):
            assert isinstance(value, list), key
            out[key] = [select(row, shape[0]) for row in value]
        elif isinstance(value, list):
            assert not any(isinstance(x, (dict, list)) for x in value), key
            out[key] = [clean(x) for x in value]
        else:
            assert not isinstance(value, dict), 'Missing nested allowlist: ' + key
            out[key] = clean(value)
    return out


EXAMPLE = fields('recorded_date publication_date date_basis url speaker')
DECISION = fields('id name place tradition route named_authors institution_link annual_scope next_step rights priority urls') | {
    'before_example': EXAMPLE, 'after_example': EXAMPLE,
    'audit_sources': fields('annual_index_urls bulletin_examples evidence_note'),
}
DECISION_COUNTS = fields('written_sources_meeting_this_limited_threshold separate_orthodox_recording_source combined_usable_church_total') | {
    'written_source_traditions': fields('mainline_protestant roman_catholic'),
}
RECORDING = fields('id name place tradition url count_scope speaker_candidates next_step rights')
PROFILE_COUNTS = fields('event_urls event_urls_2022 event_urls_2025 written_2025_link_positions written_2025_unique_urls written_2025_non_homily_exclusions written_2025_homily_candidates written_2025_candidate_sundays selected_2022_body_observations selected_2025_body_observations full_texts_hosted combined_distinct_body_target_urls known_wrong_date_content_targets written_2025_candidates_after_known_quarantine written_2025_candidate_sundays_after_known_quarantine')
PROFILE = fields('checked_on source_id risks selected_event_page_reads_scope') | {
    'church': fields('name city county state country tradition official_url diocesan_url historical_roster_overlap'),
    'author_timeline': [fields('name role start end date_precision source_url corroborating_body_url current_directory_url')],
    'routes': [fields('kind url target_years_enumerated format')],
    'counts': PROFILE_COUNTS,
    'selected_event_page_reads': [fields('url date_label')],
    'rights': fields('metadata_release_scope sermon_open_grant bulk_acquisition attribution_required'),
}
YEAR_COUNTS = fields('event_index_urls calendar_sundays sundays_with_any_event_label sundays_with_single_day_event_label sundays_with_homily_candidate_links written_index_unobserved_sundays sundays_with_candidate_after_known_quarantine')
MONTH = fields('month calendar_sundays event_index_sundays written_candidate_sundays written_candidate_urls quarantined_candidate_urls ryan_candidate_urls gary_candidate_urls')
SUNDAY = fields('date event_index_urls event_index_basis written_homily_candidate_urls written_status named_authors selected_indexed_bodies_observed quarantined_written_urls candidate_links_after_known_quarantine')
CALENDAR = {
    'counts': {'2022': YEAR_COUNTS, '2025': YEAR_COUNTS},
    'monthly_2025': [MONTH], 'sundays': [SUNDAY], 'limits': None,
}
EVENT = fields('id source_id source_url title index_date_label index_dates date_basis archive_url evidence_level recording_playability_verified homilist_verified transcript_availability')
OBSERVATION = fields('source_url body_observed title body_date_label normalized_body_label_date delivery_date named_author byline_observed format date_conflict mixed_speaker additional_voice segmentation_needed research_summary video_link_observed video_played transcript_verified printed_role venue_labels index_author_conflict index_date duplicate_content_candidate_url independent_sermon_count_allowed rechecked_on video_start_cue_as_displayed video_link_observation_basis') | {
    'linked_media_metadata': fields('url title_as_observed date_in_title scope'),
}
WRITING = fields('id source_id source_url title index_date index_date_label kind named_author author_basis index_sections index_observations archive_urls cross_author_index_conflict body_observed sunday full_text_retained quarantined_index_date independent_event_use')
MEDIA = fields('date service official_event_url visible_notice_summary manuscript_watch_source caution')
PRESIDER = fields('source_url date service presider homilist source_basis') | {
    'additional_service_homilist': fields('service homilist source_url basis'),
}
READING = fields('label reference')
ORIGINAL_FOURTH = fields('date_as_indexed speaker_as_indexed service_slots_as_indexed link_text_as_indexed visible_manuscript_title returned_document_title visible_event_header visible_event_date_iso visible_speaker visible_service_slot inspection_status discrepancy_note')
CONFIDENCE = fields('event_metadata assignment_of_linked_manuscript_to_indexed_event linked_event_time_and_speaker whether_same_manuscript_was_also_delivered_at_10am july24_event_metadata manuscript_header_error_hypothesis defect_is_confined_to_inspected_document_title additional_bulletin_event_corroboration')
ADDENDUM = fields('event_date service_slots speaker sermon_title source_url source_locator basis limit') | {'readings': [READING]}
CONFLICT = fields('church_id text_link_url source_archive_url bulletin_url bulletin_event_date bulletin_service_slots bulletin_speaker bulletin_occasion bulletin_title classification finding recommendation unknowns id readings_scope') | {
    'original_values_unchanged': ORIGINAL_FOURTH, 'bulletin_readings': [READING],
    'confidence': CONFIDENCE, 'additional_bulletin_observation': ADDENDUM,
}
TARGET = fields('church_id event_date_as_indexed speaker_as_indexed text_link_url source_archive_url original_inspection_status_unchanged original_service_slots_as_indexed original_manuscript_visible_service_slot original_visible_manuscript_title event_enrichment_status bulletin_url bulletin_date bulletin_service_slots bulletin_speaker bulletin_occasion bulletin_sermon_title confidence service_assignment_note remaining_unknowns id readings_scope link_warning occasion_detail title_variation_note') | {
    'bulletin_scripture_readings': [READING],
}
FOURTH = {
    'counts': fields('existing_2022_conflicts existing_2025_targets 2025_dated_bulletin_enrichments 2025_without_new_bulletin_enrichment shared_two_service_bulletins new_churches new_acquired_texts'),
    'limits': None, 'conflicts_2022': [CONFLICT], 'targets_2025': [TARGET],
    'additional_readings_evidence': [fields('source_url date basis') | {'additional_observation': READING}],
}


def project_observation(raw):
    row = select(raw, OBSERVATION)
    # The absence of an observation is not a negative observation.
    row['video_link_observed'] = raw.get('video_link_observed')
    if 'Earlier bounded audit observed' in row.get('research_summary', ''):
        row['research_summary'] = 'Inspected prose has the indexed date and a named author byline. No recording was played and no full text was retained.'
    return row


def project(source):
    verify_baselines()
    verify_package(source)
    raw_decisions = read(source / 'decisions/source-decision-ledger.json')
    decisions = select(raw_decisions, fields('question count_definition limits') | {'counts': DECISION_COUNTS})
    decisions['items'] = []
    for raw in raw_decisions['items']:
        row = select(raw, DECISION)
        row['detail_view'], row['detail_id'] = DETAIL_MAP[row['id']]
        decisions['items'].append(row)
    recording = select(raw_decisions['separate_recording_route'], RECORDING)
    recording['count_scope'] = '97 visible target-year audio-link metadata records: 47 in 2022 and 50 in 2025. They cover 39 of 52 calendar Sundays in 2022 and 47 of 52 in 2025. No audio was played, downloaded or transcribed.'
    recording.update(detail_view='feasibility', detail_id='holy_trinity_sf')
    decisions['separate_recording_route'] = recording

    profile = select(read(source / 'seattle/source-profile.json'), PROFILE)
    profile['risks'].append('This annual view deepens the existing Seattle supplemental source. It adds no church to the 86 identities, 150 historical entities or 12 source screens.')
    profile['risks'].append('Twelve distinct target URLs have inspected body metadata: eleven 2025 index targets and one separate 2022 date-conflicted target. The June 15 URL is a wrong-date/duplicate-content candidate, so this is not twelve independent homilies.')
    raw_obs = read(source / 'seattle/selected-body-observations.json')
    profile['rights']['interpretation'] = clean(raw_obs['rights']['interpretation'])
    profile['rights']['open_reuse_grant_found'] = raw_obs['rights']['open_reuse_grant_found']
    observations = [project_observation(row) for row in raw_obs['observations']]
    by_url = {row['source_url']: row for row in observations}
    assert len(by_url) == len(observations)
    writings = []
    for raw in read(source / 'seattle/written-index.json')['items']:
        row = select(raw, WRITING)
        row['body_observation'] = by_url.get(row['source_url']) if row['body_observed'] else None
        assert (row['body_observation'] is not None) == row['body_observed']
        writings.append(row)
    calendar = select(read(source / 'seattle/calendar.json'), CALENDAR)
    calendar['limits'].extend([
        'The 46 raw homily-candidate URLs include six non-Sunday entries and 40 Sunday URLs on 39 Sundays. After the June 15 quarantine, 39 Sunday URLs cover 38 Sundays; all 45 remaining URLs are still candidates.',
        'Monthly URL totals include the six non-Sunday homily candidates. Multiple URLs on one Sunday do not increase Sunday coverage.',
        '48 unique writing URLs comprise 46 homily candidates and two other writings. Index-only records have no inspected body observation.',
    ])
    seattle = {
        'profile': profile, 'calendar': calendar,
        'screen_update': {
            'coverage': [
                '130 event-index URLs: 70 in 2022 and 60 in 2025, with labels covering all 52 Sundays in each year. Labels do not verify playable recordings or individual homilists.',
                '2025: 48 writing URLs, including 46 homily candidates across 39 Sundays; 45 candidates across 38 Sundays remain after the June 15 quarantine. Six candidates are non-Sunday; Sunday URLs fall from 40 to 39. Annual 2022 written coverage is unknown.',
            ],
            'speaker_evidence': 'Michael G. Ryan became pastor emeritus on July 1, 2025; Gary F. Lazzeroni succeeded him as pastor. Ryan continued occasional preaching. Written authorship, service presider and service homilist are separate evidence; October 19 lists Lazzeroni as 10 a.m. presider and Ryan as homilist.',
            'next_action': 'Resolve the 2022 written inventory, then match author, service type and season. Preserve the July 1 role change, mixed voices, date conflicts and service-specific video limits before any text comparison.',
        },
        'events': [select(row, EVENT) for row in read(source / 'seattle/event-index.json')['items']],
        'writings': writings, 'observations': observations,
        'unsuccessful_requests': [{
            'attempted_url': raw_obs['unsuccessful_requests'][0]['attempted_url'],
            'discovery_basis': 'Hypothesized URL; not an observed archive link',
            'outcome': 'No readable content or site HTTP status was established. This does not establish absence of a sermon.',
            'evidence_of_absence': False,
            'scope': 'One documented annual-extension request; not a combined total of earlier attempts.',
        }],
        'media_caveats': [select(row, MEDIA) for row in raw_obs['media_caveats']],
        'presider_homilist_caveat': select(raw_obs['presider_homilist_caveat'], PRESIDER),
    }
    seattle['presider_homilist_caveat']['source_basis'] = 'Official event-page metadata identifies the presider and homilist separately.'
    seattle['presider_homilist_caveat']['additional_service_homilist']['basis'] = 'Official event-page metadata observed November 6, 2026. Ryan is not assigned to every service.'

    fourth = select(read(source / 'fourth/fourth-event-provenance.json'), FOURTH)
    fourth['earlier_service_time_note'] = 'The earlier manuscript-header checks did not confirm 2025 service times. Later dated bulletins provide advertised service-slot evidence for 11 of 13 targets; actual delivery and the manuscript’s service instance remain unverified.'
    baseline_rows = read(ROOT / 'data/feasibility.json')['fourth']['target_checks']
    baseline = {row['item_url']: row for row in baseline_rows}
    assert len(baseline) == len(baseline_rows)
    for row in fourth['conflicts_2022'] + fourth['targets_2025']:
        row['baseline_target_id'] = baseline[row['text_link_url']]['id']
    for row in fourth['conflicts_2022']:
        row['unknowns'] = [value.replace('in the returned excerpt', 'in the inspected metadata').replace('in this pass', 'in the inspected metadata') for value in row['unknowns']]
        row['original_values_unchanged']['discrepancy_note'] = row['original_values_unchanged']['discrepancy_note'].replace('manifest and official index', 'official index').replace('Manifest and official index', 'Official index')
        row['original_values_unchanged']['discrepancy_note'] = row['original_values_unchanged']['discrepancy_note'].replace('Official index label July 24', 'The official index labels July 24')
        row['recommendation'] = row['recommendation'].replace('without changing accepted data or increasing counts', 'without changing the original discrepancy classification or increasing counts')
        if 'additional_bulletin_observation' in row:
            row['bulletin_observation_period'] = 'Earlier observation: bulletin event fields were not obtained. These null fields record that earlier observation.'
            row['unknowns'][0] = 'Earlier observation: the linked bulletin event fields were not obtained. The later bulletin observation below now corroborates the event.'
            row['additional_bulletin_observation']['observation_period'] = 'Later observation: dated bulletin metadata observed November 6, 2026.'
            row['additional_bulletin_observation']['basis'] = 'Later bulletin metadata corroborates the event fields unavailable in the earlier observation.'
    for row in fourth['targets_2025']:
        row['remaining_unknowns'] = [value.replace('not verified in this bounded pass', 'not verified in the inspected metadata') for value in row['remaining_unknowns']]
        if row['event_enrichment_status'] == 'not_read_within_budget':
            row['event_enrichment_status'] = 'bulletin_not_observed'
        if 'link_warning' in row:
            row['link_warning'] = 'The 2025 index uses the same bulletin link for September 14 and September 21. Its destination was not inspected, so the bulletin URL and September 14 event metadata remain unknown.'
    for row in fourth['additional_readings_evidence']:
        row['basis'] = 'Additional published reading metadata observed November 6, 2026; the original manuscript observation is unchanged.'
    counts = {
        'written_sources': len(decisions['items']),
        'primary_written_sources': sum(row['priority'] == 'primary_written_comparison' for row in decisions['items']),
        'priority_gap_sources': sum(row['priority'] == 'priority_gap_resolution' for row in decisions['items']),
        'supplementary_written_sources': sum(row['priority'] == 'supplementary_written_source' for row in decisions['items']),
        'separate_recording_sources': 1, 'seattle_event_urls': len(seattle['events']),
        'seattle_writing_urls': len(writings), 'seattle_raw_homily_candidates': 46,
        'seattle_candidates_after_quarantine': 45, 'seattle_sunday_urls_raw': 40,
        'seattle_sunday_urls_after_quarantine': 39, 'seattle_candidate_sundays_raw': 39,
        'seattle_candidate_sundays_after_quarantine': 38, 'seattle_non_sunday_candidates': 6,
        'seattle_calendar_rows': len(calendar['sundays']), 'seattle_body_target_observations': len(observations),
        'fourth_joined_targets': len(fourth['conflicts_2022']) + len(fourth['targets_2025']),
        'new_churches': 0, 'full_texts_hosted': 0,
    }
    verify_baselines()
    return {'checked_on': raw_decisions['checked_on'], 'counts': counts, 'decisions': decisions, 'seattle': seattle, 'fourth': fourth}


def cell(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return str(value)


def csv_tables(data):
    """Summary exports with exact JSON pointers to the complete public caveats."""
    tables = {}
    decision_rows = []
    for i, row in enumerate(data['decisions']['items']):
        decision_rows.append([
            row['id'], row['name'], row['place'], row['tradition'], row['priority'], row['route'],
            row['named_authors'], row['institution_link'], row['before_example'], row['after_example'],
            row['annual_scope'], row['next_step'], row['rights'], row['urls'], row['detail_view'], row['detail_id'],
            'data/comparison.json#/decisions/items/' + str(i),
        ])
    row = data['decisions']['separate_recording_route']
    decision_rows.append([row['id'], row['name'], row['place'], row['tradition'], 'separate_recording_route',
                          'Recording metadata only', row['speaker_candidates'], '', None, None, row['count_scope'],
                          row['next_step'], row['rights'], [row['url']], row['detail_view'], row['detail_id'],
                          'data/comparison.json#/decisions/separate_recording_route'])
    tables['comparison-sources.csv'] = (
        ['ID', 'Source', 'Place', 'Tradition', 'Selection group', 'Route', 'Named authors or speaker candidates', 'Institution or role evidence', 'Before example metadata', 'After example metadata', 'Observed scope', 'Next step', 'Rights limits', 'Sources', 'Detail view', 'Detail ID', 'Full public JSON detail'], decision_rows)
    tables['seattle-events.csv'] = (
        ['ID', 'Title', 'Indexed dates', 'Date label', 'Date basis', 'Evidence level', 'Recording playability verified', 'Homilist verified', 'Transcript availability', 'Source URL', 'Archive URL', 'Full public JSON detail'],
        [[r['id'], r['title'], r['index_dates'], r['index_date_label'], r['date_basis'], r['evidence_level'], r['recording_playability_verified'], r['homilist_verified'], r['transcript_availability'], r['source_url'], r['archive_url'], 'data/comparison.json#/seattle/events/' + str(i)] for i, r in enumerate(data['seattle']['events'])])
    tables['seattle-written.csv'] = (
        ['ID', 'Index date', 'Title', 'Kind', 'Named author', 'Author basis', 'Index sections', 'Sunday', 'Body inspected', 'Quarantined indexed date', 'Author index conflict', 'Inspected body date', 'Verified delivery date', 'Observed video link (blank unknown)', 'Date conflict', 'Researcher summary', 'Source URL', 'Archive URLs', 'Full public JSON detail'],
        [[r['id'], r['index_date'], r['title'], r['kind'], r['named_author'], r['author_basis'], r['index_sections'], r['sunday'], r['body_observed'], r['quarantined_index_date'], r['cross_author_index_conflict'], (r['body_observation'] or {}).get('normalized_body_label_date'), (r['body_observation'] or {}).get('delivery_date'), (r['body_observation'] or {}).get('video_link_observed'), (r['body_observation'] or {}).get('date_conflict'), (r['body_observation'] or {}).get('research_summary'), r['source_url'], r['archive_urls'], 'data/comparison.json#/seattle/writings/' + str(i)] for i, r in enumerate(data['seattle']['writings'])])
    tables['seattle-sundays.csv'] = (
        ['Date', 'Event URLs', 'Event date basis', 'Raw homily candidate URLs', 'Written status', 'Named authors', 'Selected indexed bodies observed (blank unknown)', 'Quarantined URLs', 'Candidate URLs after quarantine', 'Full public JSON detail'],
        [[r['date'], r['event_index_urls'], r['event_index_basis'], r['written_homily_candidate_urls'], r['written_status'], r['named_authors'], r['selected_indexed_bodies_observed'], r['quarantined_written_urls'], r['candidate_links_after_known_quarantine'], 'data/comparison.json#/seattle/calendar/sundays/' + str(i)] for i, r in enumerate(data['seattle']['calendar']['sundays'])])
    fourth_rows = []
    for group in ['conflicts_2022', 'targets_2025']:
        for i, r in enumerate(data['fourth'][group]):
            old = r.get('original_values_unchanged', {})
            later = r.get('additional_bulletin_observation', {})
            fourth_rows.append([
                r['id'], r['baseline_target_id'], r.get('event_date_as_indexed', old.get('date_as_indexed')),
                r.get('speaker_as_indexed', old.get('speaker_as_indexed')),
                r.get('original_service_slots_as_indexed', old.get('service_slots_as_indexed')),
                r.get('original_visible_manuscript_title', old.get('visible_manuscript_title')),
                old.get('returned_document_title'), r.get('original_inspection_status_unchanged', old.get('inspection_status')),
                r.get('event_enrichment_status', r.get('classification')),
                r.get('bulletin_observation_period', 'Published bulletin observation'),
                r.get('bulletin_date', r.get('bulletin_event_date')), r['bulletin_service_slots'], r['bulletin_speaker'],
                r['bulletin_occasion'], r.get('bulletin_sermon_title', r.get('bulletin_title')),
                r.get('bulletin_scripture_readings', r.get('bulletin_readings')),
                r.get('occasion_detail'), r.get('title_variation_note'), r.get('service_assignment_note'),
                r.get('link_warning'), r.get('finding'), r.get('remaining_unknowns', r.get('unknowns')),
                later.get('observation_period'), later.get('event_date'), later.get('service_slots'), later.get('speaker'),
                later.get('sermon_title'), later.get('readings'), later.get('source_url'), later.get('limit'),
                r['text_link_url'], r['bulletin_url'], 'data/comparison.json#/fourth/' + group + '/' + str(i),
            ])
    tables['fourth-event-evidence.csv'] = (
        ['Package ID', 'Existing target ID', 'Indexed date', 'Indexed speaker', 'Indexed service', 'Original manuscript title', 'Original document title', 'Original inspection status', 'Evidence status or conflict classification', 'Bulletin observation period', 'Bulletin date', 'Bulletin services', 'Bulletin speaker', 'Bulletin occasion', 'Bulletin sermon title', 'Published readings', 'Service-specific occasion caveat', 'Title variation caveat', 'Service assignment caveat', 'Link caveat', 'Conflict finding', 'Remaining unknowns', 'Later observation period', 'Later bulletin date', 'Later bulletin services', 'Later bulletin speaker', 'Later bulletin title', 'Later published readings', 'Later bulletin URL', 'Later observation limit', 'Manuscript URL', 'Bulletin URL', 'Full public JSON detail'], fourth_rows)
    return {name: (headers, [[cell(v) for v in row] for row in rows]) for name, (headers, rows) in tables.items()}


def write_outputs(data):
    verify_baselines()
    (ROOT / 'data/comparison.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, (headers, rows) in csv_tables(data).items():
        write_csv(ROOT / 'data' / name, headers, rows)
    verify_baselines()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_directory', type=Path)
    args = parser.parse_args()
    write_outputs(project(args.input_directory))
    print('Projected six written source decisions, one separate recording route, Seattle annual metadata and 17 exact Fourth target joins. Both manifests and four baseline hashes verified.')
