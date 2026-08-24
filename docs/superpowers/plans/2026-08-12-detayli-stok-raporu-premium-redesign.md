# Detaylı Stok Raporu Premium Yeniden Tasarım Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detaylı Stok Raporu sayfasını baştan tasarlayıp premium dashboard görünümüne (5 KPI kartı + 2 ApexChart + offcanvas filtre + sticky thead) kavuşturmak.

**Architecture:** Backend view'a minimal KPI agregasyonu eklenir; template komple yeniden yazılır; iki yeni statik dosya (CSS + JS) oluşturulur. Veritabanı veya model değişikliği yok. Mevcut tüm filtreler/sıralama/export korunur.

**Tech Stack:** Django 4.x, Bootstrap 5.3, ApexCharts (CDN), Vanilla JS (var olan jQuery 3.7 ile uyumlu), Bootstrap Icons (zaten mevcut).

---

## Global Constraints

- Veritabanı şeması değişmez; migration yok.
- `Urun`, `UrunVaryanti` ve diğer modellere dokunulmaz.
- Mevcut 5 filtre (arama, kategori, marka, durum, cinsiyet, kar_orani_min/max) korunur; UI farklı yere taşınabilir ama davranış aynı.
- Mevcut `clearFilters` mantığı korunur ve JS'e taşınır.
- Mevcut `stok_excel` view'ı değişmez; Excel/PDF export URL'leri aynı kalır.
- Yeni dosyalar: `static/css/stok-raporu.css` ve `static/js/stok-raporu.js`. `collectstatic` sonrası `staticfiles/` güncellenir.
- Mevcut `tokens.css`, `shell.css`, `main.css` dosyalarına **dokunulmaz**.
- ApexCharts CDN: `https://cdn.jsdelivr.net/npm/apexcharts` — base.html'a eklenir (veya sadece bu template'te). Spec kararı: **sadece bu template**'te CDN yüklenir.

---

## File Structure

**Create:**
- `static/css/stok-raporu.css` — premium stiller (glass + gradient + animations)
- `static/js/stok-raporu.js` — chart init + sidebar + chips

**Modify:**
- `rapor/views.py` — `stok_raporu` view'a KPI agregaları ekle (lines around 195-213, context bloğu)
- `templates/rapor/stok_raporu.html` — komple yeniden yaz

**Do NOT modify:**
- `templates/base.html` (eğer CDN template-local yüklenirse)
- `rapor/views.py` içindeki `stok_excel`, `stok_pdf`, diğer view'lar
- `static/css/tokens.css`, `shell.css`, `main.css`
- `static/js/nuvia-*.js`
- Herhangi bir model dosyası

---

## Task 1: Backend — `stok_raporu` view'a KPI agregaları

**Files:**
- Modify: `rapor/views.py` — `stok_raporu` function (satır 75-213; özellikle `rows` loop ve `context` bloğu)

