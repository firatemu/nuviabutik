#!/bin/bash
#
# Template Fiyat Güncelleme Scripti
# satis_fiyati → pesin_fiyat ve taksitli_fiyat'a günceller
#

TEMPLATE_DIR="/var/www/nuviabutik/templates"
BACKUP_DIR="/var/backups/nuviabutik/templates_$(date +%Y%m%d_%H%M%S)"

echo "================================================"
echo "TEMPLATE FİYAT GÜNCELLEMESİ"
echo "================================================"
echo ""

# Yedek al
echo "📦 Yedek alınıyor..."
mkdir -p "$BACKUP_DIR"
cp -r "$TEMPLATE_DIR" "$BACKUP_DIR/"
echo "✅ Yedek: $BACKUP_DIR"
echo ""

# Güncelleme yapılacak dosyaları bul
FILES=$(grep -rl "\.satis_fiyati" "$TEMPLATE_DIR" 2>/dev/null)

if [ -z "$FILES" ]; then
    echo "⚠️  Güncellenecek dosya bulunamadı!"
    exit 0
fi

echo "📋 Güncellenecek dosyalar:"
echo "$FILES" | while read file; do
    echo "  - ${file#$TEMPLATE_DIR/}"
done
echo ""

TOPLAM=$(echo "$FILES" | wc -l)
echo "📊 Toplam: $TOPLAM dosya"
echo ""

# Onay al
read -p "❓ Devam etmek istiyor musunuz? (yes/no): " ONAY

if [ "$ONAY" != "yes" ] && [ "$ONAY" != "y" ]; then
    echo "❌ İşlem iptal edildi."
    exit 0
fi

echo ""
echo "🚀 Güncelleme başlatılıyor..."
echo ""

BASARILI=0
HATALI=0

# Her dosyayı güncelle
echo "$FILES" | while read file; do
    if [ -f "$file" ]; then
        echo "📝 İşleniyor: ${file#$TEMPLATE_DIR/}"
        
        # Basit değişiklik: urun.satis_fiyati → urun.pesin_fiyat
        # NOT: Bu basit bir değişiklik, daha karmaşık durumlarda manuel kontrol gerekebilir
        
        # Geçici dosya oluştur
        TMP_FILE="${file}.tmp"
        
        # Değiştir (dikkatli olun, sadece temel değişiklikler)
        sed -e 's/urun\.satis_fiyati/urun.pesin_fiyat/g' \
            -e 's/v\.urun\.satis_fiyati/v.urun.pesin_fiyat/g' \
            -e 's/item\.urun\.satis_fiyati/item.urun.pesin_fiyat/g' \
            -e 's/product\.satis_fiyati/product.pesin_fiyat/g' \
            "$file" > "$TMP_FILE"
        
        # Başarılı ise değiştir
        if [ $? -eq 0 ]; then
            mv "$TMP_FILE" "$file"
            echo "  ✅ Başarılı"
            ((BASARILI++))
        else
            rm -f "$TMP_FILE"
            echo "  ❌ Hata"
            ((HATALI++))
        fi
    fi
done

echo ""
echo "================================================"
echo "✅ GÜNCELLEME TAMAMLANDI"
echo "================================================"
echo "✅ Başarılı: $BASARILI"
[ $HATALI -gt 0 ] && echo "❌ Hatalı: $HATALI"
echo ""
echo "💾 Yedek: $BACKUP_DIR"
echo ""
echo "⚠️  DİKKAT: Değişiklikleri manuel kontrol edin!"
echo "   Bazı template'ler özel düzenleme gerektirebilir."
echo ""

