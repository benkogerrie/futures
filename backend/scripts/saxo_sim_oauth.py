#!/usr/bin/env python3
"""
Eenmalige Saxo OpenAPI SIM — OAuth Authorization Code → refresh token.

Gebruik (PowerShell, vanuit backend/):

  .venv\\Scripts\\Activate.ps1
  python scripts/saxo_sim_oauth.py

Vereist in omgeving of in backend/.env:
  SAXO_APP_KEY, SAXO_APP_SECRET, SAXO_REDIRECT_URI
Optioneel:
  SAXO_AUTH_BASE_URL (default https://sim.logonvalidation.net)
  SAXO_WRITE_REFRESH (pad; default ./.saxo_refresh naast backend/.env)

Vercel / productie-callback (URL uit browser, mag #fragment bevatten):

  python scripts/saxo_sim_oauth.py --exchange-url "https://jouw-domein/auth/saxo/callback?code=...&state=..."
"""

from __future__ import annotations

import argparse
import base64
import os
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import httpx

SIM_AUTH = "https://sim.logonvalidation.net"


def load_dotenv_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def basic_auth_header(app_key: str, app_secret: str) -> str:
    token = base64.b64encode(f"{app_key}:{app_secret}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def exchange_code(
    auth_base: str,
    app_key: str,
    app_secret: str,
    redirect_uri: str,
    code: str,
) -> dict:
    url = auth_base.rstrip("/") + "/token"
    body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    )
    headers = {
        "Authorization": basic_auth_header(app_key, app_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    r = httpx.post(url, content=body, headers=headers, timeout=60.0)
    r.raise_for_status()
    return r.json()


def wait_for_callback(redirect_uri: str, expected_state: str, timeout: int) -> tuple[str | None, str | None]:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        return None, "Alleen http:// redirect URIs worden automatisch afgehandeld (gebruik handmatige modus)."
    host = (parsed.hostname or "").lower()
    if host not in ("localhost", "127.0.0.1"):
        return None, "Host moet localhost of 127.0.0.1 zijn voor de ingebouwde callback-server."

    port = parsed.port or (80 if parsed.scheme == "http" else 443)
    if port == 80:
        return None, "Gebruik een vrije poort in je redirect URI, bv. http://localhost:8765/callback (poort 80 is lastig op Windows)."

    path_only = parsed.path or "/"
    if path_only != "/" and path_only.endswith("/"):
        path_only = path_only.rstrip("/")

    done: dict[str, str | None] = {"code": None, "err": None}
    event = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            req = urlparse(self.path)
            if req.path != path_only:
                self.send_error(404, "Verkeerd pad — controleer SAXO_REDIRECT_URI.")
                return
            qs = parse_qs(req.query)
            if qs.get("error"):
                done["err"] = qs.get("error_description", qs["error"])[0] if qs.get("error_description") else qs["error"][0]
                self._ok_html("Inloggen afgebroken. Sluit dit tabblad en kijk in de terminal.")
                event.set()
                return
            code = (qs.get("code") or [None])[0]
            state = (qs.get("state") or [None])[0]
            if not code:
                done["err"] = "Geen ?code= in callback."
                self._ok_html("Geen code ontvangen. Sluit dit tabblad.")
                event.set()
                return
            if state != expected_state:
                done["err"] = "State komt niet overeen (mogelijk verkeerde sessie)."
                self._ok_html("State mismatch. Sluit dit tabblad.")
                event.set()
                return
            done["code"] = code
            self._ok_html("OK — je mag dit tabblad sluiten en teruggaan naar de terminal.")
            event.set()

        def _ok_html(self, msg: str) -> None:
            body = f"""<!doctype html><meta charset="utf-8"><title>Saxo OAuth</title>
            <p style="font-family:system-ui">{msg}</p>""".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    try:
        server = HTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        return None, f"Kon niet luisteren op 127.0.0.1:{port} — {e}. Kies een andere poort in SAXO_REDIRECT_URI."

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if not event.wait(timeout=timeout):
        server.shutdown()
        return None, f"Timeout ({timeout}s) — geen callback ontvangen."
    server.shutdown()
    return done["code"], done["err"]


def parse_callback_url(full_url: str) -> tuple[str, str]:
    """
    Haal redirect_uri (zonder query) en authorization code uit een browser-URL.
    Alles na # (client-side router) wordt genegeerd.
    """
    s = full_url.strip().split("#", 1)[0].strip()
    if "?" not in s:
        raise ValueError("URL mist querystring (?code=...).")
    redirect_uri, _, query = s.partition("?")
    redirect_uri = redirect_uri.strip()
    if not (redirect_uri.startswith("https://") or redirect_uri.startswith("http://localhost") or redirect_uri.startswith("http://127.0.0.1")):
        raise ValueError("Verwacht https://… of http://localhost… / http://127.0.0.1… callback-URL.")
    qs = parse_qs(query)
    code = (qs.get("code") or [None])[0]
    if not code:
        raise ValueError("Geen code= in querystring.")
    return redirect_uri, unquote(code)


def manual_code() -> str:
    print()
    print("Plak de volledige redirect-URL uit de adresbalk (met ?code=...) of plak alleen de authorization code:")
    line = sys.stdin.readline().strip()
    if not line:
        return ""
    if "code=" in line:
        url = line
        if "://" not in url:
            url = "http://localhost" + (url if url.startswith("/") else "/" + url)
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        c = (qs.get("code") or [None])[0]
        if c:
            return unquote(c)
    return line.strip()


def write_refresh_and_print(
    *,
    tokens: dict,
    write_path: str,
    backend_root: Path,
) -> int:
    refresh = tokens.get("refresh_token")
    if not refresh or not isinstance(refresh, str):
        print(f"Onverwacht antwoord (geen refresh_token): {tokens}", file=sys.stderr)
        return 1

    out = Path(write_path)
    out.write_text(refresh, encoding="utf-8")
    print()
    print("Gelukt.")
    print()
    print(f"   Refresh token weggeschreven naar: {out.resolve()}")
    print()
    print("Zet in backend/.env en op Railway (SIM):")
    print("     SAXO_REFRESH_TOKEN=<dezelfde waarde>   (of SAXO_REFRESH_TOKEN_FILE)")
    print(f"     SAXO_REFRESH_TOKEN_FILE={out.resolve()}   (optioneel)")
    print()
    print("   SAXO_REDIRECT_URI moet exact overeenkomen met de callback die Saxo gebruikt,")
    print("   bijv. https://futures-theta.vercel.app/auth/saxo/callback")
    print()
    print("Herstart de API en test GET /api/dashboard")
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Saxo SIM OAuth — refresh token ophalen")
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Geen lokale server; plak zelf de code na browser-login",
    )
    parser.add_argument(
        "--exchange-url",
        metavar="URL",
        help="Volledige callback-URL (code in query; #fragment mag blijven staan). Voor Vercel e.d.",
    )
    parser.add_argument(
        "--exchange-code",
        metavar="CODE",
        help="Alleen de authorization code; gebruik samen met --redirect-uri of SAXO_REDIRECT_URI in .env",
    )
    parser.add_argument(
        "--redirect-uri",
        metavar="URI",
        help="Exact geregistreerde redirect URI (verplicht bij --exchange-code als die niet in .env staat)",
    )
    parser.add_argument("--timeout", type=int, default=600, help="Seconden wachten op callback (default 600)")
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parent.parent
    load_dotenv_file(backend_root / ".env")

    app_key = os.getenv("SAXO_APP_KEY", "").strip()
    app_secret = os.getenv("SAXO_APP_SECRET", "").strip()
    redirect_uri_env = os.getenv("SAXO_REDIRECT_URI", "").strip()
    auth_base = os.getenv("SAXO_AUTH_BASE_URL", SIM_AUTH).strip() or SIM_AUTH

    if not app_key or not app_secret:
        print("Ontbrekend: zet SAXO_APP_KEY en SAXO_APP_SECRET in backend/.env", file=sys.stderr)
        return 1

    write_path = os.getenv("SAXO_WRITE_REFRESH", "").strip() or str(backend_root / ".saxo_refresh")

    if args.exchange_url:
        try:
            redirect_uri, code = parse_callback_url(args.exchange_url)
        except ValueError as e:
            print(f"Ongeldige --exchange-url: {e}", file=sys.stderr)
            return 1
        print("Code wisselen voor tokens (redirect uit jouw URL) …")
        print(f"   redirect_uri: {redirect_uri}")
        try:
            tokens = exchange_code(auth_base, app_key, app_secret, redirect_uri, code)
        except httpx.HTTPStatusError as e:
            print(f"Token-endpoint fout: {e.response.status_code} {e.response.text[:800]}", file=sys.stderr)
            print(
                "Tip: redirect_uri in Saxo-app moet exact gelijk zijn; code is eenmalig — bij 'invalid_grant' opnieuw inloggen.",
                file=sys.stderr,
            )
            return 1
        except httpx.RequestError as e:
            print(f"Netwerkfout: {e}", file=sys.stderr)
            return 1
        return write_refresh_and_print(tokens=tokens, write_path=write_path, backend_root=backend_root)

    if args.exchange_code:
        redirect_uri = (args.redirect_uri or redirect_uri_env).strip()
        if not redirect_uri:
            print("Geef --redirect-uri of zet SAXO_REDIRECT_URI in backend/.env", file=sys.stderr)
            return 1
        code = args.exchange_code.strip()
        print("Code wisselen voor tokens …")
        try:
            tokens = exchange_code(auth_base, app_key, app_secret, redirect_uri, code)
        except httpx.HTTPStatusError as e:
            print(f"Token-endpoint fout: {e.response.status_code} {e.response.text[:800]}", file=sys.stderr)
            return 1
        except httpx.RequestError as e:
            print(f"Netwerkfout: {e}", file=sys.stderr)
            return 1
        return write_refresh_and_print(tokens=tokens, write_path=write_path, backend_root=backend_root)

    redirect_uri = redirect_uri_env
    if not redirect_uri:
        print("Ontbrekend: zet SAXO_REDIRECT_URI in backend/.env (of gebruik --exchange-url)", file=sys.stderr)
        return 1

    state = secrets.token_urlsafe(24)
    auth_params = urlencode(
        {
            "response_type": "code",
            "client_id": app_key,
            "state": state,
            "redirect_uri": redirect_uri,
        }
    )
    authorize_url = f"{auth_base.rstrip('/')}/authorize?{auth_params}"

    print()
    print("=== Saxo SIM — OAuth stap voor stap ===")
    print()
    print("1) Controleer op https://www.developer.saxo (SIM) dat je app exact deze redirect URI heeft:")
    print(f"   {redirect_uri}")
    print()
    print("2) Open deze URL in je browser (staat ook in je klembord als je op Enter drukt na start):")
    print()
    print("   ", authorize_url)
    print()

    code: str | None = None
    err: str | None = None

    if args.manual:
        code = manual_code()
        if not code:
            print("Geen code ingevoerd.", file=sys.stderr)
            return 1
    else:
        print(f"3) Lokale server luistert op je redirect URI (max {args.timeout}s) …")
        print("   Log in bij Saxo SIM en keur de app goed; je wordt teruggestuurd naar localhost.")
        print()
        try:
            webbrowser.open(authorize_url)
        except OSError:
            pass
        code, err = wait_for_callback(redirect_uri, state, args.timeout)
        if err:
            print(f"Callback-fout: {err}", file=sys.stderr)
            print("Tip: probeer --manual en plak de URL uit de adresbalk na redirect.", file=sys.stderr)
            return 1
        if not code:
            print("Geen code ontvangen.", file=sys.stderr)
            return 1

    print("4) Code wisselen voor tokens bij Saxo …")
    try:
        tokens = exchange_code(auth_base, app_key, app_secret, redirect_uri, code)
    except httpx.HTTPStatusError as e:
        print(f"Token-endpoint fout: {e.response.status_code} {e.response.text[:800]}", file=sys.stderr)
        return 1
    except httpx.RequestError as e:
        print(f"Netwerkfout: {e}", file=sys.stderr)
        return 1

    return write_refresh_and_print(tokens=tokens, write_path=write_path, backend_root=backend_root)


if __name__ == "__main__":
    raise SystemExit(main())
