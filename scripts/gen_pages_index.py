#!/usr/bin/env python3
"""Postaví GitHub Pages site: app každé branche do site/branches/<name>/ + rozcestník site/index.html.

Běží v GitHub Actions (po fetch všech remote větví). Pro každou větev, která má v gitu
docs/grants_app.html, vytáhne ten soubor + popis (docs/PAGES_DESC.txt, fallback = subject commitu)
+ datum posledního commitu. Vygeneruje přehledovou homepage: karta na větev s popisem (co je jinak
proti main) a odkazem na její verzi appky.

Usage (v CI): python3 scripts/gen_pages_index.py site
"""
import subprocess, sys, os, html, datetime


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()


def branches():
    out = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    bs = []
    for ln in out.splitlines():
        b = ln.strip()
        if not b or b.endswith("/HEAD"):
            continue
        bs.append(b[len("origin/"):] if b.startswith("origin/") else b)
    return sorted(set(bs))


def has_app(b):
    return subprocess.run(["git", "cat-file", "-e", f"origin/{b}:docs/grants_app.html"]).returncode == 0


def show(b, path):
    r = subprocess.run(["git", "show", f"origin/{b}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def merged_to_main(b):
    """True = všechny commity větve jsou už v main (slito). None pro main."""
    if b == "main":
        return None
    return subprocess.run(["git", "merge-base", "--is-ancestor", f"origin/{b}", "origin/main"]).returncode == 0


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "site"
    os.makedirs(os.path.join(site, "branches"), exist_ok=True)
    cards = []
    for b in branches():
        if not has_app(b):
            continue
        d = os.path.join(site, "branches", b)
        os.makedirs(d, exist_ok=True)
        app = show(b, "docs/grants_app.html")
        if app is None:
            continue
        open(os.path.join(d, "grants_app.html"), "w", encoding="utf-8").write(app)
        desc = show(b, "docs/PAGES_DESC.txt") or git("log", "-1", "--format=%s", f"origin/{b}")
        date = git("log", "-1", "--format=%cd", "--date=short", f"origin/{b}")
        sha = git("log", "-1", "--format=%h", f"origin/{b}")
        cards.append((b, (desc or "").strip(), date, sha, merged_to_main(b)))
    # main první, pak abecedně
    cards.sort(key=lambda c: (c[0] != "main", c[0]))
    rows = []
    for b, desc, date, sha, merged in cards:
        if b == "main":
            badge = '<span class="main">main</span>'
        elif merged:
            badge = '<span class="mrg ok">✓ slito do main</span>'
        else:
            badge = '<span class="mrg no">⟳ neslito (rozpracováno)</span>'
        rows.append(f"""<a class=card href="branches/{html.escape(b)}/grants_app.html">
  <div class=h><span class=br>{html.escape(b)}</span>{badge}<span class=meta>{date} · {sha}</span></div>
  <p class=desc>{html.escape(desc) or '—'}</p>
  <span class=open>Otevřít aplikaci →</span></a>""")
    body = "\n".join(rows) or "<p>Žádná větev zatím nemá nasazenou aplikaci.</p>"
    gen = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = f"""<!doctype html><html lang=cs><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>re-grantio · větve</title>
<style>
:root{{--bg:#0b0e14;--card:#141925;--bd:#222a39;--fg:#e6ecf5;--mut:#8a96aa;--acc:#6ea8fe}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:880px;margin:0 auto;padding:40px 22px}}
h1{{font-size:26px;margin:0 0 4px}}.lead{{color:var(--mut);margin:0 0 26px}}
.card{{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px 18px;margin:0 0 12px;transition:border-color .15s}}
.card:hover{{border-color:var(--acc)}}
.h{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.br{{font-size:17px;font-weight:600;color:var(--acc)}}
.main{{font-size:10px;background:#2a3550;color:#9db4e6;padding:2px 7px;border-radius:20px;text-transform:uppercase;letter-spacing:.5px}}
.meta{{margin-left:auto;color:var(--mut);font-size:12px}}
.desc{{color:var(--fg);opacity:.85;margin:8px 0 10px;font-size:13.5px;white-space:pre-wrap}}
.open{{color:var(--acc);font-size:13px}}
.mrg{{font-size:10px;padding:2px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:.4px}}
.mrg.ok{{background:#173a2a;color:#74e0a8}}.mrg.no{{background:#3a3417;color:#e0cf74}}
.guide{{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:18px 20px;margin:0 0 26px}}
.guide h2{{font-size:18px;margin:0 0 8px}}.guide p{{font-size:13.5px;color:var(--fg);opacity:.9;margin:6px 0}}
.guide ol{{margin:8px 0 0;padding-left:20px}}.guide li{{margin:7px 0;font-size:13.5px}}
.guide code{{background:#0d1016;border:1px solid var(--bd);border-radius:4px;padding:1px 6px;font-size:12px;color:#9fd0ff}}
.guide pre{{background:#0d1016;border:1px solid var(--bd);border-radius:8px;padding:10px 12px;overflow-x:auto;font-size:12px;line-height:1.5;color:#cdd6e4;margin:6px 0}}
.guide .warn{{background:#15110a;border-left:3px solid #e0cf74;border-radius:0 8px 8px 0;padding:9px 12px;margin:10px 0;font-size:13px;color:#e0d4a8}}
.guide a{{color:var(--acc)}}
.h2b{{font-size:14px;color:var(--mut);margin:0 0 12px;text-transform:uppercase;letter-spacing:.5px}}
footer{{color:var(--mut);font-size:12px;margin-top:24px;text-align:center}}
footer a{{color:var(--mut)}}
</style></head><body><div class=wrap>
<h1>🎯 re-grantio</h1>
<p class=lead>Katalog českých grantů a dotací. Každá větev = vlastní verze aplikace + popis, čím se liší od <b>main</b>.</p>

<div class=guide>
<h2>🧩 Přidat další data (Claude Code + Opus)</h2>
<p>Repo je veřejné — naklonuj a rozšiř pokrytí. <b>Každé rozšíření = vlastní větev</b> s vlastní verzí appky (objeví se v seznamu níže po pushnutí).</p>
<div class=warn>⚠ <b>Než založíš novou větev:</b> ověř v seznamu níže, že předchozí větve jsou <b>✓ slité do main</b>. Pokud nejsou a nechceš schválně porovnávat víc variant proti sobě, nejdřív je smerguj — ať nestavíš na rozjeté divergenci.</div>
<ol>
<li><b>Naklonuj &amp; setup:</b><pre>git clone https://github.com/chocholous/regrantio.git
cd regrantio/opportunity_pipeline
python3.13 -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt &amp;&amp; playwright install chromium
bash scripts/unpack_data.sh</pre></li>
<li><b>Založ větev na rozšíření:</b> <code>git checkout main &amp;&amp; git pull &amp;&amp; git checkout -b rozsireni-&lt;co&gt;</code></li>
<li><b>Spusť Claude Code a přepni na Opus:</b> <code>claude</code> → <code>/model opus</code> (kategorie &amp; filtry dělá Opus)</li>
<li><b>Řekni Claudovi:</b> ať zjistí platformu nového zdroje → napíše tenký harvester (lossless, jen TEXT+dokumenty) → protáhne vrstvou 2 (Haiku pole, <b>Opus kategorie</b>) → zkonsoliduje a přestaví appku (<code>build_app.py</code>).</li>
<li><b>Popis větve:</b> přidej <code>docs/PAGES_DESC.txt</code> (1–3 věty, co je jinak vs main — ukáže se zde).</li>
<li><b>Commit + push</b> → GitHub Action sama nasadí appku větve a aktualizuje tuhle homepage.</li>
<li><b>Hotové rozšíření</b> → otevři PR a smerguj do main (badge se přepne na „✓ slito").</li>
</ol>
<p>Pravidla kvality: <b>status počítá kód</b> · harvest <b>lossless</b> · <b>kategorie/filtry = Opus</b> · grounding (evidence) · struktura před prózou. Plný recept: <a href="https://github.com/chocholous/regrantio">README.md / CLAUDE.md</a>.</p>
</div>

<p class=h2b>Větve projektu</p>
{body}
<footer>Generováno {gen} · <a href="https://github.com/chocholous/regrantio">github.com/chocholous/regrantio</a></footer>
</div></body></html>"""
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(out)
    print(f"index: {len(cards)} větví s aplikací → {site}/index.html")


if __name__ == "__main__":
    main()
