#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Barkod template'ini ZXing ile çalışacak şekilde güncelle

# Orijinal template'i oku
with open('templates/urun/barkod_sorgula.html', 'r', encoding='utf-8') as f:
    content = f.read()

# QuaggaJS kodunu ZXing ile değiştir
old_js = '''Quagga.init({
            inputStream: {
                name: " Live\,
 type: \LiveStream\,
 target: document.querySelector('#preview'),
 constraints: {
 width: 480,
 height: 320,
 facingMode: isMobile ? \environment\ : \user\ // Mobilde arka kamera
 }
 },
 locator: {
 patchSize: \medium\,
 halfSample: true
 },
 numOfWorkers: 2,
 frequency: 10,
 decoder: {
 readers: [
 \code_128_reader\,
 \ean_reader\,
 \ean_8_reader\,
 \code_39_reader\,
 \upc_reader\
 ]
 },
 locate: true
 }, function(err) {
 if (err) {
 console.error('Kamera başlatma hatası:', err);
 alert('Kamera başlatılamadı: ' + err.message);
 stopCamera();
 return;
 }

 console.log(\Kamera başlatıldı\);
 isScanning = true;
 cameraBtn.innerHTML = '<i class=\fas fa-camera\></i> <span class=\d-none d-md-inline\>Kamera Açık</span>';
 cameraBtn.classList.remove('btn-success');
 cameraBtn.classList.add('btn-warning');

 Quagga.start();
 });

 // Barkod okuma olayı
 Quagga.onDetected(function(data) {
 const code = data.codeResult.code;
 console.log(\Barkod okundu:\, code);

 // Titreşim efekti (mobil cihazlarda)
 if (navigator.vibrate) {
 navigator.vibrate([200, 100, 200]);
 }

 // Sonucu göster
 scannedCode.textContent = code;
 scanResult.classList.remove('d-none');

 // Input'a yaz
 barkodInput.value = code;

 // Kamerayı durdur
 stopCamera();

 // Otomatik arama yap
 setTimeout(() => {
 barkodForm.submit();
 }, 1500);
 });'''

new_js = '''// ZXing ile kamera başlat
 try {
 const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
 const isAndroid = /Android/i.test(navigator.userAgent);
 
 // ZXing kütüphanesini başlat
 const codeReader = new ZXing.BrowserMultiFormatReader();
 
 // Kamera cihazlarını listele
 let videoInputDevices = [];
 try {
 if (isIOS) {
 const devices = await navigator.mediaDevices.enumerateDevices();
 videoInputDevices = devices.filter(device => device.kind === 'videoinput');
 } else {
 videoInputDevices = await codeReader.listVideoInputDevices();
 }
 } catch (err) {
 console.log('Kamera listesi alma hatası, fallback yöntem:', err);
 const devices = await navigator.mediaDevices.enumerateDevices();
 videoInputDevices = devices.filter(device => device.kind === 'videoinput');
 }
 
 if (videoInputDevices.length === 0) {
 throw new Error('Hiç kamera bulunamadı');
 }
 
 // Arka kamera seçimi
 let selectedDeviceId;
 if (isIOS || isAndroid) {
 selectedDeviceId = videoInputDevices.find(device =>
 device.label && (
 device.label.toLowerCase().includes('back') ||
 device.label.toLowerCase().includes('rear') ||
 device.label.toLowerCase().includes('environment') ||
 device.label.toLowerCase().includes('wide') ||
 device.label.toLowerCase().includes('main')
 )
 )?.deviceId;
 
 if (!selectedDeviceId && videoInputDevices.length > 1) {
 selectedDeviceId = videoInputDevices[videoInputDevices.length - 1].deviceId;
 } else if (!selectedDeviceId) {
 selectedDeviceId = videoInputDevices[0].deviceId;
 }
 } else {
 selectedDeviceId = videoInputDevices[0].deviceId;
 }
 
 console.log('Seçilen kamera ID:', selectedDeviceId);
 
 // ZXing ile tarama başlat
 await codeReader.decodeFromVideoDevice(selectedDeviceId, 'preview', (result, err) => {
 if (result) {
 const code = result.getText();
 console.log('Barkod okundu:', code);
 
 // Titreşim efekti (mobil cihazlarda)
 if (navigator.vibrate) {
 navigator.vibrate([200, 100, 200]);
 }
 
 // Sonucu göster
 scannedCode.textContent = code;
 scanResult.classList.remove('d-none');
 
 // Input'a yaz
 barkodInput.value = code;
 
 // Kamerayı durdur
 stopCamera();
 
 // Otomatik arama yap
 setTimeout(() => {
 barkodForm.submit();
 }, 1500);
 }
 if (err && err instanceof ZXing.NotFoundException) {
 // Barkod bulunamadı, devam et
 console.log('Barkod aranıyor...');
 }
 if (err && !(err instanceof ZXing.NotFoundException)) {
 console.error('Okuma hatası:', err);
 }
 });
 
 isScanning = true;
 cameraBtn.innerHTML = '<i class=\fas fa-camera\></i> <span class=\d-none d-md-inline\>Kamera Açık</span>';
 cameraBtn.classList.remove('btn-success');
 cameraBtn.classList.add('btn-warning');
 
 } catch (err) {
 console.error('Kamera başlatma hatası:', err);
 let errorMessage = 'Kamera başlatılamadı: ' + err.message;
 
 if (err.name === 'NotAllowedError') {
 if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
 errorMessage = ' iOS: Ayarlar Safari Kamera erişimine izin verin ve sayfayı yenileyin.';
 } else {
 errorMessage = 'Kamera izni reddedildi. Lütfen tarayıcı ayarlarınızdan kamera erişimine izin verin.';
 }
 } else if (err.name === 'NotFoundError') {
 errorMessage = 'Kamera bulunamadı. Cihazınızda kamera olduğundan emin olun.';
 } else if (err.name === 'NotSupportedError') {
 errorMessage = 'Tarayıcınız kamera özelliğini desteklemiyor.';
 } else if (err.name === 'NotReadableError') {
 errorMessage = 'Kamera kullanımda. Diğer uygulamaları kapatıp tekrar deneyin.';
 }
 
 alert(errorMessage);
 stopCamera();
 }'''

