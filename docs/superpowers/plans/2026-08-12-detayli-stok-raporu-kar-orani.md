# Detaylı Stok Raporu - Kar Oranı ve Filtre İyileştirmesi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detaylı Stok Raporu sayfasında kar oranını alış/satış fiyatlarına göre dinamik olarak hesaplamak, kâr tutarı kolonu eklemek, stok durumu filtresini 3 seçeneğe indirmek ve kar oranı aralık filtresi eklemek.

**Architecture:** Backend tarafında (Django view) her varyant için kâr tutarı ve kâr oranı hesaplanır, template'e sözlük listesi olarak geçirilir. Kar oranı aralık filtresi Python view katmanında uygulanır. Stok durumu filtresi Django ORM ile uygulanır. Frontend'de filtre inputları + yeni tablo kolonları eklenir; sıralama davranışı mevcut haliyle kalır.

**Tech Stack:** Django 4.x, PostgreSQL, jinja-style Django template, Vanilla JS, Bootstrap 5 (sınıflar mevcut).

---

## Global Constraints

- Veritabanı şeması değiştirilmez; migration yapılmaz.
- `Urun.kar_orani` alanı başka raporlarda kullanılıyor olabilir; bu görev kapsamında dokunulmaz.
- `Urun.pesin_fiyat` aktif satış fiyatıdır; `satis_fiyati` onun alias'ıdır (`save()` içinde eşitlenir). Hesaplamalarda `pesin_fiyat` kullanılır.
- Kar oranı formülü: `oran = (satis - alis) / satis * 100`. `satis == 0` ise oran `0.0` döner (DivisionByZero yok).
- Kar oranı filtre inputları opsiyoneldir; boş bırakılırsa filtre uygulanmaz. Geçersiz sayılar yok sayılır.
- Yeni parametre isimleri: `kar_orani_min`, `kar_orani_max`. Stok durumu yeni değerleri: `stogu_olan` (`>0`), `stogu_biten` (`=0`). Boş=`''` Hepsi.

---

## File Structure

