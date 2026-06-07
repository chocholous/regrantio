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
        cards.append((b, (desc or "").strip(), date, sha))
    # main první, pak abecedně
    cards.sort(key=lambda c: (c[0] != "main", c[0]))
    rows = []
    for b, desc, date, sha in cards:
        tag = ' <span class="main">main</span>' if b == "main" else ""
        rows.append(f"""<a class=card href="branches/{html.escape(b)}/grants_app.html">
  <div class=h><span class=br>{html.escape(b)}</span>{tag}<span class=meta>{date} · {sha}</span></div>
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
footer{{color:var(--mut);font-size:12px;margin-top:24px;text-align:center}}
footer a{{color:var(--mut)}}
</style></head><body><div class=wrap>
<h1>🎯 re-grantio</h1>
<p class=lead>Katalog českých grantů a dotací. Níže jsou jednotlivé větve projektu — každá s vlastní verzí aplikace a popisem, čím se liší od <b>main</b>.</p>
{body}
<footer>Generováno {gen} · <a href="https://github.com/chocholous/regrantio">github.com/chocholous/regrantio</a></footer>
</div></body></html>"""
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(out)
    print(f"index: {len(cards)} větví s aplikací → {site}/index.html")


if __name__ == "__main__":
    main()
