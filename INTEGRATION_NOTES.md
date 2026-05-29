# Nuvia Butik QZ Tray Entegrasyon Notları

Eski WebSocket köprüsü (Print Agent), standartlara tam uyumlu çalışan **QZ Tray** ile başarılı bir şekilde güncellenmiştir. 

## 1. `qz-tray.js` Dosyasının Projeye Eklenmesi
Sistemin çalışabilmesi için `qz-tray.js` kütüphanesinin şablonlara (veya base template'in `<head>` veya `<body>` kısmına, `nuvia-bridge.js`'den **önce**) yüklenmesi gerekmektedir.
Örnek kullanım (`base.html` içerisinde):
```html
<script src="{% static 'js/qz-tray.js' %}"></script>
<script src="{% static 'js/nuvia-bridge.js' %}"></script>
<script src="{% static 'js/nuvia-print-manager.js' %}"></script>
```

## 2. QZ Tray Sertifika Alım İşlemi (Production)
Tasarım modunda/geliştirmede uygulamanın uyarı vermeden yazdırma yapabilmesi için `nuvia-bridge.js` dosyasında `setCertificatePromise` ve `setSignaturePromise` fonksiyonları "bypass" edilmiş gibi gösterilmiştir. Ancak üretim (production) sırasında QZ Tray kullanıcılara *"X uygulamasının yazıcıya erişimine izin veriyor musunuz?"* uyarısı çıkarabilir ve güvenlik ihlallerine karşı kısıtlayabilir.
- **Kalıcı Çözüm:** [qz.io](https://qz.io) üzerinden bir SSL/Digital Certificate oluşturmak, imzalama dosyasını Django sunucusu üzerinden okutup onay sürecini şeffaf hale getirmektir. İlgili `TODO` satırları `nuvia-bridge.js` dosyasında işaret edilmiştir.

## 3. Yazıcısız Test Etme İmkanı
Yeni süreçte eğer fiziksel bir `Xprinter` ya da Zebra yazıcı bağlanmamışsa bile yazdırma süreçleri test edilebilir. QZ Tray'in **Yazıcı Simülatöründen** veya Windows "Microsoft Print to PDF" yazıcıyı kullanarak yazıcı varlığını doğrulayabilir, akışlardaki hata yönetimini test edebilirsiniz.

## 4. Eski Sisteme Göre Breaking Changes (Kritik Değişiklikler)
- **Port Numarası Değişti:** Eski yerel print agent `9876` portunu kullanmaktaydı, QZ Tray standartlarında wss/ws üzerinden `8181` vb. seri aralıklardaki portları otomatik kullanılmaktadır.
- **Kurulum Değişikliği:** İstemci makinesinde artık `NuviaButikPrintAgent-Installer.bat` dosyasına ve servisine **gerek yoktur**. QZ Tray'in resmi istemcisi bilgisayara yetkilendirilmiş şekilde kurulmalıdır.
- **HTTP Fallback Kaldırıldı:** QZ Tray standartlarında Websocket hatasız yönetildiği için güvensiz ve karmaşık HTTP Fallback metodu devreden çıkarılmıştır.

## 5. View Snippet Kullanımı
UI bileşenlerine bağlandığını göstermek adına yeni oluşturulan `etiket_status_widget.html` componenti dilediğiniz herhangi bir sayfada (örneğin butonların yanına) şu şekilde dahil edilmelidir:

```django
{% include "urun/etiket_status_widget.html" %}
```
