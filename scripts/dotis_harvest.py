#!/usr/bin/env python3
"""DOTIS harvester — krajské dotační portály na platformě DOTIS (React + Azure Functions).

Objev: dotace.khk.cz (React SPA) má veřejné anonymní API `POST {base}/Data/GetProjectSubprojectCollection {}`,
které vrátí KOMPLETNÍ strom programů → podprogramů (dotačních titulů) s `dateBeg`/`dateEnd`/`memo`/`name`.
To jsou přímo výzvy s termíny → strukturovaný zdroj (žádný LLM, žádný Apify). API base je v `{web}/config.js`
(`window.dotisConfig.dotisAPIUrl`). Tenhle harvester je GENERICKÝ — stejný kód pokryje JAKÝKOLI DOTIS kraj.

Lossless: ukládá CELÝ strom (i historické tituly) do raw JSON. Status dopočítá ingest z dat (ne stav `state`,
ten je nespolehlivý). Mapování program→oblast / titul→opportunity dělá ingest_dotis.py.

Usage:
  # auto-detekce API base z config.js:
  python3 scripts/dotis_harvest.py --web https://dotace.khk.cz --source dotace.khk.cz --out data/h_dotis_khk.json
  # nebo explicitní base:
  python3 scripts/dotis_harvest.py --api-base https://dotisreactfunctions.azurewebsites.net/api --source dotace.khk.cz --out ...
"""
import argparse, json, re, sys, urllib.request


def fetch_config_apibase(web):
    """Z {web}/config.js vytáhne window.dotisConfig.dotisAPIUrl."""
    cfg = urllib.request.urlopen(web.rstrip("/") + "/config.js", timeout=20).read().decode("utf-8", "replace")
    m = re.search(r'dotisAPIUrl\s*:\s*"([^"]+)"', cfg)
    return m.group(1).rstrip("/") if m else None


def post_json(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"},
                                 method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", help="https://dotace.khk.cz (auto-detekce API base z config.js)")
    ap.add_argument("--api-base", help="explicitní API base (.../api) — přebije --web detekci")
    ap.add_argument("--source", required=True, help="host pro evidenci (dotace.khk.cz)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    base = a.api_base.rstrip("/") if a.api_base else None
    if not base:
        if not a.web:
            sys.exit("Zadej --api-base nebo --web")
        base = fetch_config_apibase(a.web)
        if not base:
            sys.exit("config.js neobsahuje dotisAPIUrl → není to DOTIS, nebo jiná struktura")
    print(f"API base: {base}", file=sys.stderr)

    tree = post_json(base + "/Data/GetProjectSubprojectCollection", {})
    programs = tree.get("data") or []
    # číselník oblastí (memo→name) — bonus kontext
    try:
        projcol = post_json(base + "/Dictionary/GetProjectCollection", {}) if False else None
    except Exception:
        projcol = None

    n_subs = sum(len(p.get("subprojects") or []) for p in programs)
    out = {"source": a.source, "api_base": base, "programs": programs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "DOTIS_HARVEST", "source": a.source, "programs": len(programs),
                      "subprojects": n_subs, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
