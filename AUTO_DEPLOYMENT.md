# GitHub Actions Otomatik Deployment Kurulum Rehberi

## 🔑 GitHub Secrets Kurulumu

GitHub repository'nizde Settings > Secrets and variables > Actions bölümünde aşağıdaki secret'ları ekleyin:

### Gerekli Secrets:

1. **SSH_HOST**
   - Value: `31.57.33.34`

2. **SSH_USER** 
   - Value: `root`

3. **SSH_PRIVATE_KEY**
   - SSH private key'inizin içeriği
   - Key oluşturmak için sunucuda: `ssh-keygen -t rsa -b 4096 -C "github-actions"`
   - Private key: `cat ~/.ssh/id_rsa` (tamamını kopyalayın)
   - Public key'i authorized_keys'e ekleyin: `cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys`

## 🚀 Nasıl Çalışır?

1. **Kod değişikliği yapıp GitHub'a push atın**
   ```bash
   git add .
   git commit -m "feature: yeni özellik eklendi"
   git push origin main
   ```

2. **GitHub Actions otomatik tetiklenir**
   - Actions sekmesinde progress'i takip edebilirsiniz

3. **Deployment süreci (yaklaşık 2-3 dakika):**
   - ✅ Kod checkout
   - ✅ SSH bağlantı kurma
   - ✅ Sunucuda backup alma
   - ✅ Git pull (son kodları çekme)
   - ✅ Dependencies güncelleme
   - ✅ Database migration
   - ✅ Static files toplama
   - ✅ Servisleri restart etme
   - ✅ Health check

4. **Başarılı deployment sonrası site otomatik güncellenir**

## 📋 Manuel Deployment (Sunucuda)

Eğer GitHub Actions kullanmak istemezseniz, sunucuda manuel deployment:

```bash
cd /var/www/nuviabutik
chmod +x server_deploy.sh
./server_deploy.sh
```

## 🔍 Deployment Logları

- GitHub Actions logları: GitHub > Actions sekmesi
- Sunucu deployment logları: `/var/log/deployment.log`
- Service logları: `journalctl -u nuviabutik -f`

## 🚨 Rollback (Geri Alma)

Eğer deployment hata verirse:

```bash
cd /var/backups/nuviabutik
ls -la  # backup listesi
cp -r nuviabutik_backup_YYYYMMDD_HHMMSS/* /var/www/nuviabutik/
systemctl restart nuviabutik nginx
```

## ⚡ Özellikler

- ✅ **Otomatik backup** (her deployment öncesi)
- ✅ **Zero-downtime deployment** (hızlı restart)
- ✅ **Health check** (deployment sonrası test)
- ✅ **Rollback desteği** (hata durumunda geri alma)
- ✅ **Detailed logging** (detaylı loglar)
- ✅ **Safety checks** (güvenlik kontrolleri)

## 🔧 İlk Kurulum

1. GitHub Secrets'ları ekleyin
2. SSH key'lerini sunucuda yapılandırın
3. Bu dosyaları commit edip push edin
4. GitHub Actions'ın çalıştığını kontrol edin

**Not:** İlk deployment'ta SSH connection error alabilirsiniz. Bu durumda SSH key'lerinizi kontrol edin.
