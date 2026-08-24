# Deploy (production)

## Prerequisites

- Python 3.11+ venv at `/var/www/nuviabutik/venv`
- PostgreSQL and Redis running
- `.env` populated (see `.env.example`) — **never commit `.env`**

Required when `DEBUG=False`:

- `SECRET_KEY`
- `DATABASE_URL`

## Update application code

```bash
cd /var/www/nuviabutik
git pull   # or rsync deploy artifact
source venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

**Do not run migrations** on production unless explicitly planned (this project phase avoids schema changes).

## Verify

```bash
set -a && source /var/www/nuviabutik/.env && set +a
sudo -u www-data env $(grep -v '^#' /var/www/nuviabutik/.env | xargs) \
  /var/www/nuviabutik/venv/bin/python /var/www/nuviabutik/manage.py check
```

## Restart

```bash
sudo systemctl restart nuviabutik.service
sudo systemctl status nuviabutik.service
```

## Smoke tests

See [docs/smoke_test_checklist.md](docs/smoke_test_checklist.md).

## Logs

- Checkout errors: `logs/checkout.log`
- Gunicorn: `journalctl -u nuviabutik.service -f`
