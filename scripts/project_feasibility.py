#!/usr/bin/env python3
"""Project reviewed inputs into public metadata. No network requests or text bodies.

Usage: python3 scripts/project_feasibility.py INPUT_DIRECTORY [--output FILE]
The reviewed input package is supplied separately; this script never fetches it.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

CHECKED = '2026-11-06'
CATEGORY = {
    'priority_text': 'Priority text candidate',
    'supplemental_text': 'Supplemental text route',
    'platform_export': 'SermonAudio export not yet validated',
    'recording_candidate': 'Recording candidate',
    'deferred_panel': 'Deferred for a continuous panel',
    'supplemental_lead': 'Supplemental lead',
}
STATUS = {'no_conflict': 'No inspected conflict', 'discrepancy': 'Source discrepancy', 'unavailable': 'Unavailable in latest check', 'index_only': 'Index only', 'readable': 'Page readable in latest check'}
ROUTES = {
    'platform_transcript': 'SermonAudio transcript',
    'church_linked_author_manuscript': 'Church-linked author manuscript',
    'official_church_manuscript_and_media': 'Church manuscripts and media',
    'mixed_archive_unverified_text': 'Mixed archive; text unverified',
    'sparse_homily_links': 'Sparse homily links',
    'pdf_manuscript_links': 'PDF manuscript links',
    'audio_archive_links': 'Church audio archive',
    'church_manuscript_and_recordings': 'Church manuscripts and recordings',
    'author_blog': 'Church-linked author blog',
    'individual_html_manuscript': 'Individual HTML manuscript',
}


SOURCE_LABELS = {
    'heritage-profile': 'Broadcaster profile', 'heritage-archive': 'Sermon archive',
    'heritage-pre': 'January 26, 2022 example', 'heritage-post': 'June 21, 2026 example',
    'sa-transcripts': 'SermonAudio transcript documentation', 'sa-api': 'SermonAudio API information',
    'woodruff-affiliation': 'Church affiliation statement', 'woodruff-profile': 'Broadcaster profile',
    'woodruff-archive': 'Sermon archive', 'woodruff-pre': 'January 9, 2022 example',
    'woodruff-post': 'August 16, 2026 example', 'trinity-profile': 'Broadcaster profile',
    'trinity-romans': 'Romans series', 'trinity-romans-older': 'Older series page — latest check unavailable',
    'trinity-pre': 'August 7, 2022 example', 'trinity-post': 'October 11, 2026 example',
    'stmark-official': 'Church sermon page and author link', 'thomas-index': 'Author sermon index',
    'thomas-license': 'Page with author license notice', 'thomas-date-conflict': 'May 2022 date discrepancy',
    'memorial-team': 'Church ministry-team biography', 'memorial-denomination': 'Church affiliation statement',
    'allen-pre': 'May 29, 2022 manuscript', 'allen-post': 'October 26, 2025 manuscript',
    'allen-index': 'Author publication index', 'fourth-archive': 'Church sermon archive',
    'fourth-2022': '2022 annual archive', 'fourth-2025': '2025 annual archive',
    'fourth-faq': 'Church affiliation information', 'haller-screen': 'Church sermon archive',
    'stlouis-screen': 'Church homily archive', 'bt-staff': 'Official pastoral staff',
    'bt-archive': 'Parish page linking the 2022 homily', 'cc-welcome': 'Parish and diocese information',
    'cc-staff': 'Official pastoral staff', 'cc-index': 'Sunday homily archive',
}


def load(root, name):
    return json.loads((root / name).read_text(encoding='utf-8-sig'))


def csv_rows(root, name):
    with (root / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def link(label, url):
    assert url and urlsplit(url).scheme in {'https', 'http'}
    return {'label': label, 'url': url}


def record_id(prefix, *parts):
    return prefix + '-' + hashlib.sha256('|'.join(str(x) for x in parts).encode()).hexdigest()[:12]


def title_key(value):
    return re.sub(r'[^\w]+', '', value.casefold())


def project_fourth(root):
    annual = load(root, 'delivery/fourth-annual-cadence.json')
    panel = load(root, 'delivery/fourth-verified-target-panel.json')
    target_checks = []
    exceptions = {
        '2022-06-19': 'The index names Joseph L. Morrow on June 19. The target instead shows Matt Helms on June 26. Do not reassign the target to the indexed event.',
        '2022-06-26': 'The exact linked target was unavailable; the inspection reported 404. Its title, speaker and date have not been confirmed on the target.',
        '2022-07-10': 'The date and speaker agree, but the index gives 10:00 a.m. and the target header gives 4:00 p.m. The service time remains unresolved.',
        '2022-07-24': 'The index and document title give July 24; the visible manuscript header gives July 31. The speaker agrees, but the event date remains unresolved.',
        '2022-09-25': 'The visible header, speaker and time agree with the 2022 index. The document title gives January 1, 2017. This is a document-title conflict, not a demonstrated header-date mismatch.',
    }
    for r in panel['records']:
        status = {'pass_match': 'no_conflict', 'source_discrepancy': 'discrepancy', 'inaccessible': 'unavailable'}[r['inspection_status']]
        target_checks.append({
            'id': record_id('fourth-check', r['text_link_url']),
            'year': r['year'], 'date': r['date_as_indexed'],
            'title': r['link_text_as_indexed'], 'speaker': r['speaker_as_indexed'],
            'index_service_time': r['service_slots_as_indexed'],
            'source_url': r['source_archive_url'], 'item_url': r['text_link_url'],
            'status': status, 'status_label': STATUS[status],
            'body_visible': r['manuscript_paragraphs_visible_beyond_title_navigation'],
            'detail_title': r['visible_manuscript_title'], 'detail_speaker': r['visible_speaker'],
            'detail_date': r['visible_event_date_iso'],
            'detail_service_time': r['visible_service_slot'],
            'confirmed_service_time': r['visible_service_slot'] if r['year'] == 2022 and status == 'no_conflict' else None,
            'detail_document_title': r.get('returned_document_title'),
            'exception': exceptions.get(r['date_as_indexed']) if status != 'no_conflict' else None,
            'checked_on': CHECKED,
        })
    by_url = {r['item_url']: r for r in target_checks}
    records = []
    for r in annual['items']:
        target = by_url.get(r.get('text_link_url'))
        kind = {'sermon_or_homily_record': 'Sermon or homily entry', 'explicit_no_sermon_service': 'Explicit no-sermon service', 'youth_homilies_group_record': 'Grouped youth homilies'}[r['record_type']]
        status = target['status'] if target else 'index_only'
        records.append({
            'id': record_id('fourth-index', r['year'], r['date_as_indexed'], r.get('text_link_url'), r.get('speaker_as_indexed'), r.get('service_slots_as_indexed')),
            'year': r['year'], 'date': r['date_as_indexed'], 'title': r.get('link_text') or kind,
            'speaker': r['speaker_as_indexed'], 'source_url': r['source_url'], 'item_url': r.get('text_link_url'),
            'date_basis': 'Church archive event-date label; delivery not independently confirmed',
            'index_service_time': r['service_slots_as_indexed'],
            'confirmed_service_time': target['confirmed_service_time'] if target else None,
            'text_link': r['text_link_observed'], 'media_link': r['media_link_observed'],
            'record_kind': kind, 'status': status, 'status_label': STATUS[status],
            'check_id': target['id'] if target else None,
        })
    summaries = []
    for r in annual['summaries']:
        summaries.append({
            'year': r['year'], 'index_records': r['index_records'], 'distinct_dates': r['distinct_dates'],
            'calendar_sundays': r['calendar_sundays'], 'sunday_dates_with_record': r['sunday_dates_with_record'],
            'sunday_dates_not_observed': r['sunday_dates_not_observed'], 'explicit_no_sermon_dates': r['explicit_no_sermon_dates'],
            'text_link_records': r['text_link_records'], 'media_link_records': r['media_link_records'],
            'speaker_counts_as_written': [{'speaker': name, 'records': n} for name, n in r['speaker_counts_as_written'].items()],
            'monthly': [{k: m[k] for k in ('month', 'reference_sundays', 'sundays_with_record', 'sundays_with_text_link')} for m in r['monthly']],
        })
    speakers = []
    for r in panel['speaker_summary']:
        speakers.append({'speaker': r['speaker_as_indexed'], 'years': [
            {'year': y, 'targets': r[f'targets_{y}'], 'no_inspected_conflict': r[f'pass_match_{y}'], 'discrepancies': r[f'source_discrepancy_{y}'], 'unavailable': r[f'inaccessible_{y}']} for y in (2022, 2025)]})
    annual_speakers = [{
        'speaker': r['speaker_label'],
        'years': [{'year': y, 'index_records': r[f'records_{y}'], 'text_links': r[f'text_links_{y}']} for y in (2022, 2025)],
        'identity_limit': 'Same written name within the church archive; a separate historical personnel check was not performed.',
    } for r in annual['cross_period_speaker_labels']]
    counts = {'annual_records': len(records), 'targets': len(target_checks), 'body_renderings': sum(r['body_visible'] is True for r in target_checks), 'no_inspected_conflict': sum(r['status'] == 'no_conflict' for r in target_checks), 'discrepancies': sum(r['status'] == 'discrepancy' for r in target_checks), 'unavailable': sum(r['status'] == 'unavailable' for r in target_checks), 'full_texts_retained': 0}
    assert counts == {'annual_records': 107, 'targets': 33, 'body_renderings': 32, 'no_inspected_conflict': 28, 'discrepancies': 4, 'unavailable': 1, 'full_texts_retained': 0}
    assert sum(r['check_id'] is not None for r in records) == 33
    return {
        'counts': counts, 'annual_records': sorted(records, key=lambda r: (r['date'], r['id'])),
        'target_checks': target_checks, 'speakers': speakers, 'annual_speakers': annual_speakers,
        'annual_summary': summaries,
        'calendar': [{k: r[k] for k in ('year', 'month', 'date', 'archive_records', 'sermon_or_homily_records', 'text_link_records', 'explicit_no_sermon_records')} for r in annual['calendar']],
        'limits': ['The 33 checked targets are part of the 107 annual index records; do not add them.',
                   'The annual index includes two explicit no-sermon musical services and one grouped youth-homilies entry.',
                   'No inspected conflict means no conflict was found in the inspected fields. It does not establish complete text, delivery as written or independent authentication.',
                   'Indexed service times and target-header times are different evidence. All 2025 target service times remain unconfirmed.',
                   'The four discrepancies are set aside for resolution. The unavailable target is unknown, not an absent sermon.',
                   'Manuscripts were read for metadata checks, not retained as a text corpus. Reuse permission has not been established.'],
        'source_links': [link('2022 church archive', 'https://www.fourthchurch.org/sermons/2022/index.html'), link('2025 church archive', 'https://www.fourthchurch.org/sermons/2025/index.html')],
    }


def project_thomas(root):
    annual = load(root, 'delivery/thomas-annual-cadence.json')
    passage = load(root, 'supplementary-delivery/thomas-passage-comparison.json')
    observations = []
    notes = {
        '2022-10-02': 'St Mark’s is mentioned as context; this is not an explicit event-venue declaration.',
        '2022-10-09': 'The earlier title, author and event-date observation is retained. The latest exact-page read failed, so passage and liturgical label remain unknown.',
        '2022-10-16': 'An attributed literary example does not establish that this manuscript republishes an earlier sermon.',
        '2022-10-23': 'The title says Revisited and the text refers to earlier discussion; this does not establish verbatim manuscript reuse.',
        '2022-10-30': 'The author groups this and three preceding Sundays into a prayer series. The observations are not necessarily independent.',
        '2025-10-05': 'No named delivery venue was established.',
        '2025-10-12': 'The text describes a reading response used at St Mark’s; this supports congregational context, not independent delivery verification.',
        '2025-10-19': 'The text refers to an earlier sermon and acknowledges human wording help and suggestions. Neither establishes AI use or a reused manuscript.',
        '2025-10-26': 'The text refers to Mystic and St Mark’s as its present setting. No independent event record was checked.',
    }
    for r in passage['rows']:
        status = 'readable' if r['detail_read_status'] == 'readable' else 'unavailable'
        date = r['event_date_as_stated']
        observations.append({
            'id': record_id('thomas-october', date, r['title']), 'year': int(date[:4]),
            'date': date, 'title': r['title'], 'speaker': r['author'],
            'publication_date': r['publication_date'], 'source_url': r['source_url'],
            'status': status, 'status_label': STATUS[status],
            'liturgical_label': r['liturgical_label'], 'passages': r['header_passages'] if status == 'readable' else None,
            'venue': None,
            'venue_evidence': 'Author’s church affiliation; no independently confirmed event venue',
            'notes': notes[date],
            'earlier_observation': 'Earlier page observation recorded the title, author and stated event date.',
            'additional_displayed_date': r['additional_displayed_date'],
            'additional_date_meaning': 'Displayed without an established label; not confirmed as a modification date.' if r['additional_displayed_date'] else None,
            'checked_on': CHECKED,
        })
    by_date_title = {(r['date'], title_key(r['title'])): r for r in observations}
    records = []
    for r in annual['records']:
        date = r['audit_date']
        detail = by_date_title.get((date, title_key(r['title'])))
        status = detail['status'] if detail else 'index_only'
        status_label = STATUS[status] if detail else ('Header date observed; outside October checks' if r.get('detail_date_verified') else 'Outside selected October checks')
        records.append({
            'id': record_id('thomas-index', date, r['title']), 'year': r['year'],
            'date': date, 'index_date': r['date_as_stated'], 'title': r['title'], 'speaker': 'Adam Thomas',
            'source_url': r['source_url'], 'item_url': detail['source_url'] if detail else r.get('detail_source_url'),
            'publication_date': detail['publication_date'] if detail else None,
            'date_basis': 'Earlier index and page-header observation; latest page unavailable' if detail and status == 'unavailable' else r['date_basis'],
            'status': status, 'status_label': status_label, 'check_id': detail['id'] if detail else None,
            'updated_title': r['explicit_updated_title'], 'revisited_title': r['revisited_title'],
        })
    assert len(records) == 88 and sum(r['check_id'] is not None for r in records) == 9
    pairs = []
    for r in passage['pairs']:
        pairs.append({
            'label': r['liturgical_label'], 'pre_date': r['pre_event_date'], 'post_date': r['post_event_date'],
            'pre_title': r['pre_title'], 'post_title': r['post_title'],
            'pre_url': r['pre_url'], 'post_url': r['post_url'],
            'pre_passages': r['pre_header_passages'], 'post_passages': r['post_header_passages'],
            'same_passage': r['header_passage_match'] == 'exact',
            'result': 'Same listed header passage' if r['header_passage_match'] == 'exact' else 'Different listed header passages',
        })
    summaries = [{
        'year': r['year'], 'index_records': r['total_index_items'], 'calendar_sundays': r['calendar_sundays'],
        'sunday_dates_with_record': r['sunday_dates_with_index_item'], 'non_sunday_items': r['non_sunday_items'],
        'sunday_dates_not_observed': r['sunday_dates_not_observed'],
        'monthly': [{'month': m['month'], 'reference_sundays': m['reference_sundays'], 'sundays_with_record': m['observed_sunday_dates']} for m in r['monthly']],
    } for r in annual['summaries']]
    counts = {'annual_records': len(records), 'october_observations': len(observations), 'currently_readable': sum(r['status'] == 'readable' for r in observations), 'currently_unavailable': sum(r['status'] == 'unavailable' for r in observations), 'same_label_pairs': len(pairs), 'equal_passage_pairs': sum(r['same_passage'] for r in pairs), 'different_passage_pairs': sum(not r['same_passage'] for r in pairs), 'full_texts_retained': 0}
    assert counts == {'annual_records': 88, 'october_observations': 9, 'currently_readable': 8, 'currently_unavailable': 1, 'same_label_pairs': 3, 'equal_passage_pairs': 1, 'different_passage_pairs': 2, 'full_texts_retained': 0}
    return {'counts': counts, 'annual_records': sorted(records, key=lambda r: (r['date'], r['id'])),
            'october_observations': sorted(observations, key=lambda r: r['date']), 'passage_pairs': pairs,
            'annual_summary': summaries,
            'calendar': [{'year': r['year'], 'month': r['month'], 'date': r['calendar_date'], 'index_records': r['index_items'], 'titles': r['titles']} for r in annual['calendar']],
            'limits': ['The nine October observations are included in the 88 author-index entries, not nine additional texts.',
                       'These are author manuscripts linked by St Mark’s. The author index is not a complete church-service archive.',
                       'Publication dates and stated event dates are separate. An extra unlabeled displayed date is not a verified modification date.',
                       'A matching liturgical label does not mean the same reading was selected. One of three pairs has the same header passage.',
                       'Neither passage matching, references to prior sermons nor human editing acknowledgments establish AI use.',
                       'The May 2022 index label says May 9; the inspected item header says May 8. Both values are preserved.'],
            'source_links': [link('Author sermon index', annual['source']), link('Church sermon page', 'https://www.stmarksmystic.org/sermons')]}


def project_rights(root):
    raw = load(root, 'supplementary-delivery/rights-clarification.json')
    sources = {r['id']: r['url'] for r in raw['sources']}
    return [
        {'id': 'thomas', 'name': 'Adam Thomas: CC BY-NC-ND 3.0',
         'scope': 'Author-owned material covered by the observed notice. Scripture quotations and other third-party material need separate consideration.',
         'operations': [
             {'operation': 'Unchanged noncommercial copies', 'status': 'Conditionally permitted', 'conditions': 'Confirm that the work and intended use fall within the notice. Preserve the work and provenance. The license does not require a new request for every covered copy.'},
             {'operation': 'Technical format conversion', 'status': 'Necessary technical changes permitted', 'conditions': 'Limited to technical changes necessary to exercise the licensed rights in other media or formats. Translation, rewriting or arbitrary cleaning is not automatically a format change.'},
             {'operation': 'Computational analysis or cleaning', 'status': 'Depends on the operation', 'conditions': 'Analysis is not automatically adaptation. If the operation creates an adaptation in the copyright sense, version 3.0 ND does not grant that right; another permission or applicable exception may be needed.'},
             {'operation': 'Share unchanged works or collections', 'status': 'Conditionally permitted; not done here', 'conditions': 'Meet noncommercial conditions and applicable attribution, source, license and notice requirements. Do not turn the work into an adaptation or restrict recipients’ licensed rights. Check third-party material separately.'},
         ], 'sources': [link('Observed author notice', sources['thomas-notice']), link('CC BY-NC-ND 3.0 legal terms', sources['cc3-law']), link('Differences between CC versions', sources['cc-version'])]},
        {'id': 'allen', 'name': 'Allen Vander Meulen: identified CC BY-NC 4.0 works',
         'scope': 'Only the identified works bearing this notice and content the licensor can license. The notice does not cover all church manuscripts or recordings.',
         'operations': [
             {'operation': 'Noncommercial copying and retention', 'status': 'Conditionally permitted', 'conditions': 'The noncommercial condition applies to covered private uses too. Retain source and license information and check third-party material.'},
             {'operation': 'Noncommercial adaptation and analysis', 'status': 'Conditionally permitted', 'conditions': 'The license grants noncommercial adaptation rights for covered content. Whether analysis needs to rely on a license depends on the actual operation and applicable exceptions.'},
             {'operation': 'Share covered works or adaptations', 'status': 'Conditionally permitted; not done here', 'conditions': 'Keep required attribution, copyright/license notices, disclaimers and source links; identify changes and supply the license or its link. No blanket rights over third-party material are granted.'},
         ], 'sources': [link('Identified licensed manuscript', sources['allen-notice']), link('CC BY-NC 4.0 legal terms', sources['cc4-law'])]},
        {'id': 'not_established', 'name': 'Other church, platform and media material',
         'scope': 'A readable page or visible download link does not establish a research-use grant. A missing license does not establish that every research use is prohibited.',
         'operations': [
             {'operation': 'Retain or process text', 'status': 'Basis not established in these checks', 'conditions': 'Assess existing authorization, applicable exceptions, site terms and the particular method and output. Research or university affiliation is not an automatic exemption.'},
             {'operation': 'Download media, transcribe, export at scale or send to outside models', 'status': 'Separate assessment required', 'conditions': 'Text-page readability and an author’s text license do not establish media rights, platform access or permission for every external service.'},
             {'operation': 'Publish full texts or media', 'status': 'Not included in this website', 'conditions': 'The public catalogue contains metadata and summaries only. Rights to publish the original works must be assessed separately.'},
         ], 'sources': [link('Creative Commons questions about mining and noncommercial use', sources['cc-faq']), link('U.S. Copyright Office: fair use', sources['fair-use'])]},
    ]


def project_screens(root):
    source_rows = load(root, 'delivery/original-source-manifest.json')['sources']
    urls = {r['source_id']: r['exact_url'] for r in source_rows}
    config = {
        'heritage-lawrence-ks': ('platform_export', 'Scott Hanks is named on the broadcaster profile and the two inspected sermon examples; the archive also contains other speakers.',
            ['Transcript displays were previously observed for January 26, 2022 and June 21, 2026.', 'September and October 2026 each show records on all four Sundays. October 2022 and 2025 coverage is not established.'],
            ['The earlier item is midweek and the later item is Sunday evening; they are not matched event types.', 'Transcript export, provenance and reuse rights still need validation.'],
            'Validate the broadcaster’s permitted transcript export route and the requested 2022/2025 date windows before collecting text.', ['heritage-profile','heritage-archive','heritage-pre','heritage-post','sa-transcripts','sa-api'], 'not_established'),
        'woodruff-simpsonville-sc': ('platform_export', 'Carl Robbins is named on the broadcaster profile and the inspected examples. Guest speakers also appear in recent archives.',
            ['Inspected examples date to January 9, 2022 and August 16, 2026.', 'One Samuel series lists all five August 2021 Sundays. October 2022 and 2025 coverage is not established.'],
            ['One series does not establish complete church coverage. The example service types differ.', 'Transcript export and reuse rights have not been validated.'],
            'Validate permitted transcript export and archive pagination, then check the same date windows and event types.', ['woodruff-affiliation','woodruff-profile','woodruff-archive','woodruff-pre','woodruff-post','sa-api'], 'not_established'),
        'trinity-montville-nj': ('platform_export', 'David Chanski is named on the profile, inspected examples and the Romans-series observations.',
            ['Earlier observations found Romans-series entries on all four August 2022 and all five August 2025 Sundays.', 'The older series page was unavailable on recheck. October 2025 has one observed series date, October 19; the October 2022 window remains unknown.'],
            ['The series is not an inventory of all church sermons.', 'Earlier metadata remains evidence, but the older page was not reproduced in the latest check.'],
            'Resolve the permitted historical archive/export route before relying on a same-speaker panel.', ['trinity-profile','trinity-romans','trinity-romans-older','trinity-pre','trinity-post','sa-api'], 'not_established'),
        'stmark-mystic-ct': ('priority_text', 'St Mark’s identifies Adam Thomas as rector and links his author archive. Manuscript authorship does not independently establish each event’s venue.',
            ['The author index contains 43 entries for 2022 and 45 for 2025.', 'Nine October observations cover five 2022 Sunday dates and four 2025 dates. Eight exact pages were readable in the latest check; one failed after an earlier successful observation.'],
            ['Author archive, not a complete record of services at St Mark’s.', 'Three same-liturgical-label pairs include only one pair with equal header passages. No AI-use evidence follows.'],
            'Use the dated author metadata to define the intended analysis, then apply the CC BY-NC-ND 3.0 conditions to the specific copying and processing operations.', ['stmark-official','thomas-index','thomas-license','thomas-date-conflict'], 'thomas'),
        'memorial-sudbury-ma': ('supplemental_text', 'The church identifies Allen Vander Meulen as a streaming worship producer who preaches occasionally. The two manuscripts name their author and claim delivery at Memorial.',
            ['Manuscript labels state delivery on May 29, 2022 and October 26, 2025.', 'These are two occasional-preacher examples, not an established weekly series.'],
            ['The stated delivery labels were not independently checked against recordings.', 'The identified CC BY-NC 4.0 notice does not cover every church publication or recording.'],
            'Treat the specifically licensed 2022 work and the separate 2025 manuscript individually; establish each item’s applicable rights and do not infer weekly coverage.', ['memorial-team','memorial-denomination','allen-pre','allen-post','allen-index'], 'allen'),
        'fourth-chicago-il': ('priority_text', 'The church archive names multiple speakers. Four same-written-name groups form the selected target checks: Joseph L. Morrow, Matt Helms, Nanette Sawyer and Rocky Supinger.',
            ['107 annual index records: 55 for 2022 and 52 for 2025.', '33 selected targets are included in those 107: 32 rendered manuscript bodies, 28 without an inspected conflict, four discrepancies and one unavailable page.'],
            ['No inspected conflict does not establish complete delivery or text reuse rights.', 'All 2025 target service times remain unconfirmed. The annual index also contains two explicit no-sermon services and a grouped youth entry.'],
            'Resolve the four source discrepancies and intended-use rights; retain separate indexed and target-header values before choosing a dated text panel.', ['fourth-archive','fourth-2022','fourth-2025','fourth-faq'], 'not_established'),
        'hallerlake-seattle-wa': ('deferred_panel', 'No supported item-level speaker identity was established in this screen.',
            ['The page labels several historical 2022 entries as manuscripts and has current dated media links.', 'The inspected historical links were represented by one repeated Facebook destination; individual text targets remain unverified.'],
            ['A manuscript label is not evidence that the linked body is available.', 'No continuous 2022/2025 text window or reuse grant was established.'],
            'Establish the actual historical destinations and text availability through a permitted route before selecting items.', ['haller-screen'], 'not_established'),
        'stlouis-memphis-tn': ('deferred_panel', 'No supported item-level speaker identity was established in this screen.',
            ['The inspected homily page exposes sparse links from 2023–2025.', 'A pre-2023 window was not established.'],
            ['Sparse inspected links do not prove that no other homilies exist.', 'No continuous pre/post series or reuse grant was established.'],
            'Locate a permitted historical archive and identify speakers and dates before selecting a continuous panel.', ['stlouis-screen'], 'not_established'),
        'blessedtrinity-missoula-mt': ('deferred_panel', 'Official staff names Fr. Ed Hislop as pastor; the three previously observed PDF headers name him. The community and its mission share an archive.',
            ['Three earlier PDF observations state October 2, 2022, October 12, 2025 and October 26, 2025.', 'On later checks both 2025 PDFs returned 404 and the 2022 PDF was inaccessible.'],
            ['Preserve the earlier observations, but do not call the files currently accessible.', 'Shared community/mission headers do not resolve delivery venue. One archive must not become two corpora.'],
            'Resolve current access through an authorized route and establish reuse terms; retain the historical evidence and venue uncertainty.', [], 'not_established'),
        'cocathedral-honolulu-hi': ('deferred_panel', 'Official staff identifies Reverend Manuel Hewe as pastor; one inspected signed homily names Fr. Manny Hewe. Some index links use Fr. Manny.',
            ['The October 2025 index has four dated PDF links; two tested targets returned 403.', 'No October 2022 date was found in the inspected index. A separate November 6, 2022 example was readable.'],
            ['Four links are not four readable texts. The unobserved 2022 window remains unknown.', 'A different link labeled under 2022 opens a PDF explicitly titled 2023; source-year labels require checking.'],
            'Resolve access and wrong-year links through an authorized route before treating this as a continuous dated manuscript source.', [], 'not_established'),
        'holy_trinity_sf': ('recording_candidate', 'The 2022 October entries explicitly name a speaker on one of four items; all four 2025 items name Fr. Aris or Fr. Nicholas. Directory matches identify Aris and Nicholas Metrakos.',
            ['Audio links occur on four of five October 2022 Sundays and all four October 2025 Sundays.', 'No transcripts were observed. The archive has multiple speakers despite its page title.'],
            ['Recordings were not downloaded or played, so recording completeness and sermon-only boundaries remain unknown.', 'An unlisted Sunday is not evidence that no sermon was delivered; media and transcription rights remain unestablished.'],
            'Establish recording and transcription permissions, then verify speaker identity, dates and recording boundaries before transcription.', [], 'not_established'),
        'saint_katherine_chandler': ('deferred_panel', 'Historical entries name Father Timothy, Father Philip Armstrong and Metropolitan Gerasimos. A current directory match for Timothy Pavlatos does not confirm the full historical tenure.',
            ['The legacy archive lists homilies on all five October 2022 Sundays.', 'The 2025 window was not reached: the legacy navigation returned 401. Linked audio access was also restricted.'],
            ['2025 coverage is unknown, not zero. Earlier indexed metadata is not a currently verified recording.', 'The archive includes other clergy and an anniversary guest; it is not a single-author series.'],
            'Resolve authorized archive access and the 2025 window before selecting a two-period panel.', [], 'not_established'),
    }
    catholic = load(root, 'delivery/catholic-source-screen.json')
    catholic_sources = {r['source_id']: r['url'] for r in catholic['sources']}
    orthodox = csv_rows(root, 'delivery/orthodox-item-metadata.csv')
    screens = []
    for r in load(root, 'delivery/candidate-overview.json')['churches']:
        cat, speaker, coverage, limits, next_action, source_ids, rights_id = config[r['candidate_id']]
        source_links = [link('Official source', r['official_source'])]
        for sid in source_ids:
            url = urls[sid]
            if url not in [s['url'] for s in source_links]:source_links.append(link(SOURCE_LABELS[sid], url))
        screen = {'id': r['candidate_id'], 'name': r['name'], 'city': r['city'], 'state': r['state'],
                  'tradition': r['affiliation_as_stated'], 'category': cat, 'category_label': CATEGORY[cat],
                  'route': r['route_type'], 'route_label': ROUTES[r['route_type']], 'speaker_evidence': speaker,
                  'coverage': coverage, 'limits': limits, 'next_action': next_action, 'source_links': source_links,
                  'rights_id': rights_id, 'case_study': 'fourth' if r['candidate_id']=='fourth-chicago-il' else 'thomas' if r['candidate_id']=='stmark-mystic-ct' else None, 'directory_id': r.get('directory86_id'), 'checked_on': CHECKED, 'observations': []}
        if r['candidate_id'] in ('blessedtrinity-missoula-mt', 'cocathedral-honolulu-hi'):
            ids = ['bt-staff', 'bt-archive'] if r['candidate_id'].startswith('blessed') else ['cc-welcome', 'cc-staff', 'cc-index']
            screen['source_links'] += [link(SOURCE_LABELS[sid], catholic_sources[sid]) for sid in ids]
            for item in catholic['items']:
                if item['candidate_id'] != r['candidate_id']:continue
                sid = item['source_id'];current = 'Earlier text observation; latest check unavailable' if sid == 'bt-pre' else 'Earlier text observation; latest check reported 404' if sid in ('bt-post12','bt-post26') else 'Access denied (403)' if sid in ('cc-denied05','cc-denied26') else 'Link observed; target not inspected' if sid == 'cc-index' else 'Text observed; not retained'
                screen['observations'].append({'date': item['date'], 'title': 'Homily', 'speaker': item['speaker'], 'date_basis': item['date_basis'], 'source_url': catholic_sources[sid], 'status_label': current, 'format': item['artifact'], 'note': 'Delivery venue not independently confirmed.'})
        if r['candidate_id'] in ('holy_trinity_sf','saint_katherine_chandler'):
            for item in orthodox:
                if item['church_id'] != r['candidate_id']:continue
                screen['observations'].append({'date': item['display_date'], 'title': item['title'], 'speaker': item['speaker_as_stated'] or None,
                    'date_basis': 'Church archive event-date label; not an independently confirmed delivery or upload date',
                    'source_url': item['archive_url'], 'status_label': 'Audio link observed; recording not inspected' if r['candidate_id']=='holy_trinity_sf' else 'Earlier archive observation; current access restricted',
                    'format': 'Audio link', 'note': 'No transcript observed. A page-level or clergy-directory name is not an item-level speaker assignment.'})
            directory_url = next((x['speaker_directory_source'] for x in orthodox if x['church_id']==r['candidate_id'] and x['speaker_directory_source']),None)
            if directory_url:screen['source_links'].append(link('Official clergy directory', directory_url))
        screens.append(screen)
    assert len(screens) == 12
    return screens


def project_supplemental(root):
    seattle = load(root, 'supplementary-delivery/seattle-catholic-source-screen.json')
    star = load(root, 'supplementary-delivery/star-sea-source-screen.json')
    grace = load(root, 'supplementary-delivery/grace-cathedral-source-screen.json')
    rows = [
        {'id': 'supplemental-stjames-seattle', 'name': 'St James Cathedral', 'city': 'Seattle', 'state': 'WA', 'tradition': 'Roman Catholic; Archdiocese of Seattle', 'route': 'church_manuscript_and_recordings',
         'speaker_evidence': 'Father Michael G. Ryan became pastor emeritus on July 1, 2025; Father Gary F. Lazzeroni succeeded him. Ryan is named as guest homilist on October 19, 2025. A presider is not automatically the homilist.',
         'coverage': ['Two October 2025 manuscripts were inspected, by different named authors. October 2022 text availability remains unknown.', 'Livestream index entries cover five October 2022 and four October 2025 Sundays; recording completeness was not established.'],
         'limits': ['A June 15, 2025 index link currently displays the October 19 heading; do not count it as an additional June manuscript.', 'The exploratory May window is separate: four May 2025 texts and one 2022 candidate do not establish matched monthly coverage. The 2022 candidate has a May 1/May 2 date conflict.'],
         'next_action': 'Keep the October manuscript, role and date issues separate; resolve authorized historical text access before proposing a same-author panel.',
         'source_links': [link('Official cathedral', seattle['church']['official_site'])] + [link({'text_current_index':'Current manuscript index','text_emeritus_index':'Pastor emeritus manuscript index','livestream_index':'Livestream archive','ryan_biography':'Michael Ryan biography','lazzeroni_biography':'Gary Lazzeroni biography','site_information':'Site information'}[k],v) for k,v in seattle['sources'].items()],
         'observations': [{'date': r['date'], 'title': 'Homily', 'speaker': r['author'], 'source_url': r['url'], 'status_label': 'Header and visible text inspected', 'date_basis': 'Manuscript event-date header; independent delivery not established', 'format':'HTML manuscript', 'note': 'No full text retained.'} for r in seattle['primary_october']['text_2025']]},
        {'id': 'supplemental-star-sea-sf', 'name': 'Star of the Sea Catholic Church', 'city': 'San Francisco', 'state': 'CA', 'tradition': 'Catholic; Archdiocese of San Francisco', 'route': 'author_blog',
         'speaker_evidence': 'The official biography names Joseph Illo as pastor and links his blog. This establishes an author–church association, not a delivery venue for every post.',
         'coverage': ['Two October 2022 posts and three October 2025 posts were observed.', 'The official church page also links recent homily videos, but no historical recording inventory or captions were verified.'],
         'limits': ['Blog post dates are not confirmed preaching dates. The observed posts include pastoral essays.', 'Historical snapshots do not prove complete current archives; no continuous Sunday-sermon series or reuse grant was established.'],
         'next_action': 'Classify individual posts by genre and event evidence before treating them as sermons; establish any intended text-use basis separately.',
         'source_links': [link(s['role'].replace('October2022','October 2022').replace('October2025','October 2025'),s['url']) for s in star['sources']],
         'observations': [{'date': item['displayed_date'], 'title': item['title'], 'speaker': 'Joseph Illo (blog author; event speaker unconfirmed)', 'source_url': window['source_url'], 'status_label':'Blog post observed; sermon delivery unconfirmed', 'date_basis': 'Displayed blog post date', 'format':'Author blog post', 'note':'Not counted as a verified delivered sermon.'} for window in star['windows'] for item in window['observed_entries']]},
        {'id': 'supplemental-grace-cathedral-sf', 'name': 'Grace Cathedral', 'city': 'San Francisco', 'state': 'CA', 'tradition': grace['affiliation']['value'], 'route':'individual_html_manuscript',
         'speaker_evidence': 'A May 2025 manuscript names the Very Rev. Dr. Malcolm Clemens Young. A 2022 official article identifies him as dean, but no comparable 2022 manuscript was inspected.',
         'coverage': ['One substantive manuscript page published May 23, 2025 was inspected, outside the October windows.', 'October 2022 and 2025 manuscript continuity remains unknown.'],
         'limits': ['The inspected rendering ends the closing prayer mid-sentence; completeness is unknown, not proof that the original page is defective.', 'Other archive/video routes returned access restrictions or throttling. No transcript or matched two-period series was established.'],
         'next_action': 'Use the individual 2025 page only with its publication-date and completeness limits; resolve event date and reuse basis before acquisition.',
         'source_links': [link('Affiliation source', grace['affiliation']['evidence_url']),link('Observed 2025 manuscript',grace['direct_sermon_samples'][0]['url'])],
         'observations': [{'date':None,'publication_date':grace['direct_sermon_samples'][0]['publication_date'],'title':grace['direct_sermon_samples'][0]['title'],'speaker':grace['direct_sermon_samples'][0]['speaker'],'source_url':grace['direct_sermon_samples'][0]['url'],'status_label':'Visible text inspected; completeness unconfirmed','date_basis':'Publication date known; event date unknown','format':'HTML manuscript','note':'Not an October-window observation.'}]},
    ]
    for r in rows:
        r.update(category='supplemental_lead',category_label=CATEGORY['supplemental_lead'],route_label=ROUTES[r['route']],rights_id='not_established',directory_id=None,case_study=None,checked_on=CHECKED)
    return rows


def inspect_public(value):
    forbidden={'body','full_text','transcript','segments','email','phone','address','reader_id','source_line_start','source_line_end','checked_at_utc','derived_at_utc','local_path','review','audit','raw_sermon_body_retained'}
    if isinstance(value,dict):
        assert not forbidden.intersection(value), 'Non-public field in projection'
        for v in value.values():inspect_public(v)
    elif isinstance(value,list):
        for v in value:inspect_public(v)
    elif isinstance(value,str):
        assert not re.search(r'[\u3400-\u9fff]|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|/Users/|/workspace/|reader|workstream|tool_|current_read|L\d+\b',value,re.I), 'Unreviewed text or bookkeeping in projection: '+value[:100]
        if value.startswith(('https://','http://')):
            parsed=urlsplit(value);assert not parsed.username and not parsed.password
            assert parsed.hostname not in {'localhost','127.0.0.1'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_directory',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data/feasibility.json')
    args=parser.parse_args();root=args.input_directory
    screens=project_screens(root);supplemental=project_supplemental(root)
    fourth=project_fourth(root);thomas=project_thomas(root)
    counts={'screens':len(screens),'screen_states':len({r['state'] for r in screens}),'supplemental_leads':len(supplemental),'categories':dict(Counter(r['category'] for r in screens)),'overlap_with_identity_catalogue':sum(r['directory_id'] is not None for r in screens),'full_texts_retained':0}
    assert counts['categories']=={'platform_export':3,'priority_text':2,'supplemental_text':1,'deferred_panel':5,'recording_candidate':1}
    data={'schema_version':1,'checked_on':CHECKED,'counts':counts,
          'scope':'Twelve deliberately selected church/source screens, separate from the 86-identity catalogue. Three additional leads are shown separately. These are metadata observations, not acquired texts or a representative national sample.',
          'screens':screens,'supplemental':supplemental,'fourth':fourth,'thomas':thomas,'rights':project_rights(root)}
    assert len({r['id'] for r in screens + supplemental}) == 15
    for section, rows in [('fourth annual', fourth['annual_records']), ('fourth targets', fourth['target_checks']), ('thomas annual', thomas['annual_records']), ('thomas October', thomas['october_observations'])]:
        assert len({r['id'] for r in rows}) == len(rows), section
    assert all(r['confirmed_service_time'] is None for r in fourth['target_checks'] if r['year'] == 2025 or r['status'] != 'no_conflict')
    inspect_public(data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS: public projections written: 12 screens, 3 supplemental leads, Fourth 107/33, Thomas 88/9; no full texts.')


if __name__=='__main__':main()