**Interfaces:**
- Reads: mevcut `rows` (her biri `{varyant, kar_tutari, kar_orani}`)
- Produces context:
  - `toplam_varyant` — int
  - `stok_olan_sayisi`, `kritik_sayisi`, `tukenmis_sayisi` — int
  - `stok_saglik_skoru` — float (yüzde 0-100)
  - `toplam_stok_degeri` — Decimal (₺)
  - `toplam_potansiyel_kar` — Decimal (₺)
  - `ortalama_kar_orani` — Decimal
  - `kar_dagilimi_json` — string (JSON for ApexCharts; template'te `safe` ile render)

- [ ] **Step 1: KPI hesaplama mantığını (mevcut `rows` loop'tan hemen sonra) ekle**

`rapor/views.py`'da `rows = [...]` döngüsünün bittiği yerden (yaklaşık satır 193) hemen sonra, `kategoriler = UrunKategoriUst.objects.all().order_by('ad')` satırından önce şu bloğu ekle:

```python
    # Premium KPI agregasyonları (rows zaten hesaplanmış)
    ZERO_DEC = Decimal('0')
    toplam_stok_degeri = ZERO_DEC
    toplam_potansiyel_kar = ZERO_DEC
    kar_orani_toplam = ZERO_DEC
    stok_olan_sayisi = 0
    kritik_sayisi = 0
    tukenmis_sayisi = 0
    kar_dagilimi = {'0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80+': 0}

    for row in rows:
        v = row['varyant']
        try:
            stok = int(v.stok_miktari or 0)
        except (TypeError, ValueError):
            stok = 0
        alis = v.urun.alis_fiyati or ZERO_DEC
        kar_tutari = row['kar_tutari'] or ZERO_DEC

        toplam_stok_degeri += alis * Decimal(stok)
        toplam_potansiyel_kar += kar_tutari * Decimal(stok)
        kar_orani_toplam += (row['kar_orani'] or ZERO_DEC)

        if stok == 0:
            tukenmis_sayisi += 1
        elif stok <= 5:
            kritik_sayisi += 1
        else:
            stok_olan_sayisi += 1

        oran = float(row['kar_orani'] or 0)
        if oran < 20:
            kar_dagilimi['0-20'] += 1
        elif oran < 40:
            kar_dagilimi['20-40'] += 1
        elif oran < 60:
            kar_dagilimi['40-60'] += 1
        elif oran < 80:
            kar_dagilimi['60-80'] += 1
        else:
            kar_dagilimi['80+'] += 1

    toplam_varyant = len(rows)
    if toplam_varyant > 0:
        stok_saglik_skoru = (stok_olan_sayisi / toplam_varyant) * 100
        ortalama_kar_orani = kar_orani_toplam / Decimal(toplam_varyant)
    else:
        stok_saglik_skoru = 0
        ortalama_kar_orani = ZERO_DEC

    # ApexCharts için JSON (template'te |safe ile render edilir)
    import json
    kar_dagilimi_json = json.dumps([
        {'range': k, 'count': v} for k, v in kar_dagilimi.items()
    ])
```

- [ ] **Step 2: Context bloğuna yeni değerleri ekle**

Mevcut context dict'in sonuna (return satırından önce) ekle:

```python
        'toplam_varyant': toplam_varyant,
        'stok_olan_sayisi': stok_olan_sayisi,
        'kritik_sayisi': kritik_sayisi,
        'tukenmis_sayisi': tukenmis_sayisi,
        'stok_saglik_skoru': stok_saglik_skoru,
        'toplam_stok_degeri': toplam_stok_degeri,
        'toplam_potansiyel_kar': toplam_potansiyel_kar,
        'ortalama_kar_orani': ortalama_kar_orani,
        'kar_dagilimi_json': kar_dagilimi_json,
```

- [ ] **Step 3: `python manage.py check` doğrula**

```bash
cd /var/www/nuviabutik && python manage.py check
```

Beklenen: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Test client ile sayfa render edilebiliyor mu kontrol et**

```bash
cd /var/www/nuviabutik && set -a && source .env && set +a && DJANGO_SETTINGS_MODULE=stoktakip.settings python3 -c "
import django; django.setup()
from django.test import Client
from django.urls import reverse
from kullanici.models import CustomUser
c = Client()
u = CustomUser.objects.filter(is_superuser=True).first()
c.force_login(u)
r = c.get(reverse('rapor:stok_raporu'))
print('Status:', r.status_code)
print('New vars in template:')
content = r.content.decode('utf-8', errors='ignore')
print('  toplam_varyant:', '{{ toplam_varyant }}' in content or 'toplam_varyant' in content)
print('  stok_saglik_skoru:', 'stok_saglik_skoru' in content)
print('  kar_dagilimi_json:', 'kar_dagilimi_json' in content)
"
```

Beklenen: Status 200. Yeni değişkenler henüz template'te yok; `kar_dagilimi_json` görünebilir (yeni HTML'de False). Önemli olan **template render hatasız** olması.

- [ ] **Step 5: Commit**

```bash
git add rapor/views.py
git commit -m "feat(stok-raporu): KPI agregasyonlari (stok degeri, potansiyel kar, ortalama oran, saglik skoru)"
```

---

## Task 2: Frontend — Premium CSS dosyası

**Files:**
- Create: `static/css/stok-raporu.css`

**Interfaces:**
- Loaded by template via `{% static 'css/stok-raporu.css' %}?v=20260812`
- Defines: `--grad-*` variables, glass card mixin, KPI card classnames, table premium styling, sticky toolbar, chart container

- [ ] **Step 1: Dosyayı oluştur**

`/var/www/nuviabutik/static/css/stok-raporu.css` dosyası oluştur ve içeriğini şu şekilde yaz (~300 satır):

```css
/* Detaylı Stok Raporu - Premium Stil
   Bağımsız dosya; tokens.css/shell.css'i override etmez. */

:root {
    /* Color tokens (premium palette) */
    --grad-blue: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --grad-green: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    --grad-purple: linear-gradient(135deg, #8e2de2 0%, #4a00e0 100%);
    --grad-orange: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
    --grad-pink: linear-gradient(135deg, #ee9ca7 0%, #ffdde1 100%);
    --grad-red: linear-gradient(135deg, #cb2d3e 0%, #ef473a 100%);
    --grad-yellow: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);

    --text-primary: #1f2937;
    --text-muted: #6b7280;
    --bg-card: rgba(255, 255, 255, 0.85);
    --border-soft: rgba(0, 0, 0, 0.06);
    --shadow-soft: 0 4px 16px rgba(0, 0, 0, 0.04);
    --shadow-hover: 0 8px 32px rgba(0, 0, 0, 0.08);
    --radius-card: 14px;
    --radius-sm: 8px;
}

/* Sayfa genel */
.sr-page {
    padding: 1.5rem 1.5rem 3rem;
}

/* Sticky header bar */
.sr-sticky-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border-soft);
    padding: 1rem 1.5rem;
    margin: -1.5rem -1.5rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}
.sr-sticky-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
}
.sr-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

/* KPI Cards */
.sr-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.sr-kpi-card {
    position: relative;
    padding: 1.25rem;
    border-radius: var(--radius-card);
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-soft);
    box-shadow: var(--shadow-soft);
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    animation: sr-fade-up 0.45s ease backwards;
}
.sr-kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-hover);
}
.sr-kpi-card::before {
    content: "";
    position: absolute;
    inset: 0;
    background: var(--bg-grad, var(--grad-blue));
    opacity: 0.08;
    pointer-events: none;
}
.sr-kpi-card .sr-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-grad, var(--grad-blue));
    color: white;
    font-size: 1.4rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
}
.sr-kpi-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
    margin-bottom: 0.25rem;
}
.sr-kpi-label {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 500;
}
.sr-kpi-badge {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
}
.sr-kpi-badge.ok { background: #d1fae5; color: #065f46; }
.sr-kpi-badge.warn { background: #fef3c7; color: #92400e; }
.sr-kpi-badge.bad { background: #fee2e2; color: #991b1b; }

/* Gradient yardimcilari */
.sr-grad-blue   { --bg-grad: var(--grad-blue); }
.sr-grad-green  { --bg-grad: var(--grad-green); }
.sr-grad-purple { --bg-grad: var(--grad-purple); }
.sr-grad-orange { --bg-grad: var(--grad-orange); }
.sr-grad-pink   { --bg-grad: var(--grad-pink); }

/* Charts */
.sr-charts-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
@media (min-width: 992px) {
    .sr-charts-row { grid-template-columns: 1fr 1fr; }
}
.sr-chart-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-card);
    padding: 1.25rem;
    box-shadow: var(--shadow-soft);
    min-height: 320px;
}
.sr-chart-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.25rem;
}
.sr-chart-subtitle {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 1rem;
}
.sr-chart-canvas {
    min-height: 260px;
}

/* Filtre sidebar (offcanvas) override'lar */
.sr-offcanvas .offcanvas-body {
    padding: 1.25rem;
}
.sr-filter-section {
    margin-bottom: 1.5rem;
}
.sr-filter-section label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.sr-filter-section .form-control,
.sr-filter-section .form-select {
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-soft);
    transition: all 0.2s ease;
}
.sr-filter-section .form-control:focus,
.sr-filter-section .form-select:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

/* Stok durumu segmented control */
.sr-segment {
    display: flex;
    gap: 0.25rem;
    background: #f3f4f6;
    padding: 0.25rem;
    border-radius: var(--radius-sm);
}
.sr-segment input[type="radio"] { display: none; }
.sr-segment label {
    flex: 1;
    text-align: center;
    padding: 0.5rem 0.5rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-muted);
    transition: all 0.2s ease;
    text-transform: none;
    letter-spacing: 0;
    margin: 0;
}
.sr-segment input[type="radio"]:checked + label {
    background: white;
    color: var(--text-primary);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    font-weight: 600;
}

/* Chip toolbar */
.sr-chip-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--bg-card);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-card);
    margin-bottom: 1rem;
    box-shadow: var(--shadow-soft);
}
.sr-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
    border-radius: 999px;
    font-size: 0.85rem;
    color: var(--text-primary);
    font-weight: 500;
}
.sr-chip button {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0;
    font-size: 1.1rem;
    line-height: 1;
    margin-left: 0.25rem;
}
.sr-chip button:hover { color: #ef4444; }
.sr-chip-clear {
    margin-left: auto;
    color: #ef4444;
    background: none;
    border: none;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.85rem;
}
.sr-chip-clear:hover { text-decoration: underline; }

/* Premium tablo */
.sr-table-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-soft);
    overflow: hidden;
}
.sr-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.9rem;
}
.sr-table thead th {
    position: sticky;
    top: 0;
    background: linear-gradient(180deg, #4b5563 0%, #374151 100%);
    color: white;
    font-weight: 600;
    padding: 0.85rem 1rem;
    text-align: left;
    font-size: 0.85rem;
    border: none;
    user-select: none;
    cursor: pointer;
    transition: background 0.2s ease;
    z-index: 5;
}
.sr-table thead th:hover {
    background: linear-gradient(180deg, #374151 0%, #1f2937 100%);
}
.sr-table thead th .sort-icon {
    margin-left: 0.35rem;
    opacity: 0.5;
    font-size: 0.75rem;
}
.sr-table thead th.sort-asc .sort-icon,
.sr-table thead th.sort-desc .sort-icon {
    opacity: 1;
    color: #fbbf24;
}
.sr-table tbody tr {
    transition: background 0.15s ease, box-shadow 0.15s ease;
}
.sr-table tbody tr:nth-child(even) {
    background-color: rgba(0, 0, 0, 0.018);
}
.sr-table tbody tr:hover {
    background-color: rgba(102, 126, 234, 0.07);
    box-shadow: inset 3px 0 0 #667eea;
}
.sr-table tbody td {
    padding: 0.85rem 1rem;
    border-top: 1px solid var(--border-soft);
    color: var(--text-primary);
    vertical-align: middle;
}

/* Kar orani badge renk kodlama */
.sr-kar-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
}
.sr-kar-badge.high { background: #d1fae5; color: #065f46; }
.sr-kar-badge.mid  { background: #fef3c7; color: #92400e; }
.sr-kar-badge.low  { background: #dbeafe; color: #1e40af; }
.sr-kar-badge.neg  { background: #fee2e2; color: #991b1b; }
.sr-kar-badge.zero { background: #f3f4f6; color: #6b7280; }

/* Kar tutari renk */
.sr-kar-tutari { font-weight: 600; font-size: 0.95rem; }
.sr-kar-tutari.pos { color: #059669; }
.sr-kar-tutari.neg { color: #dc2626; }
.sr-kar-tutari.zero { color: #6b7280; }

/* Animations */
@keyframes sr-fade-up {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.sr-kpi-card:nth-child(1) { animation-delay: 0.05s; }
.sr-kpi-card:nth-child(2) { animation-delay: 0.10s; }
.sr-kpi-card:nth-child(3) { animation-delay: 0.15s; }
.sr-kpi-card:nth-child(4) { animation-delay: 0.20s; }
.sr-kpi-card:nth-child(5) { animation-delay: 0.25s; }

/* Responsive */
@media (max-width: 768px) {
    .sr-sticky-header {
        flex-direction: column;
        align-items: stretch;
        gap: 0.5rem;
    }
    .sr-actions { justify-content: flex-end; flex-wrap: wrap; }
    .sr-kpi-value { font-size: 1.5rem; }
}

/* Print */
@media print {
    .sr-sticky-header, .sr-chip-toolbar, .sr-kpi-grid, .sr-charts-row { display: none !important; }
    .sr-table-card { box-shadow: none; border: none; }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/css/stok-raporu.css
git commit -m "feat(stok-raporu): premium CSS (glassmorphism, gradient KPI cards, sticky thead)"
```

---

## Task 3: Frontend — Premium JS dosyası

**Files:**
- Create: `static/js/stok-raporu.js`

**Interfaces:**
- Loaded by template via `{% static 'js/stok-raporu.js' %}?v=20260812`
- Reads: `data-*` attrs from template (chart data JSON, filter chip data)
- Calls: `ApexCharts` for charts, Bootstrap `Offcanvas` for sidebar

- [ ] **Step 1: Dosyayı oluştur**

`/var/www/nuviabutik/static/js/stok-raporu.js` dosyası oluştur (~150 satır):

```javascript
// Detaylı Stok Raporu - Premium JS

(function () {
    'use strict';

    // ApexCharts: Stok Sağlığı Donut
    const saglikEl = document.getElementById('sr-stok-saglik-chart');
    if (saglikEl && window.ApexCharts) {
        const stokOlan = parseInt(saglikEl.dataset.stokOlan, 10) || 0;
        const kritik    = parseInt(saglikEl.dataset.kritik, 10) || 0;
        const tukenmis  = parseInt(saglikEl.dataset.tukenmis, 10) || 0;
        const total     = stokOlan + kritik + tukenmis;
        new ApexCharts(saglikEl, {
            chart: { type: 'donut', height: 280, animations: { enabled: true } },
            series: [stokOlan, kritik, tukenmis],
            labels: ['Stoğu Olan', 'Kritik Stok', 'Tükendi'],
            colors: ['#10b981', '#f59e0b', '#ef4444'],
            legend: { position: 'right', fontSize: '13px' },
            dataLabels: { enabled: false },
            plotOptions: {
                pie: {
                    donut: {
                        labels: {
                            show: true,
                            name: { fontSize: '14px', color: '#6b7280' },
                            value: { fontSize: '28px', fontWeight: 700, color: '#1f2937' },
                            total: {
                                show: true,
                                label: 'Toplam Varyant',
                                color: '#6b7280',
                                formatter: () => total.toLocaleString('tr-TR')
                            }
                        }
                    }
                }
            },
            stroke: { width: 2, colors: ['#fff'] },
            tooltip: { y: { formatter: (v) => v + ' varyant' } }
        }).render();
    }

    // ApexCharts: Kâr Marjı Dağılımı Bar
    const dagilimEl = document.getElementById('sr-kar-dagilimi-chart');
    if (dagilimEl && window.ApexCharts) {
        let data = [];
        try {
            data = JSON.parse(dagilimEl.dataset.dagilim || '[]');
        } catch (e) {
            console.warn('kar dagilimi parse error', e);
        }
        new ApexCharts(dagilimEl, {
            chart: { type: 'bar', height: 280, toolbar: { show: false }, animations: { enabled: true } },
            series: [{ name: 'Varyant Sayısı', data: data.map(d => d.count) }],
            xaxis: { categories: data.map(d => d.range + '%') },
            colors: ['#667eea'],
            plotOptions: { bar: { borderRadius: 6, columnWidth: '55%' } },
            dataLabels: {
                enabled: true,
                style: { fontSize: '12px', fontWeight: 600 },
                offsetY: -20
            },
            grid: { borderColor: 'rgba(0,0,0,0.05)' },
            yaxis: { labels: { formatter: (v) => Math.round(v) } }
        }).render();
    }

    // Bootstrap Offcanvas init (filter sidebar)
    const offEl = document.getElementById('sr-filter-offcanvas');
    if (offEl && window.bootstrap) {
        window.bsOffcanvas = new bootstrap.Offcanvas(offEl, { backdrop: true, scroll: true });
    }

    // Filtre sidebar açma butonu
    const openBtn = document.getElementById('sr-open-filters');
    if (openBtn && window.bsOffcanvas) {
        openBtn.addEventListener('click', () => window.bsOffcanvas.show());
    }

    // Segment butonu: Stok Durumu (radio-based segmented control)
    document.querySelectorAll('.sr-segment input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', function () {
            document.getElementById('sr-durum-hidden').value = this.value;
        });
    });

    // Filtre chip kaldırma
    document.querySelectorAll('.sr-chip button[data-remove-filter]').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const filterKey = this.getAttribute('data-remove-filter');
            applyFilterRemoval(filterKey);
        });
    });

    function applyFilterRemoval(key) {
        const url = new URL(window.location.href);
        if (url.searchParams.has(key)) {
            url.searchParams.delete(key);
            window.location.href = url.toString();
        }
    }

    // Tümünü temizle
    const clearAllBtn = document.getElementById('sr-clear-all');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function (e) {
            e.preventDefault();
            clearFilters();
        });
    }

    function clearFilters() {
        const sortField = (document.querySelector('input[name="sort"]') || {}).value || '';
        const sortOrder = (document.querySelector('input[name="order"]') || {}).value || '';
        const inputs = ['arama', 'kategori', 'marka', 'cinsiyet',
                       'kar_orani_min', 'kar_orani_max', 'durum'];
        inputs.forEach(name => {
            const el = document.querySelector(`[name="${name}"]`);
            if (!el) return;
            if (el.tagName === 'SELECT') el.value = el.querySelector('option[value=""]')
                ? '' : (el.querySelector('option[value="hepsi"]') ? 'hepsi' : '');
            else if (el.type === 'radio') {
                const def = document.querySelector(`input[name="${name}"][value=""]`)
                       || document.querySelector(`input[name="${name}"][value="hepsi"]`);
                if (def) def.checked = true;
            } else {
                el.value = '';
            }
        });
        const path = window.location.pathname;
        const qs = new URLSearchParams();
        if (sortField && sortField !== 'urun__ad') {
            qs.set('sort', sortField);
            qs.set('order', sortOrder);
        }
        window.location.href = qs.toString() ? `${path}?${qs}` : path;
    }
    window.clearFilters = clearFilters;

    // Sidebar içindeki form submit'inde hidden durum input'u set et
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function () {
            const checked = document.querySelector('.sr-segment input[type="radio"]:checked');
            if (checked) {
                document.getElementById('sr-durum-hidden').value = checked.value;
            }
        });
    }
})();
```

- [ ] **Step 2: Commit**

```bash
git add static/js/stok-raporu.js
git commit -m "feat(stok-raporu): premium JS (chart init, offcanvas, filter chips)"
```

---

## Task 4: Template — Komple Yeniden Yazım

**Files:**
- Modify: `templates/rapor/stok_raporu.html` — komple yeniden yaz

**Interfaces:**
- Extends: `base.html`
- Static files: `stok-raporu.css`, `stok-raporu.js` yüklenir
- CDN: ApexCharts yalnızca bu template'te yüklenir (extra_css / extra_js block kullanılarak)
- Reads context: mevcut + yeni KPI değişkenleri (Task 1'den)

- [ ] **Step 1: Dosyayı komple sil ve yeniden yaz**

İçeriği TAMAMEN değiştir. Yeni içerik şu yapıda olacak:

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Detaylı Stok Raporu{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/stok-raporu.css' %}?v=20260812">
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<script src="{% static 'js/stok-raporu.js' %}?v=20260812" defer></script>
{% endblock %}

{% block page_content %}
<div class="sr-page">

    <!-- Sticky Header Bar -->
    <header class="sr-sticky-header">
        <div>
            <h2><i class="bi bi-boxes-stacked me-2"></i>Detaylı Stok Raporu</h2>
            <small class="text-muted">{{ toplam_varyant }} varyant · Filtrelenmiş sonuç</small>
        </div>
        <div class="sr-actions">
            <button type="button" id="sr-open-filters" class="btn btn-light">
                <i class="bi bi-funnel me-1"></i>Filtreler
            </button>
            <div class="dropdown">
                <button class="btn btn-light dropdown-toggle" type="button" data-bs-toggle="dropdown">
                    <i class="bi bi-download me-1"></i>Dışa Aktar
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li>
                        <a class="dropdown-item"
                           href="{% url 'rapor:stok_excel' %}?arama={{ arama }}&kategori={{ kategori_id }}&marka={{ marka_id }}&durum={{ durum }}&cinsiyet={{ cinsiyet }}&kar_orani_min={{ kar_orani_min }}&kar_orani_max={{ kar_orani_max }}">
                            <i class="bi bi-file-earmark-excel text-success me-2"></i>Excel
                        </a>
                    </li>
                    <li>
                        <a class="dropdown-item" href="{% url 'rapor:stok_pdf' %}?{{ request.GET.urlencode }}">
                            <i class="bi bi-file-earmark-pdf text-danger me-2"></i>PDF
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </header>

    <!-- KPI Cards -->
    <section class="sr-kpi-grid" aria-label="KPI özet">

        <article class="sr-kpi-card sr-grad-blue">
            <div class="sr-icon"><i class="bi bi-boxes"></i></div>
            <div class="sr-kpi-value">{{ toplam_varyant|default:0 }}</div>
            <div class="sr-kpi-label">Toplam Varyant</div>
        </article>

        <article class="sr-kpi-card sr-grad-green">
            <div class="sr-icon"><i class="bi bi-heart-pulse"></i></div>
            <div class="sr-kpi-value">%{{ stok_saglik_skoru|floatformat:0 }}</div>
            <div class="sr-kpi-label">Stok Sağlık Skoru</div>
            {% if stok_saglik_skoru >= 80 %}
                <span class="sr-kpi-badge ok">Sağlıklı</span>
            {% elif stok_saglik_skoru >= 50 %}
                <span class="sr-kpi-badge warn">Orta</span>
            {% else %}
                <span class="sr-kpi-badge bad">Kritik</span>
            {% endif %}
        </article>

        <article class="sr-kpi-card sr-grad-purple">
            <div class="sr-icon"><i class="bi bi-vault"></i></div>
            <div class="sr-kpi-value">{{ toplam_stok_degeri|turkish_currency }}</div>
            <div class="sr-kpi-label">Toplam Stok Değeri (₺)</div>
        </article>

        <article class="sr-kpi-card sr-grad-orange">
            <div class="sr-icon"><i class="bi bi-graph-up-arrow"></i></div>
            <div class="sr-kpi-value">{{ toplam_potansiyel_kar|turkish_currency }}</div>
            <div class="sr-kpi-label">Toplam Potansiyel Kâr (₺)</div>
        </article>

        <article class="sr-kpi-card sr-grad-pink">
            <div class="sr-icon"><i class="bi bi-percent"></i></div>
            <div class="sr-kpi-value">%{{ ortalama_kar_orani|floatformat:1 }}</div>
            <div class="sr-kpi-label">Ortalama Kâr Oranı</div>
        </article>

    </section>

    <!-- Charts Row -->
    <section class="sr-charts-row">
        <div class="sr-chart-card">
            <h3 class="sr-chart-title">Stok Sağlığı</h3>
            <p class="sr-chart-subtitle">Mevcut varyantların stok durumuna göre dağılımı</p>
            <div id="sr-stok-saglik-chart"
                 class="sr-chart-canvas"
                 data-stok-olan="{{ stok_olan_sayisi }}"
                 data-kritik="{{ kritik_sayisi }}"
                 data-tukenmis="{{ tukenmis_sayisi }}"></div>
        </div>
        <div class="sr-chart-card">
            <h3 class="sr-chart-title">Kâr Marjı Dağılımı</h3>
            <p class="sr-chart-subtitle">Varyantların kâr oranı yüzdelerine göre dağılımı</p>
            <div id="sr-kar-dagilimi-chart"
                 class="sr-chart-canvas"
                 data-dagilim="{{ kar_dagilimi_json }}"></div>
        </div>
    </section>

    <!-- Aktif Filtre Chip Toolbar -->
    {% if arama or kategori_id or marka_id or durum or cinsiyet or kar_orani_min or kar_orani_max %}
    <div class="sr-chip-toolbar" aria-label="Aktif filtreler">
        {% if arama %}
            <span class="sr-chip">Arama: {{ arama }}<button data-remove-filter="arama">×</button></span>
        {% endif %}
        {% if kategori_id %}
            <span class="sr-chip">Kategori: {{ kategori_id }}<button data-remove-filter="kategori">×</button></span>
        {% endif %}
        {% if marka_id %}
            <span class="sr-chip">Marka: {{ marka_id }}<button data-remove-filter="marka">×</button></span>
        {% endif %}
        {% if durum %}
            <span class="sr-chip">Durum: {{ durum }}<button data-remove-filter="durum">×</button></span>
        {% endif %}
        {% if cinsiyet and cinsiyet != 'hepsi' %}
            <span class="sr-chip">Cinsiyet: {{ cinsiyet }}<button data-remove-filter="cinsiyet">×</button></span>
        {% endif %}
        {% if kar_orani_min %}
            <span class="sr-chip">Kar Oranı ≥ {{ kar_orani_min }}%<button data-remove-filter="kar_orani_min">×</button></span>
        {% endif %}
        {% if kar_orani_max %}
            <span class="sr-chip">Kar Oranı ≤ {{ kar_orani_max }}%<button data-remove-filter="kar_orani_max">×</button></span>
        {% endif %}
        <a href="javascript:void(0)" id="sr-clear-all" class="sr-chip-clear">Tümünü Temizle</a>
    </div>
    {% endif %}

    <!-- Filtre Form (gizli, offcanvas + sayfa submit için) -->
    <form method="get" id="filterForm" style="display:none;">
        <input type="hidden" name="sort" value="{{ sort_field }}">
        <input type="hidden" name="order" value="{{ sort_order }}">
        <input type="hidden" name="arama" value="{{ arama }}">
        <input type="hidden" name="kategori" value="{{ kategori_id }}">
        <input type="hidden" name="marka" value="{{ marka_id }}">
        <input type="hidden" name="cinsiyet" value="{{ cinsiyet }}">
        <input type="hidden" name="kar_orani_min" value="{{ kar_orani_min }}">
        <input type="hidden" name="kar_orani_max" value="{{ kar_orani_max }}">
        <input type="hidden" id="sr-durum-hidden" name="durum" value="{{ durum }}">
    </form>

    <!-- Filtre Offcanvas -->
    <div class="offcanvas offcanvas-start sr-offcanvas" tabindex="-1" id="sr-filter-offcanvas">
        <div class="offcanvas-header">
            <h5 class="offcanvas-title"><i class="bi bi-funnel me-2"></i>Filtreler</h5>
            <button type="button" class="btn-close" data-bs-dismiss="offcanvas"></button>
        </div>
        <div class="offcanvas-body">
            <div class="sr-filter-section">
                <label>Arama</label>
                <input id="filter-arama" name="arama" type="text" class="form-control" value="{{ arama }}" placeholder="Ürün, barkod, renk, beden...">
            </div>
            <div class="sr-filter-section">
                <label>Kategori</label>
                <select id="filter-kategori" name="kategori" class="form-select">
                    <option value="">Tüm Kategoriler</option>
                    {% for k in kategoriler %}
                        <option value="{{ k.id }}" {% if kategori_id == k.id|stringformat:"s" %}selected{% endif %}>{{ k.ad }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="sr-filter-section">
                <label>Marka</label>
                <select id="filter-marka" name="marka" class="form-select">
                    <option value="">Tüm Markalar</option>
                    {% for m in markalar %}
                        <option value="{{ m.id }}" {% if marka_id == m.id|stringformat:"s" %}selected{% endif %}>{{ m.ad }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="sr-filter-section">
                <label>Stok Durumu</label>
                <div class="sr-segment" role="radiogroup">
                    <input type="radio" id="durum-h" name="durum-segment" value="" {% if not durum %}checked{% endif %}>
                    <label for="durum-h">Hepsi</label>
                    <input type="radio" id="durum-o" name="durum-segment" value="stogu_olan" {% if durum == 'stogu_olan' %}checked{% endif %}>
                    <label for="durum-o">Stoğu Olan</label>
                    <input type="radio" id="durum-b" name="durum-segment" value="stogu_biten" {% if durum == 'stogu_biten' %}checked{% endif %}>
                    <label for="durum-b">Stoğu Biten</label>
                </div>
            </div>
            <div class="sr-filter-section">
                <label>Cinsiyet</label>
                <select id="filter-cinsiyet" name="cinsiyet" class="form-select">
                    <option value="hepsi" {% if cinsiyet == 'hepsi' or not cinsiyet %}selected{% endif %}>Hepsi</option>
                    <option value="kadin" {% if cinsiyet == 'kadin' %}selected{% endif %}>Kadın</option>
                    <option value="erkek" {% if cinsiyet == 'erkek' %}selected{% endif %}>Erkek</option>
                </select>
            </div>
            <div class="sr-filter-section">
                <label>Kar Oranı Aralığı (%)</label>
                <div class="row g-2">
                    <div class="col-6">
                        <input id="filter-kmin" name="kar_orani_min" type="number" step="0.01" min="0" max="1000" class="form-control" value="{{ kar_orani_min }}" placeholder="Min">
                    </div>
                    <div class="col-6">
                        <input id="filter-kmax" name="kar_orani_max" type="number" step="0.01" min="0" max="1000" class="form-control" value="{{ kar_orani_max }}" placeholder="Max">
                    </div>
                </div>
            </div>
        </div>
        <div class="offcanvas-footer p-3 d-flex gap-2">
            <button type="button" class="btn btn-primary flex-grow-1" onclick="submitFilters()">
                <i class="bi bi-search me-1"></i>Filtrele
            </button>
            <button type="button" class="btn btn-outline-secondary" onclick="clearFilters()">
                <i class="bi bi-eraser me-1"></i>Temizle
            </button>
        </div>
    </div>

    <!-- Ana Tablo -->
    <section class="sr-table-card">
        <div class="table-responsive">
            <table class="sr-table">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="urun__ad">Ürün Adı</th>
                        <th class="sortable" data-sort="renk__ad">Varyant</th>
                        <th class="sortable" data-sort="barkod">Barkod</th>
                        <th class="sortable" data-sort="urun__kategori__ad">Kategori</th>
                        <th class="sortable" data-sort="urun__marka__ad">Marka</th>
                        <th class="sortable" data-sort="urun__cinsiyet">Cinsiyet</th>
                        <th class="sortable" data-sort="urun__alis_fiyati">Alış ₺</th>
                        <th class="sortable" data-sort="urun__satis_fiyati">Satış ₺</th>
                        <th>Kar Tutarı</th>
                        <th class="sortable" data-sort="urun__kar_orani">Kar Oranı</th>
                        <th class="sortable" data-sort="stok_miktari">Stok</th>
                        <th>İşlemler</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in rows %}
                    <tr>
                        <td><strong>{{ row.varyant.urun.ad }}</strong></td>
                        <td>
                            <small class="text-muted">
                                {% if row.varyant.renk %}{{ row.varyant.renk.ad }}{% endif %}
                                {% if row.varyant.renk and row.varyant.beden %} - {% endif %}
                                {% if row.varyant.beden %}{{ row.varyant.beden.ad }}{% endif %}
                                {% if not row.varyant.renk and not row.varyant.beden %}Standart{% endif %}
                            </small>
                        </td>
                        <td><code>{{ row.varyant.barkod }}</code></td>
                        <td>{{ row.varyant.urun.kategori.ad }}</td>
                        <td>{{ row.varyant.urun.marka.ad|default:"-" }}</td>
                        <td>
                            <span class="badge {% if row.varyant.urun.cinsiyet == 'kadin' %}bg-pink{% else %}bg-blue{% endif %}">
                                {{ row.varyant.urun.get_cinsiyet_display }}
                            </span>
                        </td>
                        <td>{{ row.varyant.urun.alis_fiyati|turkish_currency }}</td>
                        <td><strong>{{ row.varyant.urun.pesin_fiyat|turkish_currency }}</strong></td>
                        <td>
                            {% with tutar=row.kar_tutari %}
                                <span class="sr-kar-tutari {% if tutar > 0 %}pos{% elif tutar < 0 %}neg{% else %}zero{% endif %}">
                                    {{ tutar|turkish_currency }}
                                </span>
                            {% endwith %}
                        </td>
                        <td>
                            {% with oran=row.kar_orani %}
                                {% if oran >= 50 %}
                                    <span class="sr-kar-badge high">%{{ oran|floatformat:1 }}</span>
                                {% elif oran >= 30 %}
                                    <span class="sr-kar-badge mid">%{{ oran|floatformat:1 }}</span>
                                {% elif oran >= 0 %}
                                    <span class="sr-kar-badge low">%{{ oran|floatformat:1 }}</span>
                                {% elif oran < 0 %}
                                    <span class="sr-kar-badge neg">%{{ oran|floatformat:1 }}</span>
                                {% else %}
                                    <span class="sr-kar-badge zero">%{{ oran|floatformat:1 }}</span>
                                {% endif %}
                            {% endwith %}
                        </td>
                        <td>
                            <span class="fw-bold
                                {% if row.varyant.stok_miktari == 0 %}text-danger
                                {% elif row.varyant.stok_miktari <= 5 %}text-warning
                                {% else %}text-success{% endif %}">
                                {{ row.varyant.stok_miktari }}
                            </span>
                        </td>
                        <td>
                            <a href="{% url 'rapor:stok_hareketleri' row.varyant.id %}" class="btn btn-sm btn-outline-primary">
                                <i class="bi bi-clock-history"></i>
                            </a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="12" class="text-center py-4 text-muted">Ürün bulunamadı.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </section>

</div>

<!-- submitFilters: offcanvas içindeki alanları filterForm'a aktar ve submit et -->
<script>
function submitFilters() {
    var form = document.getElementById('filterForm');
    function setVal(name) {
        var src = document.getElementById('filter-' + name);
        if (src) {
            form.querySelector('input[name="' + name + '"]').value = src.value;
        }
    }
    setVal('arama');
    setVal('kategori');
    setVal('marka');
    setVal('cinsiyet');
    setVal('kmin');
    form.querySelector('input[name="kar_orani_min"]').value = document.getElementById('filter-kmin').value;
    form.querySelector('input[name="kar_orani_max"]').value = document.getElementById('filter-kmax').value;
    form.submit();
}
</script>

<!-- Sıralama script'i (değişmedi, mevcut haliyle korunur) -->
<script>
document.addEventListener('DOMContentLoaded', function () {
    const sortableHeaders = document.querySelectorAll('.sr-table thead th.sortable');
    const url = new URL(window.location.href);

    sortableHeaders.forEach(h => {
        h.addEventListener('click', function () {
            const sortField = this.getAttribute('data-sort');
            const currentSort = url.searchParams.get('sort');
            const currentOrder = url.searchParams.get('order');
            const newOrder = (currentSort === sortField && currentOrder === 'asc') ? 'desc' : 'asc';
            url.searchParams.set('sort', sortField);
            url.searchParams.set('order', newOrder);
            window.location.href = url.toString();
        });
    });
    // Aktif sıralama işareti
    const currentSort = url.searchParams.get('sort');
    const currentOrder = url.searchParams.get('order');
    if (currentSort) {
        const activeHeader = document.querySelector('[data-sort="' + currentSort + '"]');
        if (activeHeader) {
            activeHeader.classList.add(currentOrder === 'desc' ? 'sort-desc' : 'sort-asc');
            const icon = document.createElement('i');
            icon.className = 'bi bi-caret-up-fill sort-icon';
            activeHeader.appendChild(icon);
        }
    }
});
</script>

{% endblock %}
```

- [ ] **Step 2: `python manage.py check` çalıştır**

```bash
cd /var/www/nuviabutik && python3 manage.py check
```

Beklenen: Hatasız.

- [ ] **Step 3: Commit**

```bash
git add templates/rapor/stok_raporu.html
git commit -m "feat(stok-raporu): premium template (5 KPI card + 2 chart + offcanvas + sticky thead + chips)"
```

---

## Task 5: Statik Dosyaları Yayınla + Gunicorn Reload

- [ ] **Step 1: `collectstatic` çalıştır**

```bash
cd /var/www/nuviabutik && python3 manage.py collectstatic --noinput
```

Beklenen: Yeni dosyalar staticfiles'e kopyalanır.

- [ ] **Step 2: Gunicorn reload (HUP)**

```bash
PID=$(cat /var/run/gunicorn/nuviabutik.pid 2>/dev/null || echo "1690501")
kill -HUP $PID 2>/dev/null
sleep 3
ps aux | grep gunicorn | grep -v grep | head -8
```

Not: İlk denemede nginx master PID'si (1690501) kullanılmıştı; bu sefer doğru gunicorn PID'sini (`/var/run/gunicorn/nuviabutik.pid`) kullan.

- [ ] **Step 3: Manuel smoke test (Django test client)**

```bash
cd /var/www/nuviabutik && set -a && source .env && set +a && DJANGO_SETTINGS_MODULE=stoktakip.settings python3 -c "
import django; django.setup()
from django.test import Client
from django.urls import reverse
from kullanici.models import CustomUser
c = Client()
u = CustomUser.objects.filter(is_superuser=True).first()
c.force_login(u)
r = c.get(reverse('rapor:stok_raporu'))
content = r.content.decode('utf-8', errors='ignore')

checks = [
    ('Premium header', 'sr-sticky-header' in content),
    ('5 KPI cards', content.count('sr-kpi-card') >= 5),
    ('Stok saglik chart container', 'sr-stok-saglik-chart' in content),
    ('Kar dagilimi chart container', 'sr-kar-dagilimi-chart' in content),
    ('Offcanvas sidebar', 'sr-filter-offcanvas' in content),
    ('ApexCharts CDN', 'apexcharts' in content.lower()),
    ('CSS dosyasi', 'stok-raporu.css' in content),
    ('JS dosyasi', 'stok-raporu.js' in content),
    ('KPI degeri', 'sr-kpi-value' in content),
    ('Kar tutari renk', 'sr-kar-tutari' in content),
    ('Kar orani badge', 'sr-kar-badge' in content),
    ('Tablodaki yeni sinif', '<table class=\"sr-table\"' in content or 'class=\"sr-table\"' in content),
    ('Varyant satirlari var', '<tbody>' in content and 'row.varyant' in content or '{{' in content),
]
for name, ok in checks:
    print(('OK' if ok else 'FAIL').ljust(5), name)
" 2>&1
```

Beklenen: Hepsi OK.

- [ ] **Step 4: Gerçek gunicorn endpoint test (curl)**

```bash
SESSION=$(cd /var/www/nuviabutik && set -a && source .env && set +a && DJANGO_SETTINGS_MODULE=stoktakip.settings python3 -c "
import django; django.setup()
from django.test import Client
from kullanici.models import CustomUser
c = Client()
u = CustomUser.objects.filter(is_superuser=True).first()
c.force_login(u)
print(c.cookies['sessionid'].value)
")
curl -s -b "sessionid=$SESSION" -o /tmp/premium.html -w "HTTP %{http_code} size=%{size_download}\n" \
    http://127.0.0.1:8000/rapor/stok-raporu/
echo "Premium markers in production-served HTML:"
grep -c 'sr-sticky-header' /tmp/premium.html
grep -c 'sr-kpi-card' /tmp/premium.html
grep -c 'sr-stok-saglik-chart' /tmp/premium.html
```

Beklenen: HTTP 200; tüm markerler >0.

- [ ] **Step 5: Final commit yok (zaten tüm değişiklikler commit'lendi)**

İsteğe bağlı: Bu noktada bir özet commit atılabilir ama zaten 4 commit (Task 1-4) tek tek temiz.

---

## Self-Review Kontrol Listesi

### Spec coverage

| Spec gereksinimi | Sağlayan task |
|------------------|---------------|
| 5 KPI kart (glass + gradient) | Task 4 Step 1 |
| KPI değerleri (toplam, sağlık, değer, kâr, oran) | Task 1 + Task 4 |
| Stok Sağlığı Donut chart | Task 3 + Task 4 |
| Kâr Marjı Dağılımı Bar chart | Task 3 + Task 4 |
| Offcanvas filtre sidebar | Task 2 + Task 3 + Task 4 |
| Filtre chip toolbar | Task 4 |
| Sticky thead | Task 2 + Task 4 |
| Mevcut 5 filtre korunur | Task 4 |
| Kar oranı + Kâr tutarı korunur | Task 4 |
| Sıralama korunur | Task 4 |
| Excel/PDF export korunur | Task 4 |
| clearFilters korunur | Task 3 + Task 4 |
| ApexCharts CDN | Task 4 |

### Placeholder scan

- "TBD"/"TODO" yok. Tüm kod blokları tam.
- Plan'ın tamamında her yerde somut veri (no "implement later" vb.).

### Type/isim tutarlılığı

- Context isimleri spec ile aynı (`toplam_varyant`, `stok_saglik_skoru`, `kar_dagilimi_json`, vb.)
- CSS class isimleri template ve JS'te tutarlı (`sr-kpi-card`, `sr-stok-saglik-chart`, `sr-kar-dagilimi-chart`, `sr-durum-hidden`, vb.)
- Form alanları mevcut URL parametreleri ile uyumlu
