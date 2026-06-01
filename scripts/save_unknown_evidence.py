#!/usr/bin/env python3
"""Pro UNKNOWN hosty z re-fingerprintu ulož TRIMOVANÝ HTML důkaz (head meta,
title, generator, scripty/odkazy, patička, charakteristické cesty) do
platform_evidence/<host>.txt — vstup pro LLM workflow (agenti čtou, neřeší síť).
"""
import json, re, ssl, os, time, urllib.request
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
OUT = "platform_evidence"
os.makedirs(OUT, exist_ok=True)


def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.read(300000).decode("utf-8", "replace"), dict(r.headers), r.status
    except Exception as e:  # noqa: BLE001
        return f"__ERR__ {type(e).__name__}: {str(e)[:50]}", {}, None


def evidence(html, hdrs):
    head = re.search(r"<head[^>]*>(.*?)</head>", html, re.S | re.I)
    head = head.group(1) if head else html[:4000]
    metas = re.findall(r"<meta[^>]+>", head, re.I)[:25]
    links = re.findall(r'<link[^>]+href="([^"]+)"[^>]*>', head, re.I)[:25]
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', html, re.I)[:25]
    foot = re.search(r"(?is)(<footer.*?</footer>|(?:powered by|provozuje|vytvořil[oa]?|redakční systém|cms)[^<]{0,80})", html)
    body_txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    paths = sorted(set(re.findall(r'href="(/[a-z0-9_\-/]{2,30})"', html, re.I)))[:30]
    hdr_str = "\n".join(f"{k}: {v}" for k, v in hdrs.items()
                        if k.lower() in ("server", "x-powered-by", "x-generator", "set-cookie", "x-drupal-cache", "x-aspnet-version"))
    parts = [
        "## HTTP HEADERS\n" + (hdr_str or "(žádné výmluvné)"),
        "## META\n" + "\n".join(metas),
        "## LINK href (css/icons)\n" + "\n".join(links),
        "## SCRIPT src\n" + "\n".join(scripts),
        "## URL CESTY (nav)\n" + " ".join(paths),
        "## FOOTER / powered-by\n" + (re.sub(r"\s+", " ", foot.group(1))[:400] if foot else "(nenalezeno)"),
        "## TITLE+TEXT (úryvek)\n" + body_txt[:600],
    ]
    return "\n\n".join(parts)


def main():
    o = json.load(open("platform_refingerprint_out.json"))
    targets = [r for r in o["results"] if r.get("detected") in ("UNKNOWN",)]
    manifest = []
    for i, r in enumerate(targets):
        html, hdrs, code = fetch(r["base"])
        path = os.path.join(OUT, re.sub(r"[^a-z0-9.]+", "_", r["host"].lower()) + ".txt")
        if html.startswith("__ERR__"):
            content = f"HOST: {r['host']}\nBASE: {r['base']}\nLABEL_V_DATASETU: {r.get('label')}\nFETCH: {html}"
        else:
            content = (f"HOST: {r['host']}\nBASE: {r['base']}\nLABEL_V_DATASETU: {r.get('label')}\n"
                       f"HTTP: {code}\n\n" + evidence(html, hdrs))
        open(path, "w", encoding="utf-8").write(content)
        manifest.append({"host": r["host"], "base": r["base"], "label": r.get("label"),
                         "path": os.path.abspath(path)})
        if (i + 1) % 25 == 0:
            print(f"{i+1}/{len(targets)}", flush=True)
    json.dump(manifest, open("unknown_manifest.json", "w"), ensure_ascii=False, indent=1)
    print(f"EVIDENCE_DONE {len(manifest)} → {OUT}/ + unknown_manifest.json")


if __name__ == "__main__":
    main()
