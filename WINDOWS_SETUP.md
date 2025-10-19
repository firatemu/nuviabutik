# NuviaButik Print Agent - Windows Kurulum

## Yeni HTTP Bridge Versiyonu!

**Event loop sorunları çözüldü!** Artık iki agent versiyonu var:
- `xprinter_agent.py` - WebSocket versiyonu (orijinal)
- `xprinter_agent_http.py` - HTTP Bridge versiyonu (önerilen)

## 1. Gereksinimler
- Windows 10/11
- Python 3.8+ (önerilir: Python 3.13)
- Xprinter XP-470B yazıcı
- TSC driver (Seagull Software)

## 2. Python Paketleri Kurulumu

```cmd
# Gerekli paketleri yükle
pip install websockets pywin32

# Veya requirements dosyasından
pip install -r windows_requirements.txt
```

## 3. Yazıcı Kurulumu Kontrolü

Yazıcınızın doğru kurulduğunu kontrol edin:

### Yazıcı Bilgileriniz:
- **Model**: Xprinter XP-470B
- **Port**: USB001
- **Driver**: Seagull TSC
- **Server**: NUVIA

### Kontrol Adımları:
1. Windows Settings > Printers & scanners
2. "Xprinter XP-470B" görünüyor mu?
3. Yazıcı "Ready" durumunda mı?

## 4. Agent'ı Çalıştırma

### Önerilen: HTTP Bridge Versiyonu
```cmd
# Event loop sorunları olmayan versiyon
python xprinter_agent_http.py
```

### Alternatif: WebSocket Versiyonu
```cmd
# Orijinal WebSocket versiyonu
python xprinter_agent.py
```

## 5. Test

1. Agent GUI'sinde "🧪 Test Yazdır" butonuna tıklayın
2. Test etiketi yazdırılmalı
3. Bağlantı türü:
   - HTTP Bridge: `http://localhost:9876`
   - WebSocket: `ws://localhost:9876`

## 6. Web Sayfası Bağlantısı

Agent çalıştıktan sonra:
1. NuviaButik web sayfasını açın
2. Bir ürün etiketini yazdırmayı deneyin
3. Console'da bağlantı mesajlarını kontrol edin

## 7. Sorun Giderme

### "Yazıcı bulunamadı" Hatası
1. Yazıcının USB bağlantısını kontrol edin
2. Driver'ın doğru yüklendiğini kontrol edin
3. Windows'ta varsayılan yazıcı olarak ayarlayın
4. Agent'ta "🔄 Yazıcıları Yenile" butonuna tıklayın

### "WebSocket bağlantı hatası"
1. Windows Firewall'u kontrol edin
2. Port 9876'in açık olduğunu kontrol edin
3. Antivirus yazılımını kontrol edin
4. Agent'ı "Yönetici olarak çalıştır"

### "Test yazdırması başarısız"
1. Yazıcıda kağıt var mı?
2. Yazıcı hazır durumda mı?
3. USB kablosu sağlam mı?
4. Driver güncel mi?

## 8. Log Dosyası

Sorun yaşarsanız log dosyasını kontrol edin:
- Konum: `C:\NuviaButik\print_agent.log`
- Tüm işlemler loglanır
- Hata mesajları burada görünür

## 9. Önemli Notlar

- Agent Windows'ta çalışmalı (Linux'ta çalışmaz)
- WebSocket port: 9876
- ZPL format kullanılır
- NUVIA branding ile etiketler
- TSC driver gerekli

## 10. Yardım

Agent çalışmazsa:
1. Log dosyasını kontrol edin
2. Python versiyonunu kontrol edin: `python --version`
3. Paket kurulumunu kontrol edin: `pip list`
4. Yazıcı driver'ını yeniden kurun