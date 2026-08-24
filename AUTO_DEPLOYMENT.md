# GitHub Actions Otomatik Deployment Kurulum Rehberi

## GitHub Secrets

Repository: **Settings → Secrets and variables → Actions**

| Secret | Value |
|---|---|
| `SSH_HOST` | `76.13.14.43` |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | Sunucudaki private key (aşağıya bakın) |

Private key sunucuda:

```bash
cat /root/.ssh/github_actions_deploy
```

Tam çıktıyı ( `-----BEGIN` … `-----END` dahil) `SSH_PRIVATE_KEY` secret'ına yapıştırın.

## Sunucu Yolları

| Alan | Path |
|---|---|
| Uygulama | `/srv/apps/nuviabutik` |
| Deploy script | `/srv/apps/nuviabutik/scripts/deploy.sh` |
| Data (media/logs) | `/srv/data/nuviabutik` |
| DB backups | `/srv/backups/nuviabutik/database/` |

## Nasıl Çalışır?

1. `main` branch'e push
2. GitHub Actions `deploy.yml` tetiklenir
3. SSH ile sunucuya bağlanır → `scripts/deploy.sh` çalışır:
   - `git pull`
   - `pip install`
   - `collectstatic`
   - `manage.py check`
   - `systemctl restart nuviabutik`

**Not:** Production'da migration çalıştırılmaz (planlı değilse).

## Manuel Deploy

```bash
/srv/apps/nuviabutik/scripts/deploy.sh
```

## Loglar

- Deploy: `/var/log/nuviabutik-deploy.log`
- Gunicorn: `journalctl -u nuviabutik -f`

## Rollback

```bash
cd /srv/apps/nuviabutik
git log --oneline -5
git reset --hard <commit>
/srv/apps/nuviabutik/scripts/deploy.sh
```

Database geri alma için: `/srv/backups/nuviabutik/database/` içindeki `.sql.gz` yedeklerini kullanın.
