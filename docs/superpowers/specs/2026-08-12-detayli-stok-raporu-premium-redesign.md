# Detaylı Stok Raporu - Premium Yeniden Tasarım

**Tarih:** 2026-08-12
**Durum:** Onay Bekliyor
**Yazar:** Cursor (brainstorming skill)

## Özet

Detaylı Stok Raporu sayfasının (`rapor:stok_raporu`) tamamen yeniden tasarlanması. Mevcut Bootstrap-tabanlı utility-class-heavy yapı, premium bir görsel dile (glassmorphism + gradient) ve modern dashboard düzenine dönüştürülecek. Üst kısımda 5 KPI kartı, ortada iki yan yana ApexCharts görselleştirmesi (Stok Sağlığı donut + Kâr Marjı Dağılımı bar), altta ana tablo yer alacak. Filtreler sol offcanvas sidebar'da toplanacak. Sayfa, mevcut rapor veri modelinin tamamını korur; ek veri sorgusu yok.

## Hedef

- Kullanıcı sayfayı açtığında **önce büyük resim** KPI'larla görsün, sonra detaylara insin.
- Tekrar eden / kullanılmayan UI elementleri çıkar.
- Premium his: cam efekti, gradient renkler, yumuşak animasyonlar.
- Modern etkileşim: ApexCharts, Bootstrap 5 Offcanvas/Collapse, sticky toolbar.

## Kapsam

### Dahil

- `templates/rapor/stok_raporu.html` komple yeniden yazılır (~400-500 satır).
- `static/css/stok-raporu.css` yeni oluşturulur (Premium stiller).
- `static/js/stok-raporu.js` yeni oluşturulur (chart logic, sidebar toggle, filter chips).
- `rapor/views.py` içindeki `stok_raporu` view'ına KPI özet agregaları eklenir.
- `rapor/views.py` içindeki `stok_excel` view'ı mevcut haliyle korunur (kullanıcı açıkça istemedi).

### Hariç

