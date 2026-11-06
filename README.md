# Sermon research catalogue

**[Open the website](https://sermon-research-jenny.landenini.chatgpt.site/)** to browse church identities, clergy roles, text-item records and original sources. This repository contains the same public catalogue, its metadata and the notices required by its data sources.

**Find the map:** open [Churches & pastors](https://sermon-research-jenny.landenini.chatgpt.site/#view=churches), then expand **Map and state counts**. **Affiliation counts** is directly below it. Both reflect the active filters, so clear filters to see all 86 accepted identities.

## What is included

| Section | Current contents |
|---|---|
| Overview | What the catalogue contains and what it can establish. |
| Churches & pastors | 86 source-supported church identities, with city/state, affiliation evidence and original links. 28 churches have 41 named clergy-role records. Former clergy, interim roles and undated history claims are identified separately. |
| Sermon & text records | 47 item records: 36 earlier mixed-genre archive texts, four publisher timed transcripts and seven manuscripts. Records include titles, attributed authors/speakers, dates and their meaning, formats, quality limits and publisher links. |
| Sources & methods | 83 source records: 70 originals inspected, 11 inspection blocks and two discovery leads. Inspection does not establish collection permission or a usable corpus. |

**Full sermon texts, captions and recordings are not included.** Follow an item's original publisher link to see what that source makes available. Public reading, private retention and research reuse have different permission requirements.

## Why does the website show 86 churches?

The 86 are identities supported by completed reviews: **48 from the original sample plus 38 from the additional sample**. The larger numbers count candidate locations selected for checking, not verified churches or collected sermons.

| Identity review | Original sample | Additional sample |
|---|---:|---:|
| Candidates selected | 128 | 6,000 |
| Identity supported | 48 | 38 |
| More identity evidence needed | 36 | 78 |
| Excluded from current counting | 1 | 5 |
| Not yet reviewed | 43 | 5,879 |

The accepted identities span 43 states and D.C. This is not a representative national sample, and the goal of 1,000 audited churches has not been reached. Among the 86 accepted identities, 58 lack a supported clergy name and 48 lack an exact denominational affiliation. These gaps overlap.

**Zero formal sermon units currently meet every requirement** for church linkage, date, delivery, text quality and permission. The 47 text-item records are separate collections and do not fill that gap. Neither text style nor a lack of disclosure establishes whether a preacher used AI.

## Files and local use

- [index.html](index.html): the complete interactive catalogue, unchanged from the approved public v20 build. Download it, then open the downloaded file in a browser. Search, filters and the map work without a server; original-source links need internet access. GitHub's file view does not run the website.
- [data/catalogue.json](data/catalogue.json): the exact dataset embedded in the HTML, including source links and evidence limits.
- [Church CSV](data/churches.csv), [item CSV](data/items.csv), [source CSV](data/sources.csv): selected fields for browsing or analysis. Use the JSON or website details for the full qualifications.
- [snapshot.json](snapshot.json): counts, date and the HTML checksum.
- [NOTICE.md](NOTICE.md) and [notices/](notices/): source attribution and applicable license texts.

This snapshot was prepared on **6 November 2026**. Individual records retain their own source-check dates. A source-stated clergy role is not an independently verified current appointment; an item date does not prove delivery as written.

## Check or update the catalogue

Run `python3 scripts/validate.py` to check counts, the HTML checksum, JSON agreement, CSV row counts and the public-data boundary. It makes no network requests.

Updates should start with reviewed public metadata and source links. Preserve stable record identifiers and evidence dates, keep unknowns explicit, and validate before committing. Do not add raw webpages, correspondence, credentials, or sermon/transcript bodies without separately established publication rights. This repository starts with a fresh history containing only the public edition; the underlying research archive remains private.
