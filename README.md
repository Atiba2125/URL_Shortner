# URL Shortener (FastAPI + PostgreSQL + Nginx)

## Status

| Part | State |
|---|---|
| Shortener core (API, validation, short codes, DB, frontend) | Done |
| Nginx / systemd / SSL deploy config | Done (templates in `deploy/`) |
| Google "keep my domain in the address bar" proxy handler | **Not built - on hold** |

Short links currently do a normal `302` redirect to the original URL.

### Why the proxy is on hold
The brief asks to show Google's results page under the custom domain. That is
experimental (Google may block it) and carries impersonation/phishing-style risk,
plus possible Google terms issues. It should only be built after the client states the
real purpose and confirms it is permitted. If approved, build it as a limited POC:
GET-only, no cookie or credential passthrough, no account/login pages, result links
rewritten to go straight to the target sites.

## Run locally

```bash
python -m venv venv
venv\Scripts\activate          # Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000. With no `.env` it uses a local SQLite file; set
`DATABASE_URL` for PostgreSQL. Tests: `pytest`.

## API
- `POST /api/shorten` `{"url": "..."}` -> `{code, short_url, original_url}` (422 on invalid URL)
- `GET /{code}` -> 302 to the original URL (404 if unknown), increments `click_count`
- `GET /health`

## Deploy on Ubuntu VPS
1. `sudo apt install nginx postgresql python3-venv certbot python3-certbot-nginx`
2. Create DB + user: `sudo -u postgres createuser shortener -P && sudo -u postgres createdb -O shortener shortener`
3. Copy project to `/opt/shortener`, create venv, `pip install -r requirements.txt`, copy `.env.example` to `.env` and fill it in (`chmod 600`).
4. Install `deploy/shortener.service`, then `sudo systemctl enable --now shortener`.
5. Install `deploy/nginx-xyz.conf` (change the domain), point DNS A record at the VPS, run certbot.
6. Firewall: `sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable`.
7. Backups: nightly `pg_dump shortener | gzip > /var/backups/shortener-$(date +%F).sql.gz` via cron; keep logs under `/var/log/nginx/`.
