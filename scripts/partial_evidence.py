"""Explicit English projection for the final four partial-reference comparisons."""
import copy
import json

PAGE_NOTES = {
 'AT-2022-043': (
  'Opens with Jesus praying after baptism and develops relationship, identity and joy, ending with an invitation to prayer and baptismal purpose.',
  'Thematic prose with a closing prayer invitation.',
  'No explicit update or sermon-reuse statement was observed.',
  'No specific event venue is identified in the prose.'),
 'AT-2025-044': (
  'Uses the author’s forty-second birthday and a science-fiction introduction to organize forty-two lessons about life, learning and love.',
  'Birthday-based list of forty-two lessons, not the same prose structure as the 2022 item.',
  'No explicit update or sermon-reuse statement was observed. A reference to an existing book is not a link to an earlier version of this sermon.',
  'The birthday setting is the author’s account; no specific event venue is identified.'),
 'AT-2022-032': (
  'Connects beginning again and new creation with a memory of the author’s first sermon, the prodigal son, and a closing parent–child building-block activity.',
  'Reflective prose with a personal recollection and family-activity ending.',
  'The author recalls a 2003 sermon about new creation but does not say this manuscript reuses it or link an earlier version.',
  'St. Michael and All Angels Church in Dallas belongs to the 2003 internship memory, not a verified venue for the 2022 event.'),
 'AT-2025-033': (
  'Moves from a middle-school experience of shame to the father welcoming the prodigal son and restoring belonging.',
  'Personal narrative and interpretation, with an acceptance-focused ending.',
  'The title says “updated,” but no earlier sermon date, title, version relationship or earlier-version link is identified. The 2022 comparison is not an established predecessor.',
  'No specific event venue is identified in the prose.'),
 'AT-2022-014': (
  'Uses music and a personal gaming experience to discuss being lost and found. The closing prose introduces prayer and an existing song.',
  'Prose followed by a song; the page should not be treated as one uniform prose unit. The song was not played or copied.',
  'The author says the personal experience has been discussed before and uses a song written early in the pandemic. Neither establishes a version relationship with the 2025 sermon.',
  'No specific event venue is identified in the prose.'),
 'AT-2025-014': (
  'Contrasts understandings of salvation through Luke 15 and First Timothy, ending with Eucharistic reflection and a concrete sense of mission.',
  'Interpretive prose with Eucharistic and mission-focused reflection.',
  'No explicit update or sermon-reuse statement was observed.',
  'The Eucharistic setting does not identify a verifiable church or event venue.'),
 'AT-2022-013': (
  'Acknowledges the difficult steward parable, focuses on debt reduction and interest, and uses Jeremiah and Exodus to discuss poverty, generosity and practical support.',
  'Interpretive prose with additional scripture and a contemporary news example.',
  'No explicit update or sermon-reuse statement was observed.',
  'St. Andrews Episcopal Church on Martha’s Vineyard is a news example, not a verified venue for this sermon.'),
 'AT-2025-013': (
  'Acknowledges the difficult steward parable, then focuses on shame about asking for help, poverty stigma, local wages, charity and justice.',
  'Interpretive prose with local economic examples and a closing prayer for action.',
  'No explicit update or sermon-reuse statement was observed.',
  'Calling New London County local and mentioning a deacon does not verify the specific church or event venue.')
}
PAIR_NOTES = {
 11: ('Baptismal identity and forty-two life lessons',
      'Both discuss the beloved identity expressed in baptism. The 2022 item develops relationship, identity and joy with additional scripture; the 2025 item uses a birthday-based list of forty-two lessons, with beloved identity as its starting point.',
      'Thematic prose versus a birthday-based list: similar subject matter does not establish the same manuscript.',
      'Only part of the listed scripture is shared. This supports a descriptive comparison, not complete scripture control or demonstrated text reuse.'),
 12: ('Beginning again and being welcomed',
      'The 2022 item connects new creation in Second Corinthians, a first-sermon memory and beginning again. The 2025 item moves from middle-school shame to the prodigal son’s acceptance.',
      'Both use personal narrative, with different framing and an additional listed passage in 2022.',
      '“Updated” identifies a title marker, not an earlier manuscript. No version link establishes the 2022 item as the 2025 item’s predecessor.'),
 13: ('Being found and being sent',
      'The 2022 item uses music and personal experience to discuss being lost and found, with prose introducing a closing song. The 2025 item moves from Luke 15 to First Timothy and the mission that follows salvation.',
      'Prose with a song ending versus prose with Eucharistic and mission-focused reflection; the additional listed passage differs.',
      'A shared lost-and-found theme does not establish manuscript reuse or complete scripture control. Keep the song component separate from prose.'),
 14: ('The steward parable and poverty',
      'Both acknowledge the steward parable’s difficulty before selecting a detail and reject a simple individual-blame account of poverty. The 2022 item emphasizes interest, debt, Jeremiah and Exodus; 2025 emphasizes shame about asking for help, local wages, charity and justice.',
      'Shared opening structure and poverty theme, with different details and additional scripture.',
      'These observations describe structural and thematic continuity, not a demonstrated manuscript-reuse relationship. No explicit version chain or prose-similarity measurement is established.')
}