**Modify:**
- `rapor/views.py` — `stok_raporu` ve `stok_excel` view fonksiyonları (kar oranı hesaplama, Python tarafı filtreleme, satır verisi sözlükleri, Excel'de yeni sütun)
- `templates/rapor/stok_raporu.html` — Form inputları, hızlı filtre butonları, tablo kolonları, `clearFilters` JS

**Read (no change):** Veritabanı modelleri (`urun/models.py`), diğer rapor view'ları (`stok_degeri`, `urun_bazli_karlilik`).

---

## Task 1: Backend - `stok_raporu` view'ında kar oranı hesaplama ve Python tarafı filtre

**Files:**
- Modify: `rapor/views.py:75-160` (`stok_raporu` fonksiyonunun tamamı)
- Test: Manuel olarak Django runserver üzerinden sayfa yüklenerek

**Interfaces:**
- Reads from: `UrunVaryanti.aktif=True, urun__aktif=True` (mevcut query'ye ek select_related)
- Produces context:
  - `rows` — `list[dict]` (her biri: `{varyant, kar_tutari: Decimal, kar_orani: Decimal}`)
  - `arama`, `kategori_id`, `marka_id`, `durum`, `cinsiyet`, `sort_field`, `sort_order` — mevcut
  - Yeni: `kar_orani_min`, `kar_orani_max` — yüzde değerleri (string), template'te input value olarak kullanılır

- [ ] **Step 1: Yeni parametreler + Decimal import + try/except ekle**

`rapor/views.py` dosyasının en üstündeki import'lara `Decimal` ekle:

```python
from decimal import Decimal
```

`stok_raporu` fonksiyonunun başında, `cinsiyet` satırından hemen sonra:

```python
        kar_orani_min = request.GET.get('kar_orani_min', '').strip()
        kar_orani_max = request.GET.get('kar_orani_max', '').strip()
```

- [ ] **Step 2: Stok durumu filtresini yeni 3 seçeneğe güncelle**

Mevcut 4'lü `if/elif` blokunu değiştir:

```python
        # Stok durumu filtresi - Yeni 3 seçenek: Hepsi / Stoğu Olan / Stoğu Biten
        if durum == 'stogu_olan':
            varyantlar = varyantlar.filter(stok_miktari__gt=0)
        elif durum == 'stogu_biten':
            varyantlar = varyantlar.filter(stok_miktari=0)
        # '' (boş) veya yok → tümü
```

- [ ] **Step 3: Hesaplama + filtre listesi oluşturma**

`varyantlar = varyantlar.order_by(...)` satırından sonra, `kategoriler` satırından önce şu bloğu ekle:

```python
        # Filtrelenmiş varyantları listeye çevir (Python tarafı kar oranı hesaplaması için)
        varyant_list = list(varyantlar)

        # Kar oranı aralık filtresi - Python tarafında uygulanır
        min_val = None
        max_val = None
        try:
            if kar_orani_min:
                min_val = float(kar_orani_min)
        except (ValueError, TypeError):
            min_val = None
        try:
            if kar_orani_max:
                max_val = float(kar_orani_max)
        except (ValueError, TypeError):
            max_val = None

        def _passes_kar(v):
            alis = v.urun.alis_fiyati or Decimal('0')
            satis = v.urun.pesin_fiyat or Decimal('0')
            if satis != 0:
                oran = float((satis - alis) / satis * Decimal('100'))
            else:
                oran = 0.0
            if min_val is not None and oran < min_val:
                return False
            if max_val is not None and oran > max_val:
                return False
            return True

        if min_val is not None or max_val is not None:
            varyant_list = [v for v in varyant_list if _passes_kar(v)]
```

- [ ] **Step 4: Hesaplanmış satır listesi (rows) oluştur ve context'e ekle**

`varyant_list = ...` filtresinin HEMEN ARDINDAN:

```python
        # Her varyant için kar tutarı ve kar oranı hesapla (template'e hazır dict)
        ZERO = Decimal('0')
        rows = []
        for v in varyant_list:
            alis = v.urun.alis_fiyati or ZERO
            satis = v.urun.pesin_fiyat or ZERO
            kar_tutari = satis - alis
            if satis != 0:
                kar_orani = (kar_tutari / satis) * Decimal('100')
            else:
                kar_orani = ZERO
            rows.append({
                'varyant': v,
                'kar_tutari': kar_tutari,
                'kar_orani': kar_orani,
            })
```

- [ ] **Step 5: Context'i güncelle - `varyantlar` yerine `rows` + yeni parametreler**

Mevcut context bloğunu şu şekilde değiştir:

```python
        context = {
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
            'sort_field': request.GET.get('sort', 'urun__ad'),
            'sort_order': request.GET.get('order', 'asc'),
        }
```

- [ ] **Step 6: Manuel doğrulama — `python manage.py check` çalıştır**

```bash
cd /var/www/nuviabutik && python manage.py check
```

Beklenen: `System check identified no issues (0 silenced).` veya benzeri başarı mesajı.

- [ ] **Step 7: Commit (yok; tüm değişiklikler tek commit'te)**

Bu task tek commit olarak Task 3'ün sonunda (veya isteğe bağlı ara commit).

---

## Task 2: Backend - `stok_excel` view'ında yeni parametreler + dinamik kar oranı

**Files:**
- Modify: `rapor/views.py:788-893` (`stok_excel` fonksiyonunun tamamı)

**Interfaces:**
- Reads: `request.GET` — aynı parametreler (`arama, kategori, marka, durum, cinsiyet`) + yeni `kar_orani_min, kar_orani_max`
- Produces: Excel response; kolon 9 (Kar Oranı %) dinamik; yeni **kolon 10 (Kâr Tutarı)** eklenir; mevcut kolonlar 1-8, 11-12

- [ ] **Step 1: Yeni parametreleri oku**

Mevcut `cinsiyet = request.GET.get('cinsiyet')` satırından hemen sonra:

```python
        kar_orani_min = request.GET.get('kar_orani_min', '').strip()
        kar_orani_max = request.GET.get('kar_orani_max', '').strip()
```

- [ ] **Step 2: Stok durumu filtresini güncelle**

Mevcut `if durum == 'tukendi' ... elif ... elif ... normal` blokunu şu şekilde değiştir:

```python
        # Stok durumu filtresi - Yeni 3 seçenek
        if durum and durum != 'None' and durum != '':
            if durum == 'stogu_olan':
                varyantlar = varyantlar.filter(stok_miktari__gt=0)
            elif durum == 'stogu_biten':
                varyantlar = varyantlar.filter(stok_miktari=0)
```

- [ ] **Step 3: Kar oranı Python tarafı filtreleme uygula**

Cinsiyet filtresinden hemen sonra, `except (ValueError, TypeError)` satırından önce:

```python
        # Kar oranı filtre - Python tarafı
        varyant_list = list(varyantlar)
        min_val = None
        max_val = None
        try:
            if kar_orani_min:
                min_val = float(kar_orani_min)
        except (ValueError, TypeError):
            pass
        try:
            if kar_orani_max:
                max_val = float(kar_orani_max)
        except (ValueError, TypeError):
            pass

        if min_val is not None or max_val is not None:
            from decimal import Decimal as _D
            filtered = []
            for v in varyant_list:
                alis = v.urun.alis_fiyati or _D('0')
                satis = v.urun.pesin_fiyat or _D('0')
                if satis != 0:
                    oran = float((satis - alis) / satis * _D('100'))
                else:
                    oran = 0.0
                if min_val is not None and oran < min_val:
                    continue
                if max_val is not None and oran > max_val:
                    continue
                filtered.append(v)
            varyantlar = filtered
        else:
            varyantlar = varyant_list
```

- [ ] **Step 4: Excel başlıklarını güncelle + satır hesaplamasını dinamikleştir**

**Başlıkları** güncelle — mevcut `headers = [...]` listesini şu şekilde değiştir:

```python
    headers = ['Ürün Adı', 'Varyant', 'Barkod', 'Kategori', 'Marka', 'Cinsiyet',
               'Alış Fiyatı', 'Satış Fiyatı', 'Kar Oranı %', 'Kar Tutarı', 'Stok Miktarı', 'Durum']
```

**Satır hesaplamasını** güncelle — `worksheet.cell(row=row, column=9, value=float(varyant.urun.kar_orani))` satırını sil ve **önce** `_alis`/`_satis`/`_oran`/`_tutar` hesaplaması yap, ardından 9 ve 10. kolonlara yaz:

```python
        # Kar oranı ve kâr tutarı dinamik hesaplama
        _alis = varyant.urun.alis_fiyati or ZERO
        _satis = varyant.urun.pesin_fiyat or ZERO
        _tutar = _satis - _alis
        if _satis != 0:
            _oran = float(_tutar / _satis * Decimal('100'))
        else:
            _oran = 0.0
        worksheet.cell(row=row, column=9, value=_oran)
        worksheet.cell(row=row, column=10, value=float(_tutar))
```

**Eski kolon 10-11'i kaydır:** Mevcut `column=10, value=varyant.stok_miktari` → `column=11`. Mevcut `column=11, value=durum_text` → `column=12`.

Kullanılan `ZERO = Decimal('0')` sabitini fonksiyon üst kısmında (`try:` bloğundan önce) tanımla. Decimal import zaten dosyanın başında olacak.

- [ ] **Step 5: Manuel doğrulama**

```bash
cd /var/www/nuviabutik && python manage.py check
```

Beklenen: Başarı.

- [ ] **Step 6: Tek commit (tüm backend değişiklikleri)**

```bash
cd /var/www/nuviabutik && git add rapor/views.py && git commit -m "feat(stok-raporu): dinamik kâr oranı hesabı ve yeni filtre parametreleri"
```

---

## Task 3: Frontend - Template filtre inputları + tablo yeni kolonları

**Files:**
- Modify: `templates/rapor/stok_raporu.html:25-32` (export linkleri), `:89-108` (filtre inputları), `:121-146` (hızlı butonlar), `:208-322` (tablo), `:418-445` (clearFilters JS)

**Interfaces:**
- Reads: Context — `rows` (Task 1'den), `kar_orani_min`, `kar_orani_max`, `durum`, `arama`, `kategori_id`, `marka_id`, `cinsiyet`, `sort_field`, `sort_order`
- Produces: Kullanıcının etkileşimde bulunduğu HTML (filtre formu + tablo)

- [ ] **Step 1: Export linklerine yeni parametreleri ekle (satır 25-32)**

```html
            <a href="{% url 'rapor:stok_excel' %}?arama={{ arama }}&kategori={{ kategori_id }}&marka={{ marka_id }}&durum={{ durum }}&cinsiyet={{ cinsiyet }}&kar_orani_min={{ kar_orani_min }}&kar_orani_max={{ kar_orani_max }}"
                class="btn btn-success">
                <i class="fas fa-file-excel"></i> Excel İndir
            </a>
            <a href="{% url 'rapor:stok_pdf' %}?arama={{ arama }}&kategori={{ kategori_id }}&marka={{ marka_id }}&durum={{ durum }}&cinsiyet={{ cinsiyet }}&kar_orani_min={{ kar_orani_min }}&kar_orani_max={{ kar_orani_max }}"
                class="btn btn-danger">
                <i class="fas fa-file-pdf"></i> PDF İndir
            </a>
```

- [ ] **Step 2: Stok Durumu select'ini 3 seçeneğe indir (satır 89-98)**

Mevcut 5 seçenekli `durum` select'ini değiştir:

```html
                    <!-- Stok Durumu -->
                    <div class="col-md-2">
                        <label for="durum" class="form-label">Stok Durumu</label>
                        <select class="form-select" id="durum" name="durum">
                            <option value="" {% if not durum %}selected{% endif %}>Hepsi</option>
                            <option value="stogu_olan" {% if durum == 'stogu_olan' %}selected{% endif %}>Stoğu Olan</option>
                            <option value="stogu_biten" {% if durum == 'stogu_biten' %}selected{% endif %}>Stoğu Biten</option>
                        </select>
                    </div>
```

- [ ] **Step 3: Kar Oranı Aralığı input'unu Cinsiyet'ten SONRA, Butonlar'dan önce ekle**

Mevcut `.col-md-2` (Cinsiyet) bittikten sonra, mevcut `<!-- Butonlar --> .col-md-2` satırından ÖNCE:

```html
                    <!-- Kar Oranı Aralığı -->
                    <div class="col-md-2">
                        <label class="form-label">Kar Oranı Aralığı (%)</label>
                        <div class="input-group">
                            <input type="number" step="0.01" min="0" max="1000" class="form-control"
                                name="kar_orani_min" value="{{ kar_orani_min }}" placeholder="Min">
                            <input type="number" step="0.01" min="0" max="1000" class="form-control"
                                name="kar_orani_max" value="{{ kar_orani_max }}" placeholder="Max">
                        </div>
                    </div>
```

- [ ] **Step 4: Hızlı Filtreler butonlarını güncelle (satır 121-146)**

Mevcut 4'lü buton grubunu (`Tümü`, `Tükenenler`, `Kritik`, `Normal` + `Temizle`) şu şekilde değiştir:

```html
                <!-- Hızlı Filtreler -->
                <div class="row">
                    <div class="col-12">
                        <div class="btn-group btn-group-sm" role="group">
                            <a href="?{% if sort_field %}sort={{ sort_field }}&order={{ sort_order }}{% endif %}"
                                class="btn btn-outline-primary {% if not durum and not arama and not kategori_id and not marka_id and not kar_orani_min and not kar_orani_max %}active{% endif %}">
                                <i class="fas fa-list"></i> Hepsi
                            </a>
                            <a href="?durum=stogu_olan{% if sort_field %}&sort={{ sort_field }}&order={{ sort_order }}{% endif %}{% if kar_orani_min %}&kar_orani_min={{ kar_orani_min }}{% endif %}{% if kar_orani_max %}&kar_orani_max={{ kar_orani_max }}{% endif %}"
                                class="btn btn-outline-success {% if durum == 'stogu_olan' %}active{% endif %}">
                                <i class="fas fa-check-circle"></i> Stoğu Olan
                            </a>
                            <a href="?durum=stogu_biten{% if sort_field %}&sort={{ sort_field }}&order={{ sort_order }}{% endif %}{% if kar_orani_min %}&kar_orani_min={{ kar_orani_min }}{% endif %}{% if kar_orani_max %}&kar_orani_max={{ kar_orani_max }}{% endif %}"
                                class="btn btn-outline-danger {% if durum == 'stogu_biten' %}active{% endif %}">
                                <i class="fas fa-times-circle"></i> Stoğu Biten
                            </a>
                            <button type="button" class="btn btn-outline-secondary" onclick="clearFilters()">
                                <i class="fas fa-eraser"></i> Temizle
                            </button>
                        </div>
                    </div>
                </div>
```

- [ ] **Step 5: Tablo başlığı — "Kâr Tutarı" kolonu ekle (satır 210-256)**

`<thead>` içinde, mevcut `Satış Fiyatı` `<th>` ile `Kar Oranı` `<th>` arasına ekle:

```html
                            <th>Kar Tutarı</th>
```

- [ ] **Step 6: Tablo body'sini `rows` üzerinde döngüye çevir + yeni kolonları doldur (satır 257-318)**

Mevcut `<tbody>` bloğunu tamamen değiştir:

```html
                    <tbody>
                        {% for row in rows %}
                        <tr>
                            <td>{{ row.varyant.urun.ad }}</td>
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
                                <span
                                    class="badge {% if row.varyant.urun.cinsiyet == 'kadin' %}bg-pink{% else %}bg-blue{% endif %}">
                                    {{ row.varyant.urun.get_cinsiyet_display }}
                                </span>
                            </td>
                            <td>
                                <span class="text-primary fw-bold">{{ row.varyant.urun.alis_fiyati|turkish_currency }}</span>
                            </td>
                            <td>
                                <span class="text-success fw-bold">{{ row.varyant.urun.pesin_fiyat|turkish_currency }}</span>
                            </td>
                            <td>
                                <span class="fw-bold {% if row.kar_tutari > 0 %}text-success{% elif row.kar_tutari < 0 %}text-danger{% else %}text-muted{% endif %}">
                                    {{ row.kar_tutari|turkish_currency }}
                                </span>
                            </td>
                            <td>
                                <span
                                    class="badge {% if row.kar_orani >= 50 %}bg-success{% elif row.kar_orani >= 30 %}bg-warning{% elif row.kar_orani >= 0 %}bg-info{% else %}bg-danger{% endif %}">
                                    %{{ row.kar_orani|floatformat:1 }}
                                </span>
                            </td>
                            <td>
                                <span
                                    class="fw-bold {% if row.varyant.stok_miktari == 0 %}text-danger{% elif row.varyant.stok_miktari <= 5 %}text-warning{% else %}text-success{% endif %}">
                                    {{ row.varyant.stok_miktari }}
                                </span>
                            </td>
                            <td>
                                {% if row.varyant.stok_miktari == 0 %}
                                <span class="badge bg-danger">Tükendi</span>
                                {% elif row.varyant.stok_miktari <= 5 %} <span class="badge bg-warning">Kritik</span>
                                    {% else %}
                                    <span class="badge bg-success">Normal</span>
                                    {% endif %}
                            </td>
                            <td>
                                <a href="{% url 'rapor:stok_hareketleri' row.varyant.id %}"
                                    class="btn btn-outline-info btn-sm" title="Stok Hareketlerini Görüntüle">
                                    <i class="fas fa-history"></i> Hareketler
                                </a>
                            </td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="13" class="text-center">Ürün bulunamadı.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
```

- [ ] **Step 7: `clearFilters` JS fonksiyonunu yeni inputları da temizleyecek şekilde güncelle (satır 418-437)**

```html
    // Filtreleri temizle
    function clearFilters() {
        // Sıralama parametrelerini koru
        const sortField = document.querySelector('input[name="sort"]').value;
        const sortOrder = document.querySelector('input[name="order"]').value;

        // Form alanlarını temizle
        document.getElementById('arama').value = '';
        document.getElementById('kategori').value = '';
        document.getElementById('marka').value = '';
        document.getElementById('durum').value = '';
        document.querySelector('input[name="kar_orani_min"]').value = '';
        document.querySelector('input[name="kar_orani_max"]').value = '';

        // Yeni URL oluştur (sadece sıralama ile)
        let newUrl = window.location.pathname;
        if (sortField && sortField !== 'urun__ad') {
            newUrl += `?sort=${sortField}&order=${sortOrder}`;
        }

        window.location.href = newUrl;
    }
```

- [ ] **Step 8: Sayaç hesaplama fonksiyonunu `rows` üzerinde çalışacak şekilde uyarla**

Mevcut `calculateStockCounts()` fonksiyonunda `tbody tr` üzerinden `.stok-badge` aramaya gerek yok çünkü template'te badge artık başka yerde. Bu fonksiyonu sadeleştir (zaten 0 kritik/tükenen gösteriyor, kritik/tükenen artık sadece tükenmiş olanları sayacak şekilde):

```html
    // Stok sayılarını hesapla
    function calculateStockCounts() {
        const rows = document.querySelectorAll('tbody tr');
        let kritikCount = 0;
        let tukenenCount = 0;

        rows.forEach(row => {
            // Stok miktarı 11. kolon hücresinin text içeriğinden parse edilir
            const stokHucre = row.children[10]; // 11. kolon (0-indexed 10)
            if (stokHucre) {
                const val = parseInt(stokHucre.textContent.trim());
                if (!isNaN(val)) {
                    if (val === 0) tukenenCount++;
                    else if (val <= 5) kritikCount++;
                }
            }
        });

        document.getElementById('kritikCount').textContent = kritikCount;
        document.getElementById('tukenenCount').textContent = tukenenCount;
    }
```

Not: Eğer `.stok-badge` sınıfını `<td>`'ye eklerseniz daha güvenilir olur. Bunun için Step 6 tablosunda 11. `<td>`'yi şu şekilde güncelleyin (mevcut `<span class="fw-bold ...">` yerine badge ekleyin):

```html
                            <td>
                                <span class="stok-badge fw-bold {% if row.varyant.stok_miktari == 0 %}text-danger{% elif row.varyant.stok_miktari <= 5 %}text-warning{% else %}text-success{% endif %}">
                                    {{ row.varyant.stok_miktari }}
                                </span>
                            </td>
```

Bu durumda JS'i şu sadeleştirilmiş haliyle bırakın:

```html
    // Stok sayılarını hesapla
    function calculateStockCounts() {
        const rows = document.querySelectorAll('tbody tr');
        let kritikCount = 0;
        let tukenenCount = 0;

        rows.forEach(row => {
            const stokBadge = row.querySelector('.stok-badge');
            if (stokBadge) {
                const stokMiktari = parseInt(stokBadge.textContent.trim());
                if (!isNaN(stokMiktari)) {
                    if (stokMiktari === 0) tukenenCount++;
                    else if (stokMiktari <= 5) kritikCount++;
                }
            }
        });

        document.getElementById('kritikCount').textContent = kritikCount;
        document.getElementById('tukenenCount').textContent = tukenenCount;
    }
```

- [ ] **Step 9: Commit**

```bash
cd /var/www/nuviabutik && git add templates/rapor/stok_raporu.html && git commit -m "feat(stok-raporu): kâr tutarı kolonu, stoğu olan/biten filtresi, kar oranı aralık filtresi"
```

---

## Task 4: Manuel smoke test + endpoint toplama doğrulaması

**Files:**
- Read-only testleri mevcut kod üzerinde

- [ ] **Step 1: Sayfa yüklenir mi?**

```bash
cd /var/www/nuviabutik && set -a && source .env && set +a && python manage.py runserver 0.0.0.0:8765 &
# veya nginx üzerinden /rapor/stok-raporu/ URL'sine git
```

Beklenen: Sayfa yüklenir, "Kâr Tutarı" ve "Kâr Oranı" kolonları görünür, hata yok.

- [ ] **Step 2: Stok durumu filtresi "Stoğu Olan" çalışıyor mu?**

URL'ye git: `?durum=stogu_olan`

Beklenen: Sadece stok > 0 olan ürünler.

- [ ] **Step 3: Stok durumu filtresi "Stoğu Biten" çalışıyor mu?**

URL'ye git: `?durum=stogu_biten`

Beklenen: Sadece stok = 0 olan ürünler.

- [ ] **Step 4: Kar oranı aralık filtresi çalışıyor mu?**

URL'ye git: `?kar_orani_min=30&kar_orani_max=70`

Beklenen: Sadece kâr oranı %30-70 arası olan ürünler.

- [ ] **Step 5: Negatif kâr doğru gösteriliyor mu?**

Veritabanında `alis_fiyati > pesin_fiyat` olan bir ürün varsa (yoksa test verisi eklenebilir), ilgili satırda:
- Kâr Tutarı kırmızı (negatif ₺)
- Kar Oranı rozeti kırmızı ve eksi değer

- [ ] **Step 6: `pesin_fiyat = 0` ürün hata vermeden görünüyor mu?**

Veritabanında `pesin_fiyat = 0` ürün varsa, o satırda `Kar Oranı: 0.0%` yazmalı, hata yok.

- [ ] **Step 7: Export (Excel) linki yeni parametreleri koruyor mu?**

Tarayıcıda "Excel İndir" linkine sağ tıkla → URL incele → URL'de `kar_orani_min` ve `kar_orani_max` mevcut.

- [ ] **Step 8: `clearFilters` tüm inputları temizliyor mu?**

Sayfadaki "Temizle" butonuna tıkla → URL'de sadece sort parametreleri kalmalı (varsa), arama/kategori/marka/durum/kar_orani temizlenmiş olmalı.

- [ ] **Step 9: Final commit (gerekirse backend ile birlikte)**

Eğer Task 1+2 ayrı commit'lendi ise ve düzeltme gerekirse:

```bash
cd /var/www/nuviabutik && git diff rapor/views.py templates/rapor/stok_raporu.html
# (gerekirse düzeltme yap, düzeltme varsa: git commit -am "fix(stok-raporu): ...")
```

---

## Self-Review Kontrol Listesi

### Spec coverage

| Spec gereksinimi | Sağlayan task |
|------------------|---------------|
| Kar oranı dinamik hesap | Task 1 (Step 3, 4) |
| Kâr tutarı kolonu | Task 3 (Step 5, 6) |
| Stok durumu 3 seçenek | Task 1 (Step 2), Task 3 (Step 2) |
| Kar oranı aralık filtresi | Task 1 (Step 3), Task 3 (Step 3) |
| Export parametreleri | Task 2 (Step 1, 2, 3), Task 3 (Step 1) |
| Edge case'ler (sıfıra bölüm, negatif, geçersiz) | Task 1 (Step 3), Task 2 (Step 3) |
| Manuel test senaryoları | Task 4 |

### Placeholder scan

- "TBD"/"TODO" yok.
- "benzer task için tekrara" gerek yok (her task kendi içinde eksiksiz).
- Tüm kod blokları tam.

### Type/isim tutarlılığı

- `rows` her yerinde aynı (Task 1 Step 4 → Task 3 Step 6).
- `kar_orani_min`, `kar_orani_max` her yerinde aynı (Task 1, 2, 3).
- `stogu_olan`, `stogu_biten` her yerinde aynı (Task 1 Step 2, Task 2 Step 2, Task 3 Step 2 & 4).
- `_compute_metrics` yardımcısı sadece Task 1 (Step 4) içinde kullanılıyor, çakışma yok.
