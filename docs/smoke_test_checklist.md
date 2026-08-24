# NuviaButik smoke test checklist

Run after security or POS changes. Use a test user with cashier/satici role.

## Auth & CSRF

- [ ] `/kullanici/login/` loads; successful login redirects to dashboard
- [ ] Logged out: `/satis/` redirects to login (302)
- [ ] Logged out: `/gider/liste/` redirects to login (302)
- [ ] POST to `/satis/tamamla/` without CSRF token returns 403
- [ ] POST to `/satis/tamamla/` with `X-CSRFToken` header succeeds (with valid session)

## POS (satış ekranı)

- [ ] `/satis/` loads for authenticated user
- [ ] Barkod search returns product JSON
- [ ] Add to cart, complete sale with nakit — success JSON `{success: true}`
- [ ] Receipt print link opens `/satis/<id>/yazdir/`
- [ ] Session ping `/satis/ping/` returns `{success: true}`

## Broken pages (previously 500)

- [ ] `/satis/<id>/iptal/` — confirmation page (not 500)
- [ ] `/kullanici/profile/` — profile form
- [ ] `/kullanici/password-change/` — password form
- [ ] `/gider/<id>/duzenle/`, `/sil/`, `/detay/` — gider CRUD pages
- [ ] `/musteri/<id>/sil/` — delete confirm
- [ ] `/rapor/kar-zarar/` — kâr/zarar report (if linked)

## Tahsilat & labels

- [ ] Müşteri tahsilat list/add works for logged-in user
- [ ] Label API `/urun/api/getlabel/<id>/` requires login (401/302 when logged out)

## Deploy verification

```bash
set -a && source /var/www/nuviabutik/.env && set +a
sudo -u www-data env $(grep -v '^#' /var/www/nuviabutik/.env | xargs) \
  /var/www/nuviabutik/venv/bin/python /var/www/nuviabutik/manage.py check
sudo systemctl restart nuviabutik.service
```