def extend_partial(y, base):
 folder=base/'partial-pairs'
 if not folder.exists():return y
 read=lambda name:json.loads((folder/name).read_text(encoding='utf-8-sig'))
 t=y['thomas'];prior=copy.deepcopy(t['detail_status']);latest=read('latest-detail-status.json')
 for r in read('page-observations.json'):
  summary,genre,version,venue=PAGE_NOTES[r['record_id']];dates=r['displayed_post_dates'];lic=r['license_observation']
  observed=lic['label'] is not None
  license_note=('An earlier observation of this page exposed the blog’s CC BY-NC-ND 3.0 footer and separate NRSV/CEB notices. A later extraction did not reproduce that footer. This preserves the earlier observation; it is not a new live license confirmation or evidence that the license disappeared.' if observed else 'The page extraction did not expose a license footer. Notices on other pages do not resolve this page’s rights or third-party material.')
  t['pages'].append({
   'record_id':r['record_id'],'pair_id':r['pair_id'],'candidate_rank':r['candidate_rank'],
   'source_url':r['url'],'title':r['title'],'byline':r['byline'],
   'sermon_for_date':r['sermon_date'],'liturgical_label_exact':r['occasion'],
   'scripture_header_exact':r['detail_header_references'],
   'annual_listed_references':r['annual_listed_references'],
   'detail_header_matches_annual_list':r['detail_header_matches_annual_list'],
   'publication_date_first_displayed':dates[0] if dates else None,
   'additional_displayed_date':dates[1] if len(dates)>1 else None,
   'additional_displayed_date_scope':'Two dates appear beside the byline. The first matches the URL date; the meaning of the second was not separately verified. The sermon date comes from the detail header, not the post-date display.',
   'license_observation':{'status':'prior_footer_observation_retained' if observed else 'unknown_in_this_observation','notice':lic['label'],'url':lic['url'],'interpretation':license_note},
   'summary':summary,'genre':genre,'version_note':version,
   'third_party_note':'Scripture, song text, images and other third-party material have separate rights. Public readability or attribution is not republication permission.',
   'readable_prose':{'observed_on':latest['checked_on'],'representation_may_be_cached':True,'retrieval_cache_label_as_reported':r['retrieval_cache_label'],'opening_visible':r['substantive_prose_opening_visible'],'ending_visible':r['substantive_prose_ending_visible'],'internal_truncation_observed':None,'scope':'Current readable representation only; live-origin completeness, historical wording and spoken delivery are not independently verified.'},
   'venue_limit':venue+' Church association does not establish this event’s venue or independent delivery.',
   'event_venue':r['event_venue'],'event_venue_verified':r['event_venue_verified'],
   'historical_version_verified':r['historical_version_verified'],
   'explicit_prior_version_url_observed':False,'earlier_sermon_version_links_observed':r['earlier_sermon_version_links_observed']})
 pairs=copy.deepcopy(prior['pairs'])
 for r in read('pair-decisions.json'):
  title,summary,genre,limit=PAIR_NOTES[r['candidate_rank']]
  ps=[p for p in t['pages'] if p['pair_id']==r['pair_id']]
  same=len({p['liturgical_label_exact'] for p in ps})==1
  pairs.append({'pair_id':r['pair_id'],'candidate_rank':r['candidate_rank'],'record_ids':[r['record_2022_id'],r['record_2025_id']],'source_urls':r['source_urls'],'raw_detail_liturgical_labels_identical':same,'equivalent_liturgical_occasion_confirmed':same,'displayed_scripture_references_match_after_spacing_and_dash_normalization':r['complete_list_equality'],'comparison_group':'partial_reference'})
  t['comparisons'].append({'pair_id':r['pair_id'],'candidate_rank':r['candidate_rank'],'title':title,'summary':summary,'genre':genre,'decision':'Retain as a partial-reference descriptive comparison; not complete scripture control or an AI-use label.','limit':limit,'source_urls':r['source_urls'],'raw_labels_identical':same,'equivalent_occasion':same,'complete_displayed_references_match':r['complete_list_equality'],'historical_delivery_independently_verified':False,'numerical_body_similarity_computed':r['body_similarity_quantified'],'comparison_group':'partial_reference','complete_scripture_control':r['complete_scripture_control'],'sermon_reuse_established':r['sermon_reuse_established'],'reference_jaccard_ratio':r['reference_jaccard_ratio']})
 t['prior_detail_status']=prior
 t['detail_status']={'checked_on':latest['checked_on'],'counts':latest['latest_detail_counts'],'annual_counts':latest['annual_counts'],'new_addendum':latest['new_addendum'],'annual_classifier_changed':latest['annual_classifier_changed'],'limits':latest['limits'],'pair_ids':latest['pair_ids'],'pairs':pairs}
 t['summary']['scope']='Fixed annual index map, with a separate latest detail layer for all fourteen cutoff-eligible candidates: ten equal complete reference-list pairs and four partial-reference pairs.'
 t['summary']['detail_followthrough']=latest['latest_detail_counts']
 y['counts'].update(thomas_detail_pairs=14,thomas_detail_pages=28,thomas_complete_reference_pairs=10,thomas_partial_reference_pairs=4)
 route=next(r for r in y['decisions']['items'] if r['id']=='st-marks-mystic-thomas')
 route['annual_scope']='The fixed author index has 43 records dated 2022 and 45 dated 2025. Its 1,935 cross-year combinations include 1,800 under the inclusive November 30, 2022 cutoff. All 14 cutoff-eligible candidates have detail observations at 28 distinct pages: ten equal complete displayed-reference-list pairs and four partial-reference pairs. Thirteen raw detail labels agree; the Palm/Passion pair has equivalent occasion with different wording. The 2022 index has 41 Sunday-labeled rows but 40 calendar Sunday dates; 2025 has 42. These are not acquired or historically frozen texts.'
 route['next_step']='Inspect all fourteen comparisons, keeping the ten complete-reference-list pairs separate from the four partial-reference descriptions. Use their raw headers, genre differences, page-specific license observations and version limits. Passage overlap does not establish equal research quality, AI use or manuscript reuse.'
 return y
