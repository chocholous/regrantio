#!/usr/bin/env python3
"""WordPress REST harvester — MAXIMUM detailu (žádný ořez, zachované odkazy).

Pro daný (base, rest_base, entity) stáhne VŠECHNY položky CPT/typu přes
`/wp-json/wp/v2/{rest_base}?per_page=100&_embed` a z každé vytáhne:
  id, foundation_id, type, entity, title (kanonický stripovaný), title_html (raw HTML titulku),
  slug, url(link), date, modified, status,
  excerpt_text, text (PLNÝ stripovaný, bez ořezu; raw HTML je v content.rendered),
  links[] (všechny href z obsahu), documents[] (href s příponou pdf/doc/xls/...),
  images[], terms{taxonomie:[názvy]} (z _embedded wp:term), meta (neprázdné, bez theme cruft).

Nahrazuje 11 ad-hoc skriptů z workflow. Konfigurace přes CLI.
Pozn.: `_embed` vrací názvy taxonomických termů inline (1 dotaz, bez doplňků).
"""
import argparse, html, json, os, re, sys, urllib.request, urllib.error
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (compatible; grantio-research/0.1)"
DOC_RE = re.compile(r"\.(pdf|docx?|rtf|xlsx?|odt|ods|pptx?|zip)(\b|\?|$)", re.I)
HREF_RE = re.compile(r'href="([^"]+)"', re.I)
IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
META_CRUFT = re.compile(r"^(neve_|wp_typography|inline_featured|footnotes|_eb_attr|gutentor|_yoast|rank_math)", re.I)


def slug_of(u):
    m = re.match(r"https?://([^/]+)", u or "")
    host = re.sub(r"^www\.", "", m.group(1)) if m else (u or "")
    return re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h).replace("\xa0", " ")
    h = re.sub(r"[ \t]+", " ", h)
    return re.sub(r"\n{3,}", "\n\n", h).strip()


def fetch(url, timeout, retries=3):
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as e:
            return e.code, b"", {}
        except Exception:  # noqa: BLE001
            pass
    return None, b"", {}


def terms_from_embed(item):
    out = {}
    for grp in (item.get("_embedded", {}) or {}).get("wp:term", []) or []:
        for t in grp or []:
            if isinstance(t, dict):
                out.setdefault(t.get("taxonomy", "term"), []).append(t.get("name"))
    return out


def harvest(base, rest_base, entity, timeout, per_page=100, categories=None):
    """categories: volitelný seznam WP category ID → REST scope `&categories=a,b,c`
    (vrací posty v KTERÉKOLI z nich = OR) → cílený sběr dotační sekce místo celého webu."""
    fid = slug_of(base)
    cat_q = f"&categories={','.join(str(c) for c in categories)}" if categories else ""
    items, page = [], 1
    while page <= 100:
        st, body, hdr = fetch(f"{base}/wp-json/wp/v2/{rest_base}?per_page={per_page}&page={page}&_embed{cat_q}", timeout)
        # někteří poskytovatelé stropují per_page → status 200 ale PRÁZDNÉ tělo: sniž a zkus znovu
        if st == 200 and not body and per_page > 10:
            per_page = max(10, per_page // 2)
            continue
        if st != 200 or body[:1] not in (b"[", b"{"):
            break
        try:
            arr = json.loads(body)
        except json.JSONDecodeError:
            break
        if not isinstance(arr, list) or not arr:  # chybový dict {"code":...} → konec stránkování
            break
        for it in arr:
            if not isinstance(it, dict):
                continue
            ch = (it.get("content") or {}).get("rendered", "") or ""
            links = sorted({html.unescape(u) for u in HREF_RE.findall(ch) if u.startswith("http")})
            # LOSSLESS: zachovej VŠECHNA raw pole z REST (vč. custom-type: call_region, rok,
            # acf, featured_media, template, yoast, tags…) a NAVRCH přidej odvozená convenience pole.
            terms = terms_from_embed(it)
            rec = dict(it)                         # všechna raw pole beze ztráty
            rec.pop("_embedded", None)             # jen redundantní embed kopie (názvy přesunuty do terms_resolved; ID zůstávají v raw polích)
            rec.update({
                "foundation_id": fid, "harvest_type": rest_base, "entity": entity,
                "wp_id": it.get("id"), "url": it.get("link"),
                "title": to_text((it.get("title") or {}).get("rendered", "")),  # kanonický stripovaný titulek (konzument build_extract_input._shape)
                "title_html": (it.get("title") or {}).get("rendered", ""),      # LOSSLESS: raw HTML titulek (kanonický title výše přepsal raw title objekt)
                "excerpt_text": to_text((it.get("excerpt") or {}).get("rendered", "")),
                "text": to_text(ch),               # PLNÝ stripovaný text (raw HTML je v content.rendered)
                "links": links,
                "documents": [u for u in links if DOC_RE.search(u)],
                "images": sorted({html.unescape(u) for u in IMG_RE.findall(ch)}),
                "terms_resolved": terms,           # názvy taxonomií z _embed
            })
            items.append(rec)
        try:
            total_pages = int(hdr.get("x-wp-totalpages") or page)
        except ValueError:
            total_pages = page
        if page >= total_pages:
            break
        page += 1
    return items


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--rest-base", required=True)
    ap.add_argument("--entity", default="grant")
    ap.add_argument("--out-dir", default="data/wp_full")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--per-page", type=int, default=100)
    ap.add_argument("--categories", help="čárkou oddělené WP category ID — sběr jen z těchto kategorií (OR), místo celého webu")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    cats = [c.strip() for c in args.categories.split(",") if c.strip()] if args.categories else None
    items = harvest(args.base, args.rest_base, args.entity, args.timeout, args.per_page, cats)
    fid = slug_of(args.base)
    suffix = f"__{args.rest_base}" + (f"__cat-{'-'.join(cats)}" if cats and len(cats) <= 6 else ("__cat" if cats else ""))
    path = os.path.join(args.out_dir, f"{fid}{suffix}.jsonl")
    with open(path, "w", encoding="utf-8") as o:
        for it in items:
            o.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "WP_FULL", "base": args.base, "rest_base": args.rest_base,
                      "categories": cats, "items": len(items),
                      "with_documents": sum(1 for it in items if it["documents"]),
                      "total_documents": sum(len(it["documents"]) for it in items), "out": path},
                     ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
