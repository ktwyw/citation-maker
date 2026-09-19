# Citation maker — APA, Vancouver, GOST

Look a paper up by DOI or title, check and correct the fields, and get the
reference in **APA 7**, **Vancouver**, **GOST 7.1-2003** (the standard adopted
in Kazakhstan as СТ РК ГОСТ 7.1-2003) and **GOST R 7.0.5-2008** (the short
form many Russian journals use). Build a bibliography, copy it in any style,
or export RIS (Zotero, Mendeley, EndNote) or BibTeX (LaTeX, JabRef).

Two versions with the same formatting rules:

- `index.html` — web page. Live at https://ktwyw.github.io/citation-maker/
- `cite.py` — command-line tool, standard library only

## Can you trust the output?

Trust the structure; check the fields. Metadata comes from CrossRef, the
registry publishers deposit into when they register a DOI, so for journal
articles from established publishers the DOI, title, journal, year, volume
and author surnames are the publisher's own record. The tool never invents a
field: it either has data or leaves a gap and tells you.

What to check every time:

- **Author names** — often initials only; sometimes wrong order for Kazakh,
  Russian or Chinese names; occasionally a missing co-author.
- **Pages** — online-first articles may have only an article number or nothing.
- **Titles** — some publishers deposit in capitals. The *sentence case*
  button lowercases everything, then you re-capitalise proper nouns.
- **Journal names** — Vancouver uses the abbreviation, APA and GOST the full
  name; CrossRef doesn't always supply both.
- **Books and chapters** — patchier metadata; GOST wants a place of
  publication, which CrossRef often lacks.
- **Title search** — fuzzy. Confirm the DOI matches the paper you mean.
- **No DOI** — many Kazakhstani and Russian journals, older papers and grey
  literature. Use manual entry.
- **GOST variants** — journals apply house styles. Glance at the author
  guidelines.

Red fields in the form are required for that source type; yellow notes flag
the common gaps above.

## Web version

1. Paste a DOI (or a title) and click **Look up**, or click **Enter manually**.
2. Correct anything in the form; all four references update as you type.
3. Copy the one you need, or **Add to bibliography**. The list is saved in
   your browser; choose a style, sort by author or as added, then copy,
   download `.txt`, **Export RIS** or **Export .bib**. Each reference also shows
   its BibTeX entry with a generated key such as `bekova2025deep`.

The page must be served from a normal web address (GitHub Pages or opened
locally) for the CrossRef lookup to work; some sandboxed previews block it.

## Command line

```
python cite.py 10.1038/s41586-020-2649-2              # all four styles
python cite.py 10.1038/s41586-020-2649-2 --style gost71
python cite.py 10.1038/s41586-020-2649-2 --style bibtex >> refs.bib
python cite.py --title "Attention is all you need"    # best match; confirm the DOI
python cite.py 10.1234/x --json > ref.json             # save the record, edit it…
python cite.py --from ref.json --sentence-case         # …then format the edited record
python cite.py --template                              # blank record for a source without a DOI
```

Gaps are reported on stderr, e.g. `Check: pages (online-first?); author
given names are initials only`.

## The GOST rules implemented

- **7.1-2003**: heading with the first author for 1–3 authors; 4 or more
  authors are described under the title with the first three and `[и др.]`
  (`[et al.]` for Latin-script sources). Areas separated by ` . – `. Journal
  articles: `Title / Authors // Journal. – Year. – Т. 5, № 3. – С. 45–52. – DOI: …`
- **7.0.5-2008** short form: `Author A. A., Author B. B. Title // Journal.
  Year. Т. 5. № 3. С. 45–52.` with `и др.` after three authors.
- Cyrillic sources get Т./№/С.; Latin-script sources get Vol./№/P.

## Ideas for next steps

- In-text citation helper (APA author–date, Vancouver numbers)
- Batch mode: a file of DOIs in, a formatted list out
- Kazakh transliteration of author names for GOST lists in Latin script
