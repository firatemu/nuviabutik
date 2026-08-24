# Detaylı Stok Raporu - Kar Oranı ve Filtre İyileştirmesi

**Tarih:** 2026-08-12
**Durum:** Onay Bekliyor
**Yazar:** Cursor (brainstorming skill)

## Özet

`Detaylı Stok Raporu` sayfasındaki ürünlerin **kar oranı** yanlış hesaplanıyor. Mevcut uygulamada `Urun.kar_orani` DB'de saklı sabit bir yüzde olup (varsayılan 50), alış ve satış fiyatlarını dikkate almaz. Bu rapor, söz konusu sayfada kar oranını **alış ve satış fiyatlarına göre dinamik olarak yeniden hesaplamayı**, tabloya **kâr tutarı** kolonu eklemeyi, **stok durumu filtresini 3 seçeneğe** indirgemeyi ve **kar oranı aralık filtresi** eklemeyi hedefler.

## Kapsam

### Dahil

- `Detaylı Stok Raporu` (URL: `rapor:stok_raporu`) tablosundaki kar oranı gösteriminin düzeltilmesi
- Tabloya "Kâr Tutarı" kolonunun eklenmesi
- Stok durumu filtresinin sadeleştirilmesi: Hepsi / Stoğu Olan / Stoğu Biten
- Yeni kar oranı aralık filtresi (min - max)
- Export linklerinin (`stok_excel`, `stok_pdf`) yeni parametreleri koruması
- Kar oranı filtrelemesinin Python (view) tarafında yapılması

### Hariç

- Veritabanı şeması değişiklikleri (alan eklenmez, `Urun.kar_orani` dokunulmaz; başka raporlarda kullanılıyor olabilir)
- Diğer raporlar (`Stok Değeri`, `Ürün Bazlı Karlılık` vb.) - bu görev kapsamı dışıdır
- Ürün ekleme/düzenleme formundaki `kar_orani` alanı - bu rapor kapsamı dışıdır
- Frontend framework değişiklikleri (mevcut Vanilla JS + Bootstrap yapısı korunur)

## Mevcut Durum Analizi

### Kar oranı hesaplama

`templates/rapor/stok_raporu.html` (satır 285):
```django
{% with kar_orani=varyant.urun.kar_orani %}
<span class="badge ...">%{{ kar_orani|floatformat:1 }}</span>
{% endwith %}
```

Bu, DB'de `Urun.kar_orani` (DecimalField, default 50.00) değerini okur. **Alış/satış fiyatları dikkate alınmaz.** Bu nedenle alış = 100, satış = 200 olan ürün için %50 görünürken, alış = 50, satış = 200 olan ürün için de aynı %50 görünür - bu yanlıştır.

### Stok durumu filtresi

`rapor/views.py` `stok_raporu` view (satır 128-135):
```python
if durum == 'tukendi':
    varyantlar = varyantlar.filter(stok_miktari=0)
elif durum == 'kritik':
    varyantlar = varyantlar.filter(stok_miktari__gt=0, stok_miktari__lte=5)
elif durum == 'normal':
    varyantlar = varyantlar.filter(stok_miktari__gt=5)
```

Kullanıcı talebi: 4 seçenek (hepsi, normal, kritik, tükendi) yerine **3 seçenek** (hepsi, stoğu olan, stoğu biten). "Kritik" ve "Normal" ayrımı kaldırılır.

### Kar oranı filtresi

Mevcut kodda tamamen yok. Yeni eklenecek: `kar_orani_min` ve `kar_orani_max` (yüzde değerleri).

## Hedef Davranış

### 1. Tablo Gösterimi

`Detaylı Stok Raporu` tablosunda:

| Kolon | Veri Kaynağı | Açıklama |
|------|--------------|----------|
| Ürün Adı, Varyant, Barkod, Kategori, Marka, Cinsiyet | Mevcut (değişmez) | Mevcut |
| Alış Fiyatı | `Urun.alis_fiyati` | Mevcut, değişmez |
| Satış Fiyatı | `Urun.pesin_fiyat` (görünümde `satis_fiyati` alias) | Mevcut, değişmez |
| **Kâr Tutarı** | `pesin_fiyat - alis_fiyati` (yeni hesaplama) | **Yeni kolon** |
| **Kâr Oranı** | `(satis - alis) / satis × 100` (yeni hesaplama) | **Dinamik** |
| Mevcut Stok | Mevcut | Mevcut |
| Durum, İşlemler | Mevcut | Mevcut |

### 2. Hesaplama Kuralları

- **Kâr Tutarı** = `pesin_fiyat - alis_fiyati` (ondalık, ₺ cinsinden)
- **Kâr Oranı (%)** = `(pesin_fiyat - alis_fiyati) / pesin_fiyat × 100`
- **Edge case (sıfıra bölüm):** Eğer `pesin_fiyat == 0` ise kâr oranı `-` veya `0.0%` gösterilir (sıfıra bölme hatası olmaz).
- **Negatif kâr:** Eğer `alis > satis` ise kâr oranı negatif olur; kırmızı badge ile gösterilir.
- **Sıralama:** Kâr Oranı kolonu `urun__kar_orani` alanına göre sıralanmaya devam eder (kullanıcı isterse sıralama değiştirilebilir; ilk sürümde **DB alanına göre** sıralanır - aynı sayıda JOIN'li sorgu kullanılır).

### 3. Stok Durumu Filtresi

`durum` parametresi değerleri:

| Değer | Anlam | Sorgu |
|-------|-------|-------|
| `''` (boş) veya yok | Hepsi | (filtre yok) |
| `stogu_olan` | Stoğu olan | `stok_miktari__gt=0` |
| `stogu_biten` | Stoğu biten | `stok_miktari=0` |

### 4. Kar Oranı Filtresi

İki yeni GET parametresi:

- `kar_orani_min` (opsiyonel, ondalık sayı, % cinsinden)
- `kar_orani_max` (opsiyonel, ondalık sayı, % cinsinden)

Davranış:
- Her iki alan da boşsa → filtre uygulanmaz.
- Sadece `min` doluysa → `kar_orani >= min`
- Sadece `max` doluysa → `kar_orani <= max`
- İkisi de doluysa → `kar_orani` bu aralıkta.

**Kar oranı filtreleme stratejisi (Python tarafı):** DB'den tüm varyantlar çekilir, view'da Python `list` üzerinde filtrelenir, ardından template'e gönderilir. Annotation/ExpressionWrapper ile DB seviyesinde hesaplama seçilmemiştir çünkü (a) rapor veri hacmi çok büyük değildir, (b) Python tarafı okunabilirliği daha yüksektir, (c) DB alanı `F('urun__kar_orani')` hala "DB'de saklı eski kar_orani" olacağı için burada güvenilir değildir.

### 5. Export

`stok_excel` ve `stok_pdf` view'larına da yeni parametreler (`durum`, `kar_orani_min`, `kar_orani_max`) geçirilir; böylece export linkleri mevcut filtreye sadık kalır.

**Not:** Mevcut export fonksiyonlarının içerikleri bu görevde incelenmeyecek - sadece **query string ekleme/koruma** işlemi yapılır. İçerik formatlarında kar oranı hesaplaması ayrı bir konudur; bu görevde Excel/PDF çıktısına müdahale edilmez (export fonksiyonları ayrı bir görev olarak değerlendirilebilir).

## Teknik Tasarım

### Backend (`rapor/views.py`)

```python
def stok_raporu(request):
    from urun.models import UrunVaryanti, UrunKategoriUst, Marka
    from django.db.models import Q

    varyantlar = UrunVaryanti.objects.filter(
        aktif=True,
        urun__aktif=True
    ).select_related('urun', 'urun__kategori', 'urun__marka', 'renk', 'beden').order_by('urun__kategori__ad', 'urun__ad')

    arama = request.GET.get('arama', '').strip()
    kategori_id = request.GET.get('kategori')
    marka_id = request.GET.get('marka')
    durum = request.GET.get('durum')
    cinsiyet = request.GET.get('cinsiyet')

    # Kar oranı filtre parametreleri (opsiyonel)
    kar_orani_min = (request.GET.get('kar_orani_min', '')).strip()
    kar_orani_max = (request.GET.get('kar_orani_max', '')).strip()

    sort_field = request.GET.get('sort', 'urun__ad')
    sort_order = request.GET.get('order', 'asc')

    # ... mevcut valid_sort_fields listesi ...

    if sort_field not in valid_sort_fields:
        sort_field = 'urun__ad'
    if sort_order == 'desc':
        sort_field = '-' + sort_field

    if arama:
        varyantlar = varyantlar.filter(...)

    if kategori_id:
        varyantlar = varyantlar.filter(urun__kategori_id=kategori_id)

    if marka_id:
        varyantlar = varyantlar.filter(urun__marka_id=marka_id)

    # Stok durumu — yeni 3 seçenek
    if durum == 'stogu_olan':
        varyantlar = varyantlar.filter(stok_miktari__gt=0)
    elif durum == 'stogu_biten':
        varyantlar = varyantlar.filter(stok_miktari=0)
    # Boş veya yok → tümü

    if cinsiyet and cinsiyet != 'hepsi':
        varyantlar = varyantlar.filter(urun__cinsiyet=cinsiyet)

    # Kar oranı Python tarafında filtrelenecek
    varyant_list = list(varyantlar.order_by(sort_field, 'urun__ad', 'renk__ad', 'beden__ad'))

    def _compute_kar(v):
        alis = v.urun.alis_fiyati or Decimal('0')
        satis = v.urun.pesin_fiyat or Decimal('0')
        return alis, satis

    if kar_orani_min or kar_orani_max:
        try:
            min_val = float(kar_orani_min) if kar_orani_min else None
            max_val = float(kar_orani_max) if kar_orani_max else None
        except ValueError:
            min_val = None
            max_val = None

        def _passes(v):
            alis, satis = _compute_kar(v)
            if satis and satis != 0:
                oran = float((satis - alis) / satis * Decimal('100'))
            else:
                oran = 0.0
            if min_val is not None and oran < min_val:
                return False
            if max_val is not None and oran > max_val:
                return False
            return True

        varyant_list = [v for v in varyant_list if _passes(v)]

    kategoriler = UrunKategoriUst.objects.all().order_by('ad')
    markalar = Marka.objects.all().order_by('ad')

    context = {
        'varyantlar': varyant_list,
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
    return render(request, 'rapor/stok_raporu.html', context)
```

### Template (`templates/rapor/stok_raporu.html`)

#### Filtre formu (mevcut 5. satırdaki filter formuna 2 input eklenir)

Yeni iki input yan yana, Stok Durumu'nun sağında veya altındaki satıra:

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

#### Stok durumu select'i güncellemesi

```html
<select class="form-select" id="durum" name="durum">
    <option value="">Hepsi</option>
    <option value="stogu_olan" {% if durum == 'stogu_olan' %}selected{% endif %}>Stoğu Olan</option>
    <option value="stogu_biten" {% if durum == 'stogu_biten' %}selected{% endif %}>Stoğu Biten</option>
</select>
```

#### Hızlı filtre butonları güncelleme

```html
<a href="?{% if sort_field %}sort={{ sort_field }}&order={{ sort_order }}{% endif %}"
   class="btn btn-outline-primary {% if not durum and not arama and not kategori_id and not marka_id and not kar_orani_min and not kar_orani_max %}active{% endif %}">
    <i class="fas fa-list"></i> Hepsi
</a>
<a href="?durum=stogu_olan{% if sort_field %}&sort={{ sort_field }}&order={{ sort_order }}{% endif %}"
   class="btn btn-outline-success {% if durum == 'stogu_olan' %}active{% endif %}">
    <i class="fas fa-check-circle"></i> Stoğu Olan
</a>
<a href="?durum=stogu_biten{% if sort_field %}&sort={{ sort_field }}&order={{ sort_order }}{% endif %}"
   class="btn btn-outline-danger {% if durum == 'stogu_biten' %}active{% endif %}">
    <i class="fas fa-times-circle"></i> Stoğu Biten
</a>
```

`clearFilters()` fonksiyonu: Yeni inputların da temizlenmesi eklenir.

#### Tablo başlıkları (mevcut 12 sütun → 13 sütun)

```html
<th class="sortable" data-sort="urun__alis_fiyati">Alış Fiyatı</th>
<th class="sortable" data-sort="urun__satis_fiyati">Satış Fiyatı</th>
<th>Kar Tutarı</th>  <!-- yeni kolon -->
<th class="sortable" data-sort="urun__kar_orani">Kar Oranı</th>
```

#### Tablo body'si (her varyant satırında)

```html
<td>
    <span class="text-primary fw-bold">{{ varyant.urun.alis_fiyati|turkish_currency }}</span>
</td>
<td>
    <span class="text-success fw-bold">{{ varyant.urun.pesin_fiyat|turkish_currency }}</span>
</td>
<td>
    {% with alis=varyant.urun.alis_fiyati satis=varyant.urun.pesin_fiyat %}
        {% with kar_tutari=satis|sub:alis %}
            <span class="fw-bold {% if kar_tutari > 0 %}text-success{% elif kar_tutari < 0 %}text-danger{% else %}text-muted{% endif %}">
                {{ kar_tutari|turkish_currency }}
            </span>
        {% endwith %}
    {% endwith %}
</td>
<td>
    {% with alis=varyant.urun.alis_fiyati satis=varyant.urun.pesin_fiyat %}
        {% if satis and satis != 0 %}
            {% with oran=satis|sub:alis %}
                {% widthratio oran 1 100 %}  {# bu beklenen sonucu vermeyebilir — kontrolü yapılacak #}
            ...
```

**Önemli Not:** Django template'in `Decimal` üzerinde çıkarma/çarpma yapabilen yerleşik bir template filter yoktur. Bu nedenle **karmaşık matematik template tarafında değil view'da hesaplanır**, hesaplanmış değerler (örn. `kar_tutari`, `kar_orani`) varyant dict veya context üzerinde hazır olarak template'e gelir.

### Alternatif (Önerilen) Yaklaşım

`stok_raporu` view'ında varyant listesi oluşturulduktan sonra her varyant için sözlük şeklinde hesaplanmış alanlar eklenir:

```python
def _compute_metrics(v):
    alis = v.urun.alis_fiyati or Decimal('0')
    satis = v.urun.pesin_fiyat or Decimal('0')
    kar_tutari = satis - alis
    if satis != 0:
        kar_orani = (kar_tutari / satis) * Decimal('100')
    else:
        kar_orani = Decimal('0')
    return {
        'varyant': v,
        'kar_tutari': kar_tutari,
        'kar_orani': kar_orani,
    }

# ... filtre uygulandıktan sonra ...
varyant_metrics = [_compute_metrics(v) for v in varyant_list]

context = {
    'rows': varyant_metrics,  # sözlük listesi
    ...
}
```

Template'te:
```html
{% for row in rows %}
    <tr>
        <td>{{ row.varyant.urun.ad }}</td>
        ...
        <td>{{ row.kar_tutari|turkish_currency }}</td>
        <td>
            <span class="badge ...">%{{ row.kar_orani|floatformat:1 }}</span>
        </td>
        ...
    </tr>
{% endfor %}
```

Bu yaklaşım **önerilir çünkü**:
1. Template temiz kalır
2. Edge case'ler (sıfıra bölüm, negatif) merkezi olarak Python'da yönetilir
3. Badge renk mantığı (negatif/sıfır/pozitif) tek yerde toplanabilir

### Export Fonksiyonları

`stok_excel` ve `stok_pdf` view'larındaki URL'lere yeni parametreler eklenecek, fonksiyonların iç mantığına dokunulmayacak:

```python
# Mevcut export URL:
export_url = f"{reverse('rapor:stok_excel')}?arama={arama}&kategori={kategori_id}&marka={marka_id}&durum={durum}&cinsiyet={cinsiyet}&kar_orani_min={kar_orani_min}&kar_orani_max={kar_orani_max}"
```

## Etkilenen Dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `rapor/views.py` | `stok_raporu` view'ı: yeni GET parametreler, yeni stok durumu seçenekleri, hesaplama/filters |
| `templates/rapor/stok_raporu.html` | Filtre formuna inputlar, select güncelleme, hızlı butonlar, tablo başlıkları, tablo body'si, script (clearFilters) |

Toplam **2 dosya** değişir. Veritabanı migration gerekmez.

## Test Senaryoları

| # | Senaryo | Beklenen Sonuç |
|---|---------|----------------|
| 1 | Sayfa açılır | Tüm varyantlar listelenir; Kâr Tutarı ve Kâr Oranı doğru hesaplanır |
| 2 | Filtre: `kar_orani_min=30&kar_orani_max=70` | Sadece %30-70 aralığındaki ürünler |
| 3 | Filtre: `kar_orani_min=50` (max boş) | Sadece ≥%50 olanlar |
| 4 | Filtre: `durum=stogu_olan` | Sadece stok > 0 olanlar |
| 5 | Filtre: `durum=stogu_biten` | Sadece stok = 0 olanlar |
| 6 | `pesin_fiyat = 0` | Kâr Oranı "0.0%" (DivisionByZero yok) |
| 7 | `alis_fiyat > pesin_fiyat` (negatif kâr) | Kâr Tutarı kırmızı, Oran negatif |
| 8 | Filtre `kar_orani_min=abc` (geçersiz sayı) | Filtre yok sayılır (tüm sonuçlar) |
| 9 | Export linkleri | Yeni parametreler URL'de mevcut |
| 10 | Tarayıcı geri/ileri navigasyonu | Filtreler korunur |

## Riskler ve Azaltımlar

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| Mevcut kullanıcılar mevcut 4'lü durum filtresi alışkanlığında | Orta | Düşük | Hızlı butonlar "Hepsi / Stoğu Olan / Stoğu Biten" olarak açık şekilde sunulur; geçiş yumuşak |
| Kar oranı hesaplaması sonucu sayfa render'ı yavaşlar | Düşük | Düşük | Veri hacmi az; Python tarafı list comprehension yeterli. İleride annotation'a geçiş mümkün |
| `pesin_fiyat=0` ürünlerde NaN hatası | Orta | Orta | View'da sıfıra bölüm kontrolü; template'te hesaplamadan kaçınılır |
| Eski `satis_fiyati` alanı hâlâ template'te kullanılıyor | Yüksek | Orta | Bu değişiklikle düzeltilecek: `varyant.urun.pesin_fiyat` kullanılacak |

## Serbest Bırakma Planı

1. Backend değişikliği (`stok_raporu`) yapılır
2. Test (lokal + canlı): sayfa yüklenir, filtreler çalışır
3. Template güncelleme: kolonlar ve filtre inputları
4. Manuel test senaryoları uygulanır (yukarıdaki tablo)
5. Export linkleri kontrolü
6. Static collect, cache yenileme (gerekirse)

## Açık Sorular / Varsayımlar

- **Sıralama:** Kullanıcı sıralama isterse DB alanına göre kalır. İleride Python tarafı hesaplanmış değere göre sıralama eklenirse Sortable JS tarafında ek iş gerekir - bu görev kapsamında **değiştirilmez**.
- **Excel/PDF çıktısı formatı:** Bu görevde Excel/PDF rapor içeriğindeki kar oranı hesaplaması değiştirilmez. Sadece export parametreleri korunur. Excel/PDF'in de dinamik kar oranı göstermesi ayrı bir görevdir.
- **Çoklu varyant hesaplama:** Bir ürünün birden çok varyantı varsa her varyant **kendi alış/satış fiyatı** ile değerlendirilir - ki bu doğru davranıştır. Bir ürünün **ortalama** karı gösterilmez.
