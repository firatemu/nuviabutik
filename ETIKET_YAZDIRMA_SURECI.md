# Nuvia Butik - Etiket Yazdırma Sistemi Teknik Analiz ve Dökümantasyonu

Bu döküman, Nuvia Butik projesindeki ürün etiket yazdırma sürecinin teknik detaylarını, kurulan bağlantı türlerini, yazıcı bilgilerini ve şablon yapılarını içermektedir.

## 1. Yazdırma Süreci ve Bağlantı Mimarisi

Sistem direkt olarak web tarayıcısı üzerinden yazıcı ile iletişim kuramadığı için **Yerel Print Agent (Bridge/Köprü)** mimarisi kullanılmaktadır.

### 1.1 Print Agent Bağlantısı
- **Local Agent:** İstemci tarafında `NuviaButikPrintAgent-Installer.bat` ile kurulan yerel bir windows servisi / uygulaması çalıştırılır.
- **WebSocket İletişimi:** Tarayıcı tarafındaki sistem (`nuvia-print-manager.js` ve `nuvia-bridge.js`), localhost üzerindeki bu local agent ile bir WebSocket bağlantısı kurar (`ws://localhost:9876`).
- **HTTP Fallback:** Eğer WebSocket bağlantısı sağlanamazsa Print Manager HTTP kullanarak istekte bulunmaya çalışır (`http://localhost:9876/print`).
- **Port Tarama:** Eğer varsayılan `9876` portu başarısız olursa, ajan 9877-9880 arası portları deneyerek açık olan print servisini otomatik bulur.

### 1.2 Yazdırma Akışı
1. Kullanıcı arayüzde **Yazdır** veya **Toplu Yazdır** butonuna basar.
2. `nuvia-print-manager.js`, Django sunucusuna `/urun/api/etiket/websocket/<varyant_id>/` adresinden POST (veya GET) isteği göndererek yazdırma verilerini talep eder.
3. Django, arka planda ürün verilerini derleyerek şablona/kalıba (`ZPL` kodlarına) dönüştürür.
4. Elde edilen RAW (`ZPL` formatındaki text) kodları, JSON içerisinde Front-end'e döner (`zpl_data`).
5. JavaScript (`nuvia-print-manager.js`), bu ZPL kodunu arka planda açılmış olan WebSocket bağlantısı üzerinden Local Print Agent'a (`{type: 'print_label', zpl_data: data.zpl_data}`) iletir.
6. Local Print Agent kodu alır ve doğrudan varsayılan barkod yazıcısına RAW formatta döküm gönderir.

---

## 2. Yazıcı Bilgileri ve Dosya Türü

### 2.1 Yazıcı Bilgisi
Projeye göre tasarlanmış temel referans yazıcı: **Xprinter XP-470B**
- **Sürücü Adı Modeli:** `Xprinter XP-470B`
- **Etiket Boyutu:** 56mm genişlik x 40mm yükseklik.
- **Çözünürlük ve Dot (Nokta) Kullanımı:** 8 dots/mm (448 dots x 320 dots)
- Veritabanı modellemesinde kullanıcı dilerse `YaziciAyarlari` menüsünden farklı değerler girebilir (Varsayılan: 40x30mm).

### 2.2 Yazdırılan Dosya Türü
Dosyalar bilindik PDF veya XPS değildir; doğrudan **ZPL (Zebra Programming Language)** formatında komutlar halinde (TXT/RAW) gönderilir. 
Özel indirme veya test sayfalarından (`/urun/api/getlabel/`) `Content-Type: text/plain` formatında `.prn` uzantılı dosya indirilmesi de desteklenir.

---

## 3. Etiket Şablonu (Template) Türleri ve İçerik

Sistem 2 farklı yolla ZPL etiket şablonları üretebilir: **Statik (Hard-coded) Şablonlar** ve **Veritabanı Tabanlı Tasarımcı (Etiket Sablon Eleman) Şablonları**.

### 3.1 Gelişmiş ZPL Şablonları (Kod İçerisinden)
`stoktakip/advanced_zpl.py` dosyasında bulunan Python generator sınıfı, etiketin yapısını ZPL formatında derler.
**Yazdırılan Alanlar:**
- **Marka Adı:** Örn: NUVIA (En üstte, ortalı / büyük punto)
- **Alt Başlık/Slogan:** Örn: Premium Wear Man & Woman
- **Ürün/Model Adı:** Ürünün genel ismi (Örn: Elbise)
- **Fiyat:** Hesaplanan peşin satış fiyatı (Örn: 999.99 TL)
- **Beden:** Varyant bedeni (Örn: XL)
- **Barkod:** Sistemin otomatik ürettiği 13 haneli ürün barkodu (Code128 formatı: `^BCN,40,Y,N,N`)
- **Ürün Kodu ve Tarih:** Sisteme girilen kod (`TEST001`) ve o anın tarihi ortalı listelenir.

*(Örnek Optimizasyon Kodu: `^FO30,30^CF0,28^FD{brand}^FS`)*

### 3.2 Dinamik Şablon Tasarımcı Aracı
Sistemde ayrıca kullanıcıların sürükle-bırak yöntemiyle etiket tasarlayabildikleri dinamik bir altyapı da mevcuttur.
- **Models:** `EtiketSablonu` ve `EtiketSablonEleman`
- **Tasarım Aracı:** `etiket_views.py` içerisinde yönetilir. `etiket_tasarimci.html` üzerinden JSON nesnesi (pozisyon_x, pozisyon_y, barkod tipi, font ve renk ayarları vb.) kaydedilir.
- Yazıcı ayarları (`YaziciAyarlari`) da db üzerinden kullanıcıya özel (kopya_sayisi, genislik, yukseklik vb.) tutulur.

## 4. Sonuç Özeti
- Ürün etiketi yazdırmak için kullanıcı tarafında bir port agent uygulaması köprü olarak beklemektedir.
- Web ortamı bu uygulama ile WebSocket / HTTP portları vasıtasıyla bağlanır.
- Django API, ürün datasını Zebra tabanlı ZPL komutlarına string olarak derler (`^XA...^XZ`).
- Çıktı, `Xprinter` türündeki termal yazıcıya boyutlandırılmış olarak dökülür. Yapısı dinamik ve güvenli bir yerel köprü mimarisinden güç alır.
