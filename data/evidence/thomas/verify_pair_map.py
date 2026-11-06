#!/usr/bin/env python3
"""Verify the supplied metadata-only pair map with Python standard library; no network, acquisition or uploads."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
from datetime import date
import json,re,unicodedata
HERE=Path(__file__).resolve().parent
BOOK_ALIASES={}
BOOKS={'1 kings','2 kings','1 corinthians','2 corinthians','1 thessalonians','2 thessalonians','1 timothy','2 timothy','acts','ephesians','exodus','galatians','hebrews','isaiah','jeremiah','john','luke','matthew','philippians','psalm','revelation','romans'}
DASHES=str.maketrans({c:'-' for c in '\u2010\u2011\u2012\u2013\u2014\u2212'})
ATOM=r'\d+[a-z]?(?::\d+[a-z]?)?'
NUMERIC=re.compile(rf'{ATOM}(?:-{ATOM})?(?:,{ATOM}(?:-{ATOM})?)*\Z')

def norm(value):
    return ' '.join(unicodedata.normalize('NFKC', value or '').translate(DASHES).casefold().split())

def scripture(raw):
    if not raw:
        return [], [], [], 'missing', False
    tokens = [s.strip() for s in raw.split(';')]
    normalized, unparsed = [], []
    for token in tokens:
        s = re.sub(r'\s*([,:-])\s*', r'\1', norm(token))
        m = re.fullmatch(r'((?:[123] )?[a-z]+(?: [a-z]+)*) (.+)', s)
        if not m or m[1] not in BOOKS or not NUMERIC.fullmatch(m[2]):
            unparsed.append(token)
        else:
            normalized.append(BOOK_ALIASES.get(m[1], m[1]) + ' ' + m[2])
    status = 'complete' if not unparsed else ('partial' if normalized else 'unparseable')
    return tokens, normalized, unparsed, status, not unparsed

def classify(a,b):
    la,lb=a['liturgical_label_normalized'],b['liturgical_label_normalized']
    ra,rb=a['scripture_references_normalized'],b['scripture_references_normalized']
    shared=sorted(set(ra)&set(rb)); union=set(ra)|set(rb)
    labels_equal=(la==lb) if la and lb else None
    lists_equal=(sorted(ra)==sorted(rb)) if a['scripture_list_complete'] and b['scripture_list_complete'] else None
    if labels_equal is None: status='unknown_label'
    elif not labels_equal: status='nonmatch_label'
    elif shared: status='candidate'
    elif a['scripture_list_complete'] and b['scripture_list_complete']: status='nonmatch_scripture'
    else: status='unknown_scripture'
    reason={
        'candidate':'Exact normalized label and at least one exact normalized reference match.',
        'nonmatch_label':'Both labels are known and differ under the fixed exact-label rule.',
        'nonmatch_scripture':'Labels match, both displayed lists parse completely, and no whole normalized reference matches.',
        'unknown_label':'At least one label is absent or ambiguous.',
        'unknown_scripture':'Labels match but missing or unparseable scripture metadata prevents a conclusive no-match.'
    }[status]
    return {
        'pair_id':a['record_id']+'__'+b['record_id'],
        'record_2022_id':a['record_id'],'record_2025_id':b['record_id'],
        'date_2022':a['index_date'],'date_2025':b['index_date'],
        'title_2022':a['title'],'title_2025':b['title'],
        'url_2022':a['url_observed'],'url_2025':b['url_observed'],
        'cutoff_eligible_2022':a['cutoff_status']=='eligible',
        'classification':status,'classification_reason':reason,
        'label_2022':a['liturgical_label_observed'],'label_2025':b['liturgical_label_observed'],
        'normalized_labels_equal':labels_equal,
        'references_2022':ra,'references_2025':rb,
        'exact_shared_references':shared,'exact_shared_reference_count':len(shared),
        'reference_union_count':len(union),
        'reference_jaccard_ratio':len(shared)/len(union) if union else 0,
        'complete_list_equality':lists_equal,
        'scripture_parse_status_2022':a['scripture_parse_status'],
        'scripture_parse_status_2025':b['scripture_parse_status'],
        'version_markers_2022':a['version_markers_in_index_title'],
        'version_markers_2025':b['version_markers_in_index_title'],
        'record_data_flags_2022':a['data_flags'],'record_data_flags_2025':b['data_flags'],
        'evidence_level':'index_metadata_only','body_similarity_assessed':False,
        'candidate_rank':None,
    }

def rank_key(p):
    eq=p['complete_list_equality']; equality_order=0 if eq is True else 1 if eq is False else 2
    ratio=Fraction(p['exact_shared_reference_count'],p['reference_union_count']) if p['reference_union_count'] else Fraction(0)
    return (0 if p['cutoff_eligible_2022'] else 1,equality_order,-p['exact_shared_reference_count'],-ratio,p['date_2022'] or '9999-99-99',p['date_2025'] or '9999-99-99',p['record_2022_id'],p['record_2025_id'])

if __name__=='__main__':
    records=json.loads((HERE/'inventory.json').read_text(encoding='utf-8'))
    assert Counter(r['year'] for r in records)=={2022:43,2025:45}
    for r in records:
        assert norm(r['liturgical_label_observed'])==r['liturgical_label_normalized']
        tokens,refs,unparsed,status,complete=scripture(r['scripture_text_observed'])
        assert (tokens,refs,unparsed,status,complete)==(r['scripture_tokens_observed'],r['scripture_references_normalized'],r['scripture_unparsed_tokens'],r['scripture_parse_status'],r['scripture_list_complete'])
        if r['year']==2022: assert (r['cutoff_status']=='eligible')==(date.fromisoformat(r['index_date'])<=date(2022,11,30))
    pairs=[classify(a,b) for a in records if a['year']==2022 for b in records if b['year']==2025]
    queue=sorted([p for p in pairs if p['classification']=='candidate'],key=rank_key)
    for rank,p in enumerate(queue,1):p['candidate_rank']=rank
    assert pairs==json.loads((HERE/'pair-classifications.json').read_text(encoding='utf-8'))
    assert queue==json.loads((HERE/'candidate-queue.json').read_text(encoding='utf-8'))
    assert len(pairs)==1935 and len(queue)==15
    cut=[p for p in pairs if p['cutoff_eligible_2022']]
    assert len(cut)==1800 and sum(p['classification']=='candidate' for p in cut)==14
    print('Verified all 88 index rows, 1935 pair decisions, 15 ranks, and the 1800-pair / 14-candidate cutoff subset. No network or body operations performed.')
