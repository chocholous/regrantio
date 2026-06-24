#!/usr/bin/env python3
"""Re-fingerprint platforem: stáhni homepage každého 200-webu, urči SKUTEČNÝ CMS
z generator meta / hlaviček / charakteristických markerů a porovnej s labelem
v merged_dataset. Odhalí slité labely (jako mv_legacy) + identifikovatelné UNKNOWN.
MARKER → platform_refingerprint_out.json.
"""
import json, re, ssl, time, urllib.request
from urllib.parse import urlparse
from collections import Counter

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
import http_util   # jednotná TLS politika (audit #7/#32)
LOG = "platform_refingerprint.log"

# podpisy: (název, regexy v HTML/headers). Pořadí = priorita (specifické dřív).
SIGS = [
    ("wordpress", [r"/wp-content/", r"/wp-json", r'name="generator"[^>]*WordPress']),
    ("plone", [r'name="generator"[^>]*Plone', r"/resolveuid/", r"\+\+resource\+\+", r"portal_css"]),
    ("vismo", [r"webhouse", r"aspinclude/vismoweb", r"vismo", r'class="dok"']),
    ("aspnet_clanek_mvhzs", [r"/clanek/[\w-]+\.aspx", r"/soubor/[\w-]+\.aspx"]),
    ("drupal", [r'name="generator"[^>]*Drupal', r"Drupal\.settings", r"/sites/default/files", r"/sites/all/"]),
    ("joomla", [r'name="generator"[^>]*Joomla', r"/media/jui/", r"com_content", r"/templates/.*?/css"]),
    ("typo3", [r"/typo3conf/", r"/typo3temp/", r'name="generator"[^>]*TYPO3']),
    ("liferay", [r"Liferay", r"/o/liferay", r"/web/guest"]),
    ("nextjs_react", [r"__NEXT_DATA__", r"/_next/static"]),
    ("nuxt_vue", [r"__NUXT__", r"/_nuxt/"]),
    ("public4u", [r"Public4u", r"public4u"]),
    ("gordic_ginis", [r"gordic", r"ginis", r"/gordic/ginis"]),
    ("grantys", [r"grantys"]),
    ("galileo", [r"[Gg]alileo"]),
    ("dsw2_otevrenamesta", [r"var fonds=", r"dsw2\.otevrenamesta", r"/explore/(fonds|appeals)"]),
    ("sharepoint", [r"_layouts/15", r"SharePoint", r"sp\.runtime"]),
    ("webnode", [r"webnode"]),
    ("wix", [r"wix\.com", r"X-Wix-"]),
    ("squarespace", [r"squarespace"]),
]


def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with http_util.urlopen(req, timeout=timeout) as r:
            body = r.read(400000).decode("utf-8", "replace")
            hdrs = " ".join(f"{k}:{v}" for k, v in r.headers.items())
            return body + "\n" + hdrs, r.status
    except Exception as e:  # noqa: BLE001
        return f"__ERR__ {type(e).__name__}", None


def detect(blob):
    hits = []
    gen = re.search(r'name="generator"[^>]*content="([^"]+)"', blob, re.I)
    powered = re.search(r"X-Powered-By:\s*([^\n]+)", blob, re.I)
    server = re.search(r"\bServer:\s*([^\n]+)", blob, re.I)
    for name, pats in SIGS:
        matched = [p for p in pats if re.search(p, blob, re.I)]
        if matched:
            hits.append((name, len(matched), matched[:2]))
    hits.sort(key=lambda x: -x[1])
    return {
        "detected": hits[0][0] if hits else "UNKNOWN",
        "all_hits": [h[0] for h in hits],
        "evidence": hits[0][2] if hits else [],
        "generator": gen.group(1)[:60] if gen else None,
        "x_powered_by": powered.group(1).strip()[:40] if powered else None,
        "server": server.group(1).strip()[:40] if server else None,
    }


def main():
    d = json.load(open("data/merged_dataset.json"))
    # 1 záznam na unikátní host (homepage), nes label z datasetu
    by_host = {}
    for r in d:
        h = urlparse(r["url"]).netloc
        base = f"{urlparse(r['url']).scheme}://{h}"
        if h not in by_host:
            by_host[h] = {"base": base, "label": r.get("platform"), "status": r.get("status")}
    hosts = sorted(by_host)
    open(LOG, "w").write(f"re-fingerprint {len(hosts)} hostů\n")
    results = []
    for i, h in enumerate(hosts):
        rec = dict(by_host[h]); rec["host"] = h
        blob, code = fetch(rec["base"])
        rec["http"] = code
        if blob.startswith("__ERR__") or code is None:
            rec["detected"] = "ERR"; rec["err"] = blob[:40]
        else:
            rec.update(detect(blob))
            rec["mismatch"] = (rec["detected"] not in ("UNKNOWN",) and rec.get("label") not in (None, "UNKNOWN")
                               and not _same(rec["detected"], rec["label"]))
        results.append(rec)
        if (i + 1) % 25 == 0:
            open(LOG, "a").write(f"{i+1}/{len(hosts)}\n")
    json.dump({"marker": "REFP_DONE", "n": len(results), "results": results},
              open("platform_refingerprint_out.json", "w"), ensure_ascii=False, indent=1)
    open(LOG, "a").write(f"REFP_DONE {len(results)}\n")


def _same(det, label):
    label = (label or "").lower()
    m = {"aspnet_clanek_mvhzs": "mv_legacy", "nextjs_react": "react_nextjs",
         "nuxt_vue": "vue_nuxt", "dsw2_otevrenamesta": "dsw2"}
    return m.get(det, det) in label or det in label


if __name__ == "__main__":
    main()
