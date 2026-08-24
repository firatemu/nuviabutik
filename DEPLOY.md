# Deploy (production)

## Prerequisites

- Python 3.12+ venv at `/srv/apps/nuviabutik/venv`
- PostgreSQL and Redis running
- `.env` populated (see `.env.example`) — **never commit `.env`**

Required when `DEBUG=False`:

- `SECRET_KEY`
- `DATABASE_URL`
- `NUVIABUTIK_DATA_DIR=/srv/data/nuviabutik`

## Update application code

```bash
/srv/apps/nuviabutik/scripts/deploy.sh
```

Or manually:

```bash
cd /srv/apps/nuviabutik
git pull
source venv/bin/activate
pip install -r requirements.txt python-barcode==0.16.1 hiredis==3.3.0
python manage.py collectstatic --noinput
```

**Do not run migrations** on production unless explicitly planned.

## Verify

```bash
set -a && source /srv/apps/nuviabutik/.env && set +a
sudo -u www-data env $(grep -v '^#' /srv/apps/nuviabutik/.env | xargs) \
  /srv/apps/nuviabutik/venv/bin/python /srv/apps/nuviabutik/manage.py check
```

## Restart

```bash
sudo systemctl restart nuviabutik.service
sudo systemctl status nuviabutik.service
```

## Smoke tests

See [docs/smoke_test_checklist.md](docs/smoke_test_checklist.md).

## Logs

- App logs: `/srv/data/nuviabutik/logs/`
- Gunicorn: `journalctl -u nuviabutik.service -f`
- Deploy: `/var/log/nuviabutik-deploy.log`
