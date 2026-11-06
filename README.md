# Sermon research catalogue

**[Open the website](https://sermon-research-jenny.landenini.chatgpt.site/)** to compare collection routes, inspect church and clergy evidence, and follow original sources.

Start with **[Collection feasibility](https://sermon-research-jenny.landenini.chatgpt.site/#view=feasibility)**. For the map, open **[Churches & pastors → Map and state counts](https://sermon-research-jenny.landenini.chatgpt.site/#view=churches&map=open)**. Affiliation counts sit below the map; both follow the active filters.

## What can be collected?

Twelve sources were deliberately selected for closer inspection. These assessments identify routes and remaining checks; they are not a representative national sample or acquired text corpus.

| Assessment | Sources | What remains |
|---|---|---|
| 2 priority text candidates | Fourth Presbyterian, Chicago; Adam Thomas / St Mark’s Episcopal, Mystic | Resolve item-level conflicts and apply intended-use conditions. |
| 1 supplemental text route | Memorial Congregational, Sudbury | Use the specifically licensed author work within its conditions; two observed manuscripts do not establish weekly coverage. |
| 3 platform routes | Heritage Baptist, Trinity Baptist, Woodruff Road Presbyterian | Validate permitted SermonAudio export, historical coverage and transcript provenance. |
| 1 recording candidate | Holy Trinity Greek Orthodox, San Francisco | Establish recording/transcription rights, speakers and recording boundaries. |
| 5 deferred continuous-panel sources | Haller Lake, St Louis, Blessed Trinity, Co-Cathedral of St Theresa, Saint Katherine | Resolve sparse archives, restricted access, missing dates or incomplete two-period coverage. |

**[Three supplemental leads](https://sermon-research-jenny.landenini.chatgpt.site/#view=feasibility&group=supplemental)**—St James Cathedral in Seattle, Star of the Sea and Grace Cathedral in San Francisco—remain outside those twelve. One of the twelve overlaps the existing identity catalogue; do not add these collections together.

### Inspect the strongest examples

- **[Fourth Presbyterian](https://sermon-research-jenny.landenini.chatgpt.site/#view=feasibility&id=fourth-chicago-il):** 107 annual index records, including two explicit no-sermon services and one grouped youth entry. The 33 exact-target checks are a subset: 32 bodies rendered, 28 without an inspected conflict, four discrepancies and one unavailable target. Indexed and target-header service times remain separate; 2025 times are unconfirmed. Speaker tables retain 2022/2025 index and target counts.
- **[Adam Thomas / St Mark’s](https://sermon-research-jenny.landenini.chatgpt.site/#view=feasibility&id=stmark-mystic-ct):** 88 annual entries include nine October observations. Eight latest page reads succeeded; one failed after an earlier successful observation. Three same-liturgical-label pairs contain one equal-header-passage pair and two different passages. Index, event and publication dates remain distinct, including the May 9 index / May 8 header discrepancy.

These are metadata observations. They do not establish complete delivery, retained text or AI use.

## Other catalogue sections

| Section | Contents and counting unit |
|---|---|
| Churches & pastors | **86 supported identities** across 43 states and D.C.; **41 clergy-role records at 28 churches**. Historical, interim and undated role claims keep their qualifications. |
| Sermon & text records | **47 item records**: 36 earlier mixed-genre archive items, four publisher timed transcripts and seven manuscripts. This separate collection is not the twelve-source assessment. |
| Sources & methods | **83 source records**: 70 originals inspected, 11 inspection blocks and two discovery leads. Inspection does not establish permission or a usable corpus. |

**Full sermon texts, captions and recordings are not included.** Original publisher links show what each source makes available. A church role does not identify the speaker of every event, and lack of AI disclosure means unknown use.

The 86 accepted identities comprise 48 from the original 128 candidates and 38 from an additional 6,000. The original sample has 36 identity holds, one exclusion and 43 unreviewed candidates; the additional sample has 78 holds, five exclusions and 5,879 unreviewed candidates. The goal of 1,000 audited churches has not been reached.

Five source-linked affiliation updates bring the filled count to **43**, with **43 still unestablished**. Evidence varies between local statements and organization directories; this is not 43 equally precise verified jurisdictions. Two broad-tradition findings and two unavailable follow-ups remain notes, not exact affiliations. Clergy names remain unestablished for 58 accepted identities. These gaps overlap.

No item linked to the frozen church samples yet meets every church-linkage, date, delivery, quality and permission requirement. This does **not** mean there are zero feasible collection routes.

## Access and reuse

The website distinguishes operations rather than assigning one blanket permission label. Thomas’s observed **CC BY-NC-ND 3.0** notice supports conditional unchanged noncommercial copying/collections and necessary technical format changes, but not general adaptation permission. The specifically identified Allen Vander Meulen **CC BY-NC 4.0** work supports conditional noncommercial adaptation. Analysis is not automatically adaptation; assess the actual operation. Notices do not cover unrelated works or third-party materials. See the source detail pages and [attribution](NOTICE.md).

## Files and reproducibility

- [index.html](index.html): standalone interactive website. Download and open it in a browser; search, filters and the map work without a server. Original links require internet. GitHub’s file view does not run HTML.
- [data/catalogue.json](data/catalogue.json): existing church, item and source records with stable IDs.
- [data/feasibility.json](data/feasibility.json): separately counted collection screens, supplemental leads, nested observations and operation-specific rights.
- [Collection-route CSV](data/collection-feasibility.csv), [supplemental-lead CSV](data/supplemental-leads.csv), [church CSV](data/churches.csv), [item CSV](data/items.csv), [source CSV](data/sources.csv). Detail-page exports preserve inspected exceptions and unknowns.
- [src/](src/): readable website code and styles; [snapshot.json](snapshot.json): counts and HTML checksum; [notices/](notices/): required data and map license notices.

Run these offline checks with Python 3 and Node.js:

```sh
python3 scripts/build.py
python3 scripts/validate.py
node tests/public.test.cjs
```

The build uses only the two public JSON files. `scripts/project_feasibility.py INPUT_DIRECTORY` reproduces the feasibility projection from the separately supplied reviewed metadata package, selecting public fields explicitly. That input package, raw pages, correspondence and retained text bodies are not published here.

Evidence retains its individual review dates; this edition is dated **6 November 2026**. Keep unknowns, source links and separate counting units when updating. The original research repository and its restricted text history remain private.
