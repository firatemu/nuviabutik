// ZXing ile basit kamera kodu
async function startCamera() {
    try {
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const isAndroid = /Android/i.test(navigator.userAgent);
        const isMobile = isIOS || isAndroid;
        
        cameraArea.classList.remove('d-none');
        cameraBtn.disabled = true;
        cameraBtn.innerHTML = '<i class=" fas fa-spinner fa-spin\></i> <span class=\d-none d-md-inline\>Başlatılıyor...</span>';
 
 // ZXing kütüphanesini başlat
 if (typeof ZXing === 'undefined') {
 throw new Error('ZXing kütüphanesi yüklenmemiş');
 }
 
 const codeReader = new ZXing.BrowserMultiFormatReader();
 window.codeReader = codeReader;
 
 // Cihaz listesi al
 let videoInputDevices = [];
 try {
 videoInputDevices = await codeReader.listVideoInputDevices();
 } catch (err) {
 console.log('Kamera listesi alma hatası, fallback:', err);
 const devices = await navigator.mediaDevices.enumerateDevices();
 videoInputDevices = devices.filter(device => device.kind === 'videoinput');
 }
 
 if (videoInputDevices.length === 0) {
 throw new Error('Hiç kamera bulunamadı');
 }
 
 // Arka kamera seç
 let selectedDeviceId = videoInputDevices[0].deviceId;
 if (isMobile && videoInputDevices.length > 1) {
 const backCamera = videoInputDevices.find(device =>
 device.label && (
 device.label.toLowerCase().includes('back') ||
 device.label.toLowerCase().includes('rear') ||
 device.label.toLowerCase().includes('environment')
 )
 );
 if (backCamera) {
 selectedDeviceId = backCamera.deviceId;
 } else {
 selectedDeviceId = videoInputDevices[videoInputDevices.length - 1].deviceId;
 }
 }
 
 console.log('Kamera başlatılıyor:', selectedDeviceId);
 
 // ZXing ile tarama başlat
 await codeReader.decodeFromVideoDevice(selectedDeviceId, 'preview', (result, err) => {
 if (result) {
 const code = result.getText();
 console.log('Barkod okundu:', code);
 
 // Titreşim
 if (navigator.vibrate) {
 navigator.vibrate([200, 100, 200]);
 }
 
 // Sonucu göster
 scannedCode.textContent = code;
 scanResult.classList.remove('d-none');
 barkodInput.value = code;
 
 // Kamerayı durdur ve arama yap
 stopCamera();
 setTimeout(() => barkodForm.submit(), 1500);
 }
 if (err && !(err instanceof ZXing.NotFoundException)) {
 console.error('Okuma hatası:', err);
 }
 });
 
 isScanning = true;
 cameraBtn.innerHTML = '<i class=\fas fa-camera\></i> <span class=\d-none d-md-inline\>Kamera Açık</span>';
 cameraBtn.classList.remove('btn-success');
 cameraBtn.classList.add('btn-warning');
 
 // Scroll to camera
 cameraArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
 
 } catch (err) {
 console.error('Kamera başlatma hatası:', err);
 let errorMessage = 'Kamera başlatılamadı.';
 
 if (err.name === 'NotAllowedError') {
 errorMessage = 'Kamera izni reddedildi. Lütfen tarayıcı ayarlarından kamera erişimine izin verin.';
 } else if (err.name === 'NotFoundError') {
 errorMessage = 'Kamera bulunamadı.';
 } else if (err.message) {
 errorMessage = err.message;
 }
 
 alert(errorMessage);
 stopCamera();
 }
}

function stopCamera() {
 if (window.codeReader) {
 window.codeReader.reset();
 }
 isScanning = false;
 cameraArea.classList.add('d-none');
 cameraBtn.disabled = false;
 cameraBtn.innerHTML = '<i class=\fas fa-camera\></i> <span class=\d-none d-md-inline\>Kamera</span><span class=\d-md-none\></span>';
 cameraBtn.classList.remove('btn-warning');
 cameraBtn.classList.add('btn-success');
 scanResult.classList.add('d-none');
 
 setTimeout(() => barkodInput.focus(), 300);
}
