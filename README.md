# URL Shortener (FastAPI + PostgreSQL + Nginx)

## Status

| Part | State |
|---|---|
| Shortener core (API, validation, short codes, DB, frontend) | Done |
| Click counting + stats API (`GET /api/links/{code}`) + click counts in the UI | Done |
| Admin panel at `/admin` (login, search, edit, delete) and CLI tool (`python -m app.cli`) | Done |
| In-app rate limiting, friendly 404 page, edge-case tests (37 tests) | Done |
| PostgreSQL support, SQLite-to-PostgreSQL copy script | Done and tested locally |
| Nginx / systemd / SSL / backup / hardening templates | Done (in `deploy/`), not yet run on a real VPS |
| Google "keep my domain in the address bar" proxy handler | **Not built** |

Short links do a normal `302` redirect to the original URL, so the browser address
bar shows the destination site (e.g. google.com), not this domain.

### About the proxy / masking requirement
The briefs ask to show Google's results page under the custom domain (address bar masked,
original Google page rendered from the VPS, assets/redirects rewritten, cookies/scripts and
Search Console working). That part is intentionally **not built**: it presents Google's page
on another domain, is unreliable (Google blocks/CAPTCHAs proxied traffic), would route users'
Google cookies through this server, and Search Console attribution cannot be guaranteed. It
should only be reconsidered if the client states a legitimate purpose and confirms it is
allowed under Google's terms. Everything else in the scope (shortener, dashboard/CLI, admin
panel, rate limiting, error handling, edge-case tests, VPS/Nginx/SSL deployment) is covered.

## Run locally

```bash
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000. With no `.env` it uses a local SQLite file.

### Use PostgreSQL
1. Create a database: `CREATE DATABASE shortener;`
2. `copy .env.example .env` and set
   `DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/shortener`
   and `BASE_URL=http://localhost:8000`.
3. Start the app. Tables are created automatically.
4. Optional - copy old SQLite links across: `python -m scripts.migrate_sqlite_to_db shortener.db`

Tests: `pytest` (always uses a temporary SQLite database).

## Admin panel and CLI
**Admin panel:** set `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env` (empty password = panel disabled, returns 503), restart,
then open `/admin` and sign in. You can search links, see click totals, edit a link's destination, and delete links.
Use a long random password and HTTPS in production (HTTP Basic sends the password with every request).

**CLI** (on the server, no login needed):
```bash
python -m app.cli create "https://www.google.com/search?q=pizza"
python -m app.cli list --limit 20
python -m app.cli stats <code>
python -m app.cli edit <code> "https://new-destination"
python -m app.cli delete <code>
```
**Rate limit:** `RATE_LIMIT_PER_MINUTE` (default 30) caps link creation per IP; extra requests get `429`.

## API
- `POST /api/shorten` `{"url": "..."}` -> `{code, short_url, original_url}` (422 on invalid URL)
- `GET /api/links/{code}` -> `{code, short_url, original_url, click_count, created_at}` (404 if unknown)
- `GET /{code}` -> 302 to the original URL, increments `click_count` (HEAD requests are not counted)
- `GET /health`
- Interactive docs: `/api/docs`

## Deploy on Ubuntu VPS
1. `sudo apt install nginx postgresql python3-venv certbot python3-certbot-nginx`
2. Create DB + user: `sudo -u postgres createuser shortener -P && sudo -u postgres createdb -O shortener shortener`
3. Copy project to `/opt/shortener`, create venv, `pip install -r requirements.txt`, copy `.env.example` to `.env`, fill it in (`chmod 600`), set `BASE_URL` to the real https domain.
4. Install `deploy/shortener.service`, then `sudo systemctl enable --now shortener`.
5. Install `deploy/nginx-xyz.conf` (change the domain), point the DNS A record at the VPS, run `sudo certbot --nginx -d yourdomain.com`.
6. Security: review and run `deploy/harden.sh` (firewall, fail2ban, automatic updates).
7. Backups: install `deploy/backup.sh` (instructions at the top of the file) - nightly gzip dump, 14 days kept. Logs: `/var/log/nginx/` and `journalctl -u shortener`.
