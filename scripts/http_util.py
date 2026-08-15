#!/usr/bin/env python3
"""Sdílený HTTP helper — JEDNOTNÁ TLS politika napříč harvestery i doc-storem.

Audit #7/#32: harvestery běžely s CERT_NONE (verify OFF), ale doc-store downloader
(dsw2_fetch) ověřoval certifikáty (verify ON) → tytéž přílohy se zalistovaly, ale
NESTÁHLY (tiše, SSL CERTIFICATE_VERIFY_FAILED v manifestu). Tady je JEDEN zdroj pravdy.

Politika (env REGRANTIO_TLS):
  auto (default) — ověř (certifi/system trust store); při chybě OVĚŘENÍ CERTIFIKÁTU se
                   pro daný host JEDNOU nahlas zaloguje ⚠ a request se zopakuje BEZ
                   ověření. Bezpečné defaultně, ale bez tiché ztráty dat (české
                   municipální weby běžně posílají neúplný řetězec → proto měly CERT_NONE).
  strict        — vždy ověřuj, žádný fallback (cert chyba = tvrdá chyba, propaguje se).
  insecure      — nikdy neověřuj (CERT_NONE všude) = staré chování harvesterů.

Non-TLS chyby (timeout/DNS/refused) se NIKDY nepolykají — propagují se beze změny.
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import os
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

def _verified_context():
    """Ověřující kontext. Preferuje NATIVNÍ ověření operačního systému.

    ⚠ PROČ NEJDŘÍV OS, A NE certifi. Na strojích s antivirem, který rozpadá HTTPS
    (Avast, Kaspersky, firemní proxy), je řetěz podepsaný lokální CA. Ta je
    v úložišti Windows, ale v certifi z definice NENÍ — takže OpenSSL ověření
    zamítne a spadne to do fallbacku BEZ ověření. To je nejhorší kombinace:
    provoz jede dál, jen se přestane cokoli ověřovat, a pozná se to jen podle
    varování, které nikdo nečte.

    Naměřeno na tomhle stroji: bez truststore skončilo ověření u VŠECH zdrojů
    na `CERTIFICATE_VERIFY_FAILED: Basic Constraints of CA cert not marked
    critical` — což je vada certifikátu antiviru, ne zdroje. Přes nativní
    ověření (SChannel) tytéž zdroje projdou.

    `truststore` je nepovinný. Když chybí, chová se to jako dřív.
    """
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:  # noqa: BLE001
        pass

    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:  # noqa: BLE001
        pass  # bez certifi → system trust store (na Windows i Win ROOT store)
    return ctx


VERIFIED_CTX = _verified_context()

UNVERIFIED_CTX = ssl.create_default_context()
UNVERIFIED_CTX.check_hostname = False
UNVERIFIED_CTX.verify_mode = ssl.CERT_NONE

MODE = os.environ.get("REGRANTIO_TLS", "auto").lower()
_warned = set()


def _host(req):
    u = req.full_url if isinstance(req, urllib.request.Request) else req
    return urlsplit(u or "").netloc or "?"


def _warn_fallback(host):
    if host not in _warned:
        _warned.add(host)
        print(f"⚠ TLS: ověření certifikátu selhalo pro {host} → opakuji BEZ ověření "
              f"(REGRANTIO_TLS={MODE}; nastav strict pro tvrdé selhání)", file=sys.stderr)


def context(secure=True):
    """TLS kontext dle politiky — pro kód, který si drží vlastní opener (lewis_dynamo).
    V režimu auto/strict vrací ověřující kontext; v insecure vždy neověřující.
    Pozor: opener přes context() NEMÁ auto-fallback (ten je jen v urlopen())."""
    if MODE == "insecure" or not secure:
        return UNVERIFIED_CTX
    return VERIFIED_CTX


def urlopen(req, timeout=None, **kw):
    """urlopen s JEDNOTNOU TLS politikou + auto-fallback (viz modul docstring).
    `req` je urllib Request nebo URL string. Drop-in za urllib.request.urlopen."""
    if MODE == "insecure":
        return urllib.request.urlopen(req, timeout=timeout, context=UNVERIFIED_CTX, **kw)
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=VERIFIED_CTX, **kw)
    except (urllib.error.URLError, ssl.SSLError) as e:
        reason = getattr(e, "reason", e)
        if not isinstance(reason, ssl.SSLError):
            raise  # ne-TLS chyba (DNS/timeout/HTTPError/refused) → propaguj beze změny
        if MODE == "strict":
            raise
        _warn_fallback(_host(req))
        return urllib.request.urlopen(req, timeout=timeout, context=UNVERIFIED_CTX, **kw)