- Veritabanı şeması değişmez, migration yok.
- `Urun`, `UrunVaryanti` modellerinde değişiklik yok.
- Sidebar menüdeki bağlantı (`base.html`'deki "Detaylı Stok Raporu" linki) aynen kalır.
- Sidebar menünün kendisi kapsam dışıdır (sadece içeriğe filtre olarak offcanvas kullanılır).
- Dark mode toggle **kapsam dışı** (kullanıcı seçmedi).
- Responsive/içerik davranışı için Tailwind vb. framework **eklenmez**; mevcut Bootstrap 5 kullanılır.

## Mevcut Durum Analizi (Sorunlar)

| # | Sorun |
|---|-------|
| 1 | Tek tablo üzerinde çok yoğun bilgi; kullanıcı "büyük resmi" göremiyor. |
| 2 | "Bulunan Sonuç / Toplam Varyant / Kritik Stok / Tükenenler" kartları bilgi sunuyor ama **eylemi yönlendirmiyor**. |
| 3 | Satış değeri (₺), potansiyel kâr (₺) gibi hayati finansal veriler **görünmüyor**. |
| 4 | Tabloda filtre yok; tüm veri tek sayfada. |
| 5 | Görsel açıdan statik: utility class yoğunluğu, dağınık inline `<style>` ve `<script>`. |
| 6 | Stok sağlığı yüzdesel bir gösterge mevcut değil. |
| 7 | Kar marjı dağılımı görsel olarak görünmüyor. |

## Hedef Davranış

### Sayfa Yapısı (Yukarıdan Aşağıya)

```
1. Sticky Header Bar (sayfa üst)
   - Başlık (sol)
   - Aç/Kapa filtre sidebar butonu
   - Export Dropdown (sağ): Excel İndir | PDF İndir | Yazdır

2. KPI Şerit (5 kart yanyana, glass cards)
   - Kart 1: Toplam Varyant Sayısı
   - Kart 2: Stok Sağlık Skoru (% stoğu olan)
   - Kart 3: Toplam Stok Değeri (₺) — alis × stok
   - Kart 4: Toplam Potansiyel Kâr (₺) — (satis-alis) × stok
   - Kart 5: Ortalama Kâr Oranı (%)

3. İki Chart Yanyana (lg+ ekranda, md altta alta)
   - Sol: Stok Sağlığı Donut (Stoğu Olan / Kritik / Tükendi)
   - Sağ: Kâr Marjı Dağılımı Bar (0-20%, 20-40%, 40-60%, 60-80%, 80%+)

4. Ana Tablo
   - Sticky header
   - Sortable columns
   - Hover row glow
   - Tüm mevcut filtreler + sıralama korunur

5. Offcanvas Filtre Sidebar (Sol)
   - Buton ile açılır
   - Tüm filtre inputları burada
   - "Filtrele" ve "Temizle" CTA'lar altta sticky
```

### KPI Kart Detayları

Her kart ortalama `~200px` genişliğinde, `~110px` yüksekliğinde olacak.

#### Kart 1: Toplam Varyant
- **İkon:** `bi-boxes` (Bootstrap Icons), mavi gradient arka plan
- **Değer:** `{{ rows|length }}` formatlı (örn: 4.281)
- **Alt başlık:** "Filtrelenmiş sonuç" (eğer filtre varsa), "Toplam varyant" (yoksa)
- **Renk:** `--grad-blue` (indigo → mavi gradient)

#### Kart 2: Stok Sağlık Skoru
- **İkon:** `bi-heart-pulse`, yeşil gradient
- **Değer:** `{{ stok_saglik_skoru|floatformat:0 }}%` (stoğu olanların oranı)
- **Mini sparkline:** Son 7 günlük trend (eğer veri varsa; aksi halde gizli)
- **Renk:** `--grad-green` (zümrüt → yeşil)
- **Renk durumu:** Skor ≥80 → yeşil, 50-80 → sarı, <50 → kırmızı (badge)

#### Kart 3: Toplam Stok Değeri
- **İkon:** `bi-vault`, mor gradient
- **Değer:** `₺{{ toplam_stok_degeri|turkish_currency }}`
- **Alt başlık:** "Maliyet (₺)" — alis × stok toplamı
- **Renk:** `--grad-purple` (mor → indigo)

#### Kart 4: Toplam Potansiyel Kâr
- **İkon:** `bi-graph-up-arrow`, turuncu gradient
- **Değer:** `₺{{ toplam_potansiyel_kar|turkish_currency }}`
- **Alt başlık:** "Satış sonrası kâr"
- **Renk:** `--grad-orange` (turuncu → amber)

#### Kart 5: Ortalama Kâr Oranı
- **İkon:** `bi-percent`, pembe gradient
- **Değer:** `%{{ ortalama_kar_orani|floatformat:1 }}`
- **Alt başlık:** "Tüm satışlar için"
- **Renk:** `--grad-pink` (pembe → rose)

### KPI Hata Yönetimi

- Veri yoksa (0 varyant) kartlar "—" veya "Veri yok" gösterir.
- Hesaplamada hata oluşursa kart '—' gösterir ve küçük bir tooltip ile hata bildirir.

### Grafik Detayları (ApexCharts)

**Stok Sağlığı Donut:**
- 3 dilim: Stoğu Olan (yeşil `#10b981`), Kritik (sarı `#f59e0b`), Tükendi (kırmızı `#ef4444`)
- Merkezinde: Toplam varyant sayısı (`rows|length`)
- Legend: sağda, dikey
- Responsive yükseklik: `280px`
- ApexCharts `chart type="donut"`

**Kâr Marjı Dağılımı Bar:**
- 5 bar: 0-20%, 20-40%, 40-60%, 60-80%, 80%+
- Renk: gradient (her aralık farklı tonlama)
- Y-ekseni: varyant sayısı
- Hover: detaylı tooltip (ör. "40-60% aralığında 412 varyant, ₺25,800 toplam değer")
- ApexCharts `chart type="bar"`

### Filtre Sidebar (Bootstrap 5 Offcanvas)

- Sol taraftan `offcanvas-start` ile açılır.
- Tetikleyici buton: header'daki "Filtreler" butonu (kırmızı nokta ile aktif filtre sayısı).
- İçerik:
  - Arama input
  - Kategori select (Select2)
  - Marka select (Select2)
  - Stok Durumu segmented control (3 chip butonu: Hepsi / Stoğu Olan / Stoğu Biten)
  - Cinsiyet radio group
  - Kar Oranı Aralığı (Min/Max number input yan yana)
  - Sticky altta "Filtrele" (primary) + "Temizle" (outline) butonları

### Filtre Chip Toolbar (Sticky, Tablo Üstü)

- Aktif filtreler chip olarak görünür (örn: `[Kategori: Takım ×]`, `[Kar Oranı: 30-70 ×]`)
- Her chip'in sağında × butonu (filtreyi kaldırır)
- "Tümünü Temizle" linki (clearFilters)

### Ana Tablo İyileştirmeleri (Premium)

- Sticky `<thead>` (scroll sırasında yapışır)
- Zebra stripe (`:nth-child(even)` hafif gri)
- Hover row: glow efekti (subtle box-shadow)
- Sortable header'lar: ok ikonları + tıklama animasyonu
- "İşlemler" kolonunda hover ikonu ile hareketler link'i parlar
- Row'da "Kar Oranı" badge'i renk kodları: ≥50 yeşil, 30-50 sarı, 0-30 mavi, <0 kırmızı
- Mobil için responsive mode (overflow-x scroll mevcut haliyle)

## Tasarım Kararları

### 1. ApexCharts neden?
- Ücretsiz, açık kaynak, modern görünüm
- Bootstrap 5 ile uyumlu renkler
- CDN: `https://cdn.jsdelivr.net/npm/apexcharts` (mevcut CDN yapısıyla uyumlu)
- Alternatif: Chart.js (daha hafif ama ApexCharts daha "premium")

### 2. CSS dosyası neden ayrı?
- Mevcut `tokens.css`/`shell.css` ile uyumlu olacak şekilde `static/css/stok-raporu.css` yeni dosyası.
- Yeni dosya, sadece bu rapor için stil tanımlar; global token'lara saygı gösterir.
- `?v=20260812` cache-busting query eklenir.

### 3. JS dosyası neden ayrı?
- Chart init logic, sidebar toggle, chip yönetimi karmaşık; inline `<script>` artık yeterli değil.
- `static/js/stok-raporu.js` yeni dosyası.

### 4. CSS Variables / Theme
- Yeni dosya `tokens.css`'i override etmez.
- Kendi `--grad-blue`, `--grad-green` vb. CSS variables tanımlar.

### 5. Responsive Breakpoints
- `< md` (mobil): KPI'lar alt alta; tablo overflow-x-scroll; sidebar full-screen offcanvas
- `md - lg`: 2-3 KPI yan yana
- `≥ lg`: 5 KPI tek satır; 2 chart yan yana; sidebar 1/3 genişlik

### 6. Erişilebilirlik (a11y)
- ARIA labels (`aria-label`, `role`)
- Tablo için `<caption>`
- Renk körlüğü için sadece renge değil, etiketlere de güven
- Chart'larda metin alternatifi (screen reader için)

## Teknik Tasarım

### Backend (`rapor/views.py`)

`stok_raporu` view'ında yeni hesaplamalar:

```python
def stok_raporu(request):
    """Stok raporu view'ı - Premium tasarım"""
    from urun.models import UrunVaryanti, UrunKategoriUst, Marka
    from decimal import Decimal
    
    # ... mevcut filtre, sorgu, hesaplama kodu ...
    # `rows` listesi zaten mevcut implementasyonda var.
    
    # Yeni KPI agregaları
    toplam_stok_degeri = Decimal('0')
    toplam_potansiyel_kar = Decimal('0')
    kar_orani_toplam = Decimal('0')
    stok_olan_sayisi = 0
    kritik_sayisi = 0
    tukenmis_sayisi = 0
    
    for row in rows:
        v = row['varyant']
        alis = v.urun.alis_fiyati or Decimal('0')
        satis = v.urun.pesin_fiyat or Decimal('0')
        stok = v.stok_miktari or 0
        kar_tutari = row['kar_tutari']  # Decimal
        
        toplam_stok_degeri += alis * Decimal(stok)
        toplam_potansiyel_kar += kar_tutari * Decimal(stok)
        kar_orani_toplam += row['kar_orani']
        
        if stok == 0:
            tukenmis_sayisi += 1
        elif stok <= 5:
            kritik_sayisi += 1
        else:
            stok_olan_sayisi += 1
    
    toplam_varyant = len(rows)
    stok_olan_orani = (stok_olan_sayisi / toplam_varyant * 100) if toplam_varyant else 0
    ortalama_kar_orani = (kar_orani_toplam / Decimal(toplam_varyant)) if toplam_varyant else Decimal('0')
    
    # Kar marjı dağılımı
    kar_dagilimi = {
        '0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80+': 0,
    }
    for row in rows:
        oran = float(row['kar_orani'])
        if oran < 20: kar_dagilimi['0-20'] += 1
        elif oran < 40: kar_dagilimi['20-40'] += 1
        elif oran < 60: kar_dagilimi['40-60'] += 1
        elif oran < 80: kar_dagilimi['60-80'] += 1
        else: kar_dagilimi['80+'] += 1
    
    context = {
        # mevcut context
        'rows': rows,
        'kategoriler': kategoriler,
        'markalar': markalar,
        'arama': arama,
        'kategori_id': kategori_id,
        'marka_id': marka_id,
        'durum': durum,
        'cinsiyet': cinsiyet,
        'kar_orani_min': kar_orani_min,
        'kar_orani_max': kar_orani_max,
        'sort_field': ...,
        'sort_order': ...,
        
        # YENİ
        'toplam_varyant': toplam_varyant,
        'stok_olan_sayisi': stok_olan_sayisi,
        'kritik_sayisi': kritik_sayisi,
        'tukenmis_sayisi': tukenmis_sayisi,
        'stok_saglik_skoru': stok_olan_orani,
        'toplam_stok_degeri': toplam_stok_degeri,
        'toplam_potansiyel_kar': toplam_potansiyel_kar,
        'ortalama_kar_orani': ortalama_kar_orani,
        'kar_dagilimi': kar_dagilimi,  # dict for ApexCharts
    }
```

### Frontend

**`static/css/stok-raporu.css`** (~300-400 satır):
- Glass card mixin
- Gradient utility classes
- KPI card sizing/animations
- Sticky toolbar
- Table premium styling
- Hover effects
- Responsive breakpoints
- Color tokens

**`static/js/stok-raporu.js`** (~150-200 satır):
- ApexCharts init (2 chart)
- Bootstrap 5 Offcanvas init
- Filter chip management
- `clearFilters()` güncellemesi
- Sortable header animation
- Sidebar toggle

**`templates/rapor/stok_raporu.html`** (~400-500 satır):
- Sectioned structure
- Tüm mevcut filtre inputları
- KPI kart markup
- Chart containerlar (ApexCharts init JS tarafında)
- Tablo markup (mevcut kolonlar korunur)

### Statik Dosya Yönetimi

- `static/css/stok-raporu.css` ve `static/js/stok-raporu.js` dosyaları oluşturulur.
- `collectstatic` çalıştırılır → `staticfiles/` dizinine kopyalanır.
- Template'te `{% static 'css/stok-raporu.css' %}?v=20260812` ile yüklenir.
- Nginx servisi güncel dosyaları direkt serve eder.

### Eski `stok_raporu.html`'deki inline `<style>` ve `<script>`

- Inline bloklar **yeni `.css` ve `.js` dosyalarına taşınır.**
- Mevcut `clearFilters()` fonksiyonu yeni JS dosyasına taşınır (genişletilmiş haliyle).
- Eski `<style>` blokunda `bg-pink`, `bg-blue` tanımları varsa bunlar **korunmalı** (mevcut template kullanıyor).

## Etkilenen Dosyalar

| Dosya | İşlem |
|-------|-------|
| `templates/rapor/stok_raporu.html` | Komple yeniden yaz |
| `static/css/stok-raporu.css` | Yeni oluştur |
| `static/js/stok-raporu.js` | Yeni oluştur |
| `rapor/views.py` (`stok_raporu`) | KPI agregaları ekle |
| `staticfiles/` | collectstatic ile yenile |

## Test Senaryoları

| # | Senaryo | Beklenen |
|---|---------|----------|
| 1 | Sayfa yüklenir | KPI kartlar, 2 chart, tablo görünür |
| 2 | Stok Sağlığı donut render | 3 dilim + merkezde toplam |
| 3 | Kâr Marjı dağılımı bar render | 5 bar görünür |
| 4 | Filtre sidebar açılır | Offcanvas soldan açılır |
| 5 | Filtre uygula | Sidebar kapanır, KPI'lar günceller, tablo filtrelenir |
| 6 | Aktif filtre chip görünür | Chip toolbar'da görünür |
| 7 | Chip'den filtre kaldır | Filtre kalkar, sayfa yenilenir |
| 8 | Excel İndir çalışır | Mevcut Excel export etkilenmez |
| 9 | Tablo sıralama çalışır | Sıralama yönü değişir |
| 10 | Mobil görünüm | KPI'lar alt alta, sidebar full-screen |
| 11 | Negatif kâr durumu | Kâr Tut. kırmızı, Kar Oranı neg. badge |
| 12 | `clearFilters` tüm inputları temizler | Tüm 5 filtre sıfırlanır |

## Riskler ve Azaltımlar

| Risk | Azaltma |
|------|---------|
| ApexCharts CDN yüklenmezse chart boş kalır | CDN başarısız olursa mesaj göster, tablo yine çalışır |
| `collectstatic` unutulursa statik dosya eski | Spec'te açıkça listelendi; implementer adım sonunda çalıştırır |
| Inline JS hâlâ cached kalır | Yeni `stok-raporu.css/js` için `?v=20260812` query |
| Gunicorn template cache | Spec ilerleyen adımda gunicorn HUP sinyali gerektirebilir (kullanıcı daha önce karşılaştı) |
| Sidebar offcanvas yüksekliği (mobil) | `vh-100` ile sağlanır; test senaryosu 10 |

## Serbest Bırakma Planı

1. View'da KPI agregalarını ekle
2. Stok raporu view test
3. CSS dosyası oluştur
4. JS dosyası oluştur  
5. Template'i yeniden yaz
6. `python manage.py check`
7. `python manage.py collectstatic --noinput`
8. Smoke test (Django test client + curl)
9. Gunicorn HUP ile reload
10. Manuel browser test

## Açık Sorular / Varsayımlar

- **Excel export** şu anki haliyle kalır (kar oranı + kâr tutarı kolonları + 12 sütun). Yeni KPI'lar Excel'e eklenmez (Excel zaten raporunu kendi başına oluşturur).
- **Sparkline** (kart 2'de mini trend) ilk sürümde **yok** — veri yok. Kart 2'de sadece skor + badge olur. İleride eklenebilir.
- **Bulk select & action** tabloda **yok** (kullanıcı istemedi).
- **Dark mode** yok.
- **Mobile sidebar full-screen** davranışı için ek JS kontrolü şart (Bootstrap 5 offcanvas default olarak %100 destekler; ekstra test gerekmez).
- **Collectstatic** sonrası nginx reload gerekebilir, ama nginx genelde dosya sistemini otomatik serve eder.