# Değiştir
content = content.replace(old_js, new_js)

# stopCamera fonksiyonunu güncelle
old_stop = '''function stopCamera() {
 if (isScanning) {
 Quagga.stop();
 isScanning = false;
 }

 cameraArea.classList.add('d-none');
 cameraBtn.disabled = false;
 cameraBtn.innerHTML = '<i class=\fas fa-camera\></i> <span class=\d-none d-md-inline\>Kamera</span><span class=\d-md-none\></span>';
 cameraBtn.classList.remove('btn-warning');
 cameraBtn.classList.add('btn-success');
 scanResult.classList.add('d-none');

 // Input'a odaklan
 setTimeout(() => {
 barkodInput.focus();
 }, 300);
 }'''

new_stop = '''function stopCamera() {
 if (isScanning) {
 // ZXing codeReader'ı durdur
 if (window.codeReader) {
 window.codeReader.reset();
 }
 isScanning = false;
 }

 cameraArea.classList.add('d-none');
 cameraBtn.disabled = false;
 cameraBtn.innerHTML = '<i class=\fas fa-camera\></i> <span class=\d-none d-md-inline\>Kamera</span><span class=\d-md-none\></span>';
 cameraBtn.classList.remove('btn-warning');
 cameraBtn.classList.add('btn-success');
 scanResult.classList.add('d-none');

 // Input'a odaklan
 setTimeout(() => {
 barkodInput.focus();
 }, 300);
 }'''

content = content.replace(old_stop, new_stop)

# startCamera fonksiyonunu async yap
content = content.replace('function startCamera() {', 'async function startCamera() {')

# Değişken tanımlarını güncelle
old_vars = '''let isScanning = false;'''
new_vars = '''let isScanning = false;
 let codeReader = null;'''

content = content.replace(old_vars, new_vars)

# window.codeReader referansını ekle
content = content.replace('// ZXing ile kamera başlat', '''// ZXing ile kamera başlat
 window.codeReader = new ZXing.BrowserMultiFormatReader();
 const codeReader = window.codeReader;''')

# Dosyayı kaydet
with open('templates/urun/barkod_sorgula.html', 'w', encoding='utf-8') as f:
 f.write(content)

print('Barkod template ZXing ile güncellendi!')
