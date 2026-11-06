#!/usr/bin/env python3
"""Build the standalone public catalogue and CSV downloads from reviewed metadata."""
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8-sig'))

def json_script(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')

def safe_cell(value):
    value = '' if value is None else str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value

def write_csv(name, headers, rows):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(headers)
    writer.writerows([[safe_cell(x) for x in row] for row in rows])
    (ROOT / 'data' / name).write_text(out.getvalue(), encoding='utf-8')

def main():
    data, f, e, c, x = read('data/catalogue.json'), read('data/feasibility.json'), read('data/extensions.json'), read('data/catholic.json'), read('data/comparison.json')
    data['counts']['affiliation_not_established'] = sum(r['affiliation'] == 'Not established' for r in data['churches'])
    (ROOT / 'data/catalogue.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    app = '\n'.join((ROOT / 'src' / n).read_text() for n in ('app.js', 'feasibility.js', 'extensions.js', 'catholic.js', 'comparison.js', 'startup.js'))
    html = (ROOT / 'src/template.html').read_text()
    for marker, value in [('@@CSS@@', (ROOT / 'src/styles.css').read_text() + '\n' + (ROOT / 'src/feasibility.css').read_text()), ('@@CATALOGUE@@', json_script(data)), ('@@FEASIBILITY@@', json_script(f)), ('@@EXTENSIONS@@', json_script(e)), ('@@CATHOLIC@@', json_script(c)), ('@@COMPARISON@@', json_script(x)), ('@@APP@@', app)]:
        assert html.count(marker) == 1, marker
        html = html.replace(marker, value)
    (ROOT / 'index.html').write_text(html)
    write_csv('churches.csv', ['Church', 'City', 'State', 'Affiliation', 'Affiliation as stated', 'Evidence scope', 'Affiliation checked', 'Church source checked', 'Original sources', 'Named clergy and roles'], [
        [r['name'], r['city'], r['state_name'], r['affiliation'], r['affiliation_as_stated'], r['affiliation_scope'], r.get('affiliation_checked_on'), r['checked_on'], ' | '.join(r['source_urls']), ' | '.join(p['name'] + ' — ' + (p.get('role_english') or p['role_verbatim']) for p in r['people']) or 'Not established'] for r in data['churches']])
    headers = ['Church / source', 'City', 'State', 'Tradition evidence', 'Category', 'Route', 'Speaker evidence', 'Observed coverage', 'Limits', 'Next action', 'Original sources']
    for key, filename in [('screens', 'collection-feasibility.csv'), ('supplemental', 'supplemental-leads.csv')]:
        write_csv(filename, headers, [[r['name'], r['city'], r['state'], r['tradition'], r['category_label'], r['route_label'], r['speaker_evidence'], ' | '.join(r['coverage']), ' | '.join(r['limits']), r['next_action'], ' | '.join(x['url'] for x in r['source_links'])] for original in f[key] for r in [dict(original, **e['orthodox']['screen_update']) if original['id']=='holy_trinity_sf' else dict(original, **x['seattle']['screen_update']) if original['id']=='supplemental-stjames-seattle' else dict(original, limits=[v.replace('All 2025 target service times remain unconfirmed.',x['fourth']['earlier_service_time_note']) for v in original['limits']]) if original['id']=='fourth-chicago-il' else original]])
    snapshot = read('snapshot.json')
    snapshot.update(source='Public catalogue with reviewed collection-feasibility metadata', snapshot_date='2026-11-06', index_sha256=hashlib.sha256(html.encode()).hexdigest(), counts=data['counts'], feasibility_counts=f['counts'])
    snapshot['extension_counts'] = e['counts']
    snapshot['catholic_counts'] = c['counts']
    snapshot['comparison_counts'] = x['counts']
    snapshot['data_origin'] = 'Five metadata datasets are embedded separately. Source decisions and new Seattle/Fourth observations extend existing sources without adding church or corpus totals. Catholic follow-up checks are linked to eight historical IDs; two written-homily supplements are counted separately. Historical entities, source screens, item records and accepted identities are not added together.'
    (ROOT / 'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    print('Built standalone HTML and CSVs from five separate public metadata datasets.')

if __name__ == '__main__':
    main()
