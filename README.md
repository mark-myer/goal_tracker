# QuestLog (goal_tracker)

QuestLog is a FastAPI + SQLite goal-tracker app with quests, metrics, XP/leveling, webhook updates, Odoo integration, and SSE live updates.

## Prerequisites

- Python 3.11+ (3.12 tested)
- `pip`
- Linux/macOS shell (or equivalent on Windows)

## 1) Install

```bash
git clone https://github.com/mark-myer/goal_tracker.git
cd goal_tracker
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2) Configure environment

QuestLog reads configuration from environment variables:

- `DATABASE_URL` (optional)  
  Default: `sqlite:///./questlog.db`
- `ENCRYPTION_KEY` (recommended for persistent Odoo API key encryption)  
  Must be a valid Fernet key.

Generate a key:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Then export variables:

```bash
export ENCRYPTION_KEY='PASTE_YOUR_FERNET_KEY_HERE'
# optional override
export DATABASE_URL='sqlite:///./questlog.db'
```

## 3) Run locally

```bash
uvicorn questlog.main:app --host 0.0.0.0 --port 8000
```

Open:

- App/API root: `http://localhost:8000/`
- OpenAPI docs: `http://localhost:8000/docs`
- SSE stream: `http://localhost:8000/events`

## 4) Run tests

```bash
python -m pytest -q
```

## 5) Host in production

Use a process manager + reverse proxy. A common setup is **systemd + Nginx**.

### systemd service

Create `/etc/systemd/system/questlog.service`:

```ini
[Unit]
Description=QuestLog FastAPI service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/goal_tracker
Environment="ENCRYPTION_KEY=PASTE_YOUR_FERNET_KEY_HERE"
Environment="DATABASE_URL=sqlite:////opt/goal_tracker/questlog.db"
ExecStart=/opt/goal_tracker/.venv/bin/uvicorn questlog.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable/start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now questlog
sudo systemctl status questlog
```

### Nginx reverse proxy

Create `/etc/nginx/sites-available/questlog`:

```nginx
server {
    listen 80;
    server_name your-domain.example;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # important for SSE (/events)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/questlog /etc/nginx/sites-enabled/questlog
sudo nginx -t
sudo systemctl reload nginx
```

For HTTPS, add TLS via Let's Encrypt (`certbot`) or your standard ingress setup.

## Notes

- SQLite is simplest for single-user/small-team usage.
- Keep `ENCRYPTION_KEY` stable across restarts if you use Odoo connections; changing it prevents decrypting previously stored API keys.
