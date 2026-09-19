#!/usr/bin/env python3
"""
cite.py — format a reference in APA 7, Vancouver, GOST 7.1-2003 and GOST R 7.0.5-2008.

Look up by DOI (CrossRef, no key needed) or format a record you supply as JSON.

    python cite.py 10.1038/s41586-020-2649-2            # all four styles
    python cite.py 10.1038/s41586-020-2649-2 --style gost71
    python cite.py 10.1038/s41586-020-2649-2 --style bibtex >> refs.bib
    python cite.py --title "Attention is all you need"  # best title match; confirm the DOI
    python cite.py 10.1234/x --json > ref.json           # save the fetched record to edit
    python cite.py --from ref.json                       # format an edited record
    python cite.py --template                            # blank record for manual entry

Nothing is invented: fields come from the publisher's CrossRef record or from
the JSON you pass in. Empty fields are reported so you can fill them.
Standard library only.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "citation-maker@example.com"   # CrossRef "polite pool" contact; replace with yours

TEMPLATE = {
    "type": "journal-article",   # journal-article | book | book-chapter | proceedings-article | other
    "authors": [],               # [{"family": "Smith", "given": "John Paul"}, ...]
    "editors": [],
    "title": "",
    "container": "",             # journal, book or proceedings title
    "short": "",                 # journal abbreviation (Vancouver)
    "year": "",
    "volume": "",
    "issue": "",
    "pages": "",                 # "45–62" or an article number
    "doi": "",
    "publisher": "",
    "place": "",
    "url": "",
}


# ---------------------------------------------------------------------------
# CrossRef
# ---------------------------------------------------------------------------
def crossref(path: str) -> dict:
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"https://api.crossref.org/{path}{sep}mailto={MAILTO}",
                                 headers={"User-Agent": f"cite.py (mailto:{MAILTO})"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["message"]


def clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()


def from_crossref(w: dict) -> dict:
    type_map = {"journal-article": "journal-article", "book": "book", "monograph": "book", "edited-book": "book",
                "book-chapter": "book-chapter", "proceedings-article": "proceedings-article"}
    people = lambda lst: [{"family": a.get("family", a.get("name", "")), "given": a.get("given", "")} for a in (lst or []) if a.get("family") or a.get("name")]
    year = ""
    for key in ("issued", "published-print", "published-online"):
        parts = (w.get(key) or {}).get("date-parts") or [[None]]
        if parts[0][0]:
            year = str(parts[0][0]); break
    rec = dict(TEMPLATE)
    rec.update({
        "type": type_map.get(w.get("type"), "other"),
        "authors": people(w.get("author")),
        "editors": people(w.get("editor")),
        "title": clean_title((w.get("title") or [""])[0]),
        "container": (w.get("container-title") or [""])[0],
        "short": (w.get("short-container-title") or [""])[0],
        "year": year,
        "volume": w.get("volume", ""),
        "issue": w.get("issue", ""),
        "pages": (w.get("page") or "").replace("-", "–") or w.get("article-number", ""),
        "doi": w.get("DOI", ""),
        "publisher": w.get("publisher", ""),
        "place": w.get("publisher-location", ""),
    })
    return rec


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------
def initials(given: str, sep: str) -> str:
    parts = [p for p in given.split() if p]
    return sep.join("-".join(x[0].upper() + "." for x in p.split("-") if x) for p in parts)


def gost_name(p):   # I. O. Surname
    return f"{initials(p['given'], ' ')} {p['family']}" if p.get("given") else p["family"]


def head_name(p):   # Surname, I. O.
    return f"{p['family']}, {initials(p['given'], ' ')}" if p.get("given") else p["family"]


def van_name(p):    # Surname IO
    return f"{p['family']} {initials(p['given'], '').replace('.', '').replace('-', '')}" if p.get("given") else p["family"]


def is_cyr(s: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", s))


def dash(s: str) -> str:
    return re.sub(r"(\d)\s*-\s*(\d)", r"\1–\2", s)


def end_dot(s: str) -> str:
    return s if re.search(r"[.!?]$", s) else s + "."


def bare_doi(d: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)


def sentence_case(t: str) -> str:
    words = t.split(" ")
    all_caps = t == t.upper()
    out = []
    for i, w in enumerate(words):
        keep = not all_caps and re.fullmatch(r"[A-ZА-ЯЁ0-9\-]{2,6}", re.sub(r"[:,.;]$", "", w))
        x = w if keep else w.lower()
        if i == 0 or words[i - 1].endswith(":"):
            x = x[:1].upper() + x[1:]
        out.append(x)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def apa(f: dict) -> str:
    A, E = f["authors"], f["editors"]
    if not A:
        names = ""
    elif len(A) == 1:
        names = head_name(A[0])
    elif len(A) <= 20:
        names = ", ".join(map(head_name, A[:-1])) + ", & " + head_name(A[-1])
    else:
        names = ", ".join(map(head_name, A[:19])) + ", … " + head_name(A[-1])
    yr = f"({f['year']})." if f["year"] else "(n.d.)."
    link = f"https://doi.org/{bare_doi(f['doi'])}" if f["doi"] else f["url"]
    vol = f", {f['volume']}" + (f"({f['issue']})" if f["issue"] else "") if f["volume"] else (f", ({f['issue']})" if f["issue"] else "")
    pg = f", {dash(f['pages'])}" if f["pages"] else ""
    t = f["type"]
    if t in ("journal-article", "proceedings-article"):
        body = f"{end_dot(f['title'])} {f['container']}{vol}{pg}."
    elif t == "book":
        body = f"{end_dot(f['title'])} {f['publisher']}."
    elif t == "book-chapter":
        eds = ", ".join(gost_name(p) for p in E)
        eds = f"{eds} ({'Eds.' if len(E) > 1 else 'Ed.'}), " if E else ""
        pp = f" (pp. {dash(f['pages'])})" if f["pages"] else ""
        body = f"{end_dot(f['title'])} In {eds}{f['container']}{pp}. {f['publisher']}."
    else:
        body = end_dot(f["title"]) + (f" {f['container']}." if f["container"] else "") + (f" {f['publisher']}." if f["publisher"] else "")
    return re.sub(r"\s+", " ", f"{names + ' ' if names else ''}{yr} {body}{' ' + link if link else ''}").strip()


def vancouver(f: dict) -> str:
    A = f["authors"]
    names = ", ".join(map(van_name, A[:6])) + (", et al" if len(A) > 6 else "")
    jr = f["short"] or f["container"]
    t = f["type"]
    if t in ("journal-article", "proceedings-article"):
        body = f"{end_dot(f['title'])} {jr}. {f['year']}" + (f";{f['volume']}" if f["volume"] else "") + \
               (f"({f['issue']})" if f["issue"] else "") + (f":{dash(f['pages'])}" if f["pages"] else "") + "."
    elif t == "book":
        body = f"{end_dot(f['title'])} {f['place'] + ': ' if f['place'] else ''}{f['publisher']}; {f['year']}."
    elif t == "book-chapter":
        E = f["editors"]
        eds = ", ".join(map(van_name, E)) + (", editors. " if len(E) > 1 else ", editor. ") if E else ""
        body = f"{end_dot(f['title'])} In: {eds}{end_dot(f['container'])} {f['place'] + ': ' if f['place'] else ''}{f['publisher']}; {f['year']}." + \
               (f" p. {dash(f['pages'])}." if f["pages"] else "")
    else:
        body = f"{end_dot(f['title'])} {f['container'] or f['publisher']}. {f['year']}."
    link = f" doi:{bare_doi(f['doi'])}" if f["doi"] else (f" Available from: {f['url']}" if f["url"] else "")
    return re.sub(r"\s+", " ", f"{names + '. ' if names else ''}{body}{link}").strip()


def gost71(f: dict) -> str:
    """GOST 7.1-2003: heading for 1–3 authors; 4+ authors described under title, first three + [et al.]."""
    A, E = f["authors"], f["editors"]
    cyr = is_cyr(f["title"] + " ".join(a["family"] for a in A))
    T = dict(vol="Т.", no="№", p="С.", etal="[и др.]", ed="под ред.", pp="с", art="Ст.") if cyr else \
        dict(vol="Vol.", no="№", p="P.", etal="[et al.]", ed="ed. by", pp="p", art="Art.")
    heading = head_name(A[0]) + " " if 1 <= len(A) <= 3 else ""
    resp = "" if not A else (", ".join(map(gost_name, A)) if len(A) <= 3 else ", ".join(map(gost_name, A[:3])) + " " + T["etal"])
    pages = "" if not f["pages"] else (f"{T['p']} {dash(f['pages'])}" if re.search(r"[–-]", f["pages"]) else f"{T['art']} {f['pages']}")
    doi = f"DOI: {bare_doi(f['doi'])}" if f["doi"] else (f"URL: {f['url']}" if f["url"] else "")
    join = lambda parts: ". – ".join(p for p in parts if p) + "."
    t = f["type"]
    if t in ("journal-article", "proceedings-article"):
        vol_iss = ", ".join(x for x in (f"{T['vol']} {f['volume']}" if f["volume"] else "", f"{T['no']} {f['issue']}" if f["issue"] else "") if x)
        return heading + join([f"{f['title']} / {resp} // {f['container']}", f["year"], vol_iss, pages, doi])
    pub = " : ".join(x for x in (f["place"], f["publisher"]) if x) + (f", {f['year']}" if f["year"] else "")
    if t == "book":
        return heading + join([f"{f['title']} / {resp}", pub, f"{f['pages']} {T['pp']}" if f["pages"] else "", doi])
    if t == "book-chapter":
        eds = f" / {T['ed']} " + ", ".join(map(gost_name, E)) if E else ""
        return heading + join([f"{f['title']} / {resp} // {f['container']}{eds}", pub, pages, doi])
    return heading + join([f"{f['title']}{' / ' + resp if resp else ''}{' // ' + f['container'] if f['container'] else ''}", f["publisher"], f["year"], doi])


def gost705(f: dict) -> str:
    """GOST R 7.0.5-2008 short form, as used in many Russian journal reference lists."""
    A = f["authors"]
    cyr = is_cyr(f["title"] + " ".join(a["family"] for a in A))
    T = dict(vol="Т.", no="№", p="С.", etal="и др.", pp="с", art="Ст.") if cyr else dict(vol="Vol.", no="№", p="P.", etal="et al.", pp="p", art="Art.")
    nm = lambda p: f"{p['family']} {initials(p['given'], ' ')}" if p.get("given") else p["family"]
    names = ", ".join(map(nm, A)) if len(A) <= 3 else ", ".join(map(nm, A[:3])) + " " + T["etal"]
    doi = f" DOI: {bare_doi(f['doi'])}" if f["doi"] else (f" URL: {f['url']}" if f["url"] else "")
    pages = "" if not f["pages"] else (f" {T['p']} {dash(f['pages'])}." if re.search(r"[–-]", f["pages"]) else f" {T['art']} {f['pages']}.")
    lead = names + " " if names else ""
    t = f["type"]
    if t in ("journal-article", "proceedings-article"):
        return (f"{lead}{f['title']} // {f['container']}. {f['year']}." + (f" {T['vol']} {f['volume']}." if f["volume"] else "") +
                (f" {T['no']} {f['issue']}." if f["issue"] else "") + pages + doi).strip()
    pub = ": ".join(x for x in (f["place"], f["publisher"]) if x)
    if t == "book":
        return f"{lead}{f['title']}. {pub}, {f['year']}." + (f" {f['pages']} {T['pp']}." if f["pages"] else "") + doi
    if t == "book-chapter":
        return f"{lead}{f['title']} // {f['container']}. {pub}, {f['year']}.{pages}{doi}"
    return f"{lead}{f['title']}." + (f" {f['container']}." if f["container"] else "") + f" {f['year']}.{doi}"


_CYR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i",
        "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
        "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "ә": "a", "ғ": "g", "қ": "q", "ң": "n", "ө": "o", "ұ": "u", "ү": "u", "һ": "h", "і": "i"}


def bib_key(f: dict) -> str:
    """first author (ASCII) + year + first title word, e.g. bekova2025deep"""
    import unicodedata
    def fold(s):
        s = "".join(_CYR.get(c.lower(), c) for c in s)
        s = unicodedata.normalize("NFD", s)
        return re.sub(r"[^a-z0-9]", "", s.lower())
    a = f["authors"][0]["family"] if f["authors"] else "anon"
    w = re.search(r"\w+", f["title"])
    return f"{fold(a) or 'anon'}{f['year'] or 'nd'}{fold(w.group(0)) if w else 'ref'}"


def bibtex(f: dict) -> str:
    etype = {"journal-article": "article", "book": "book", "book-chapter": "incollection",
             "proceedings-article": "inproceedings", "other": "misc"}.get(f["type"], "misc")
    people = lambda lst: " and ".join(f"{p['family']}, {p['given']}" if p.get("given") else p["family"] for p in lst)
    fields = []
    add = lambda k, v: fields.append(f"  {k:<9} = {{{v}}}") if v else None
    add("author", people(f["authors"]))
    add("title", f["title"])
    if f["type"] == "journal-article":
        add("journal", f["container"])
    elif f["type"] in ("book-chapter", "proceedings-article"):
        add("booktitle", f["container"])
    elif f["type"] == "other":
        add("howpublished", f["container"])
    add("editor", people(f["editors"]))
    add("year", f["year"]); add("volume", f["volume"]); add("number", f["issue"])
    add("pages", dash(f["pages"]).replace("–", "--"))
    add("publisher", f["publisher"]); add("address", f["place"])
    add("doi", bare_doi(f["doi"]) if f["doi"] else ""); add("url", f["url"])
    return f"@{etype}{{{bib_key(f)},\n" + ",\n".join(fields) + "\n}"


STYLES = {"apa": ("APA 7", apa), "vancouver": ("Vancouver", vancouver),
          "gost71": ("GOST 7.1-2003", gost71), "gost705": ("GOST R 7.0.5-2008", gost705),
          "bibtex": ("BibTeX", bibtex)}

REQUIRED = {"journal-article": ["authors", "title", "container", "year"], "book": ["authors", "title", "publisher", "year"],
            "book-chapter": ["authors", "title", "container", "publisher", "year"],
            "proceedings-article": ["authors", "title", "container", "year"], "other": ["title", "year"]}


def gaps(f: dict) -> list[str]:
    out = [k for k in REQUIRED.get(f["type"], []) if not f[k]]
    if f["type"] == "journal-article" and not f["pages"]:
        out.append("pages (online-first?)")
    if not f["doi"] and not f["url"]:
        out.append("doi/url")
    if f["authors"] and all(re.fullmatch(r"([A-ZА-ЯЁ]\.?\s?)+", a.get("given", "") or "") for a in f["authors"]):
        out.append("author given names are initials only")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Format references in APA, Vancouver and GOST.")
    ap.add_argument("doi", nargs="?", help="a DOI to look up on CrossRef")
    ap.add_argument("--title", help="look up by title instead (fuzzy: confirm the DOI)")
    ap.add_argument("--from", dest="src", help="format a record from a JSON file")
    ap.add_argument("--style", choices=list(STYLES), help="print one style only")
    ap.add_argument("--json", action="store_true", help="print the record as JSON (to save and edit)")
    ap.add_argument("--sentence-case", action="store_true", help="convert the title to sentence case")
    ap.add_argument("--template", action="store_true", help="print a blank record for manual entry")
    args = ap.parse_args()

    if args.template:
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2)); return 0

    try:
        if args.src:
            rec = dict(TEMPLATE); rec.update(json.load(open(args.src, encoding="utf-8")))
        elif args.title:
            res = crossref(f"works?query.bibliographic={urllib.parse.quote(args.title)}&rows=1")
            if not res.get("items"):
                print("No match on CrossRef.", file=sys.stderr); return 1
            rec = from_crossref(res["items"][0])
            print(f"Best match — confirm DOI {rec['doi']} is the paper you mean.\n", file=sys.stderr)
        elif args.doi:
            m = re.search(r"10\.\d{4,9}/[^\s\"<>]+", args.doi)
            if not m:
                print("That doesn't look like a DOI.", file=sys.stderr); return 1
            rec = from_crossref(crossref("works/" + urllib.parse.quote(m.group(0).rstrip(".,;)"))))
        else:
            ap.print_help(); return 1
    except urllib.error.HTTPError as e:
        print(f"CrossRef: {e.code} {'not found' if e.code == 404 else e.reason}", file=sys.stderr); return 1
    except (urllib.error.URLError, OSError) as e:
        print(f"Network error: {e}", file=sys.stderr); return 1

    if args.sentence_case:
        rec["title"] = sentence_case(rec["title"])

    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2)); return 0

    for key, (label, fn) in STYLES.items():
        if args.style and key != args.style:
            continue
        if not args.style:
            print(f"{label}:")
        print(fn(rec) + ("\n" if not args.style else ""))
    g = gaps(rec)
    if g:
        print("Check: " + "; ".join(g), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
