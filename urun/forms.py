from django import forms
from .models import Urun, UrunKategoriUst, Marka, UrunVaryanti, StokHareket


class UrunForm(forms.ModelForm):
    """Ana ürün formu"""
    
    class Meta:
        model = Urun
        fields = [
            'urun_kodu', 'ad', 'aciklama', 'kategori', 'marka', 'cinsiyet', 'birim',
            'varyasyonlu', 'alis_fiyati', 'kar_orani',
            'satis_fiyati', 'kritik_stok_seviyesi',
            'resim', 'aktif', 'stok_takibi'
        ]
        
        widgets = {
            'urun_kodu': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Otomatik oluşturulacak'
            }),
            'ad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ürün adını girin'
            }),
            'aciklama': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ürün açıklaması (opsiyonel)'
            }),
            'kategori': forms.Select(attrs={
                'class': 'form-select'
            }),
            'marka': forms.Select(attrs={
                'class': 'form-select'
            }),
            'cinsiyet': forms.Select(attrs={
                'class': 'form-select'
            }),
            'birim': forms.Select(attrs={
                'class': 'form-select'
            }),
            'varyasyonlu': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'varyasyon_tipleri': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'alis_fiyati': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'kar_orani': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1000',
                'placeholder': '50.00'
            }),
            'satis_fiyati': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
                'readonly': True
            }),
            'kritik_stok_seviyesi': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '5'
            }),
            'resim': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'aktif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'stok_takibi': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marka alanını opsiyonel yap
        self.fields['marka'].required = False
        self.fields['marka'].empty_label = "Marka Seçin"
        
        # Fiyat alanlarını opsiyonel yap
        self.fields['alis_fiyati'].required = False
        self.fields['satis_fiyati'].required = False


class UrunVaryantiForm(forms.ModelForm):
    """Ürün varyantı formu"""
    
    class Meta:
        model = UrunVaryanti
        fields = [
            'barkod', 'renk', 'beden',
            'stok_miktari', 'ek_aciklama', 'resim', 'aktif'
        ]
        
        widgets = {
            'barkod': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Otomatik oluşturulacak'
            }),
            'renk': forms.Select(attrs={
                'class': 'form-select'
            }),
            'beden': forms.Select(attrs={
                'class': 'form-select'
            }),
            'stok_miktari': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'ek_aciklama': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ek açıklama (opsiyonel)'
            }),
            'resim': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'aktif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tüm varyasyon alanlarını opsiyonel yap
        self.fields['renk'].required = False
        self.fields['beden'].required = False
        
        # Empty label'lar
        self.fields['renk'].empty_label = "Renk Seçin"
        self.fields['beden'].empty_label = "Beden Seçin"


class MarkaForm(forms.ModelForm):
    """Marka formu"""
    
    class Meta:
        model = Marka
        fields = ['ad', 'aciklama', 'logo', 'aktif']
        
        widgets = {
            'ad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Marka adını girin'
            }),
            'aciklama': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Marka açıklaması (opsiyonel)'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'aktif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aciklama'].required = False
        self.fields['logo'].required = False


class StokGirisForm(forms.Form):
    """Stok giriş formu"""
    varyant = forms.ModelChoiceField(
        queryset=UrunVaryanti.objects.filter(aktif=True, stok_kaydedildi=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label="Ürün Varyantı",
        help_text="Stok girişi yapılacak ürün varyantını seçin"
    )
    
    miktar = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Giriş miktarı',
            'required': True
        }),
        label="Giriş Miktarı",
        help_text="Stoka eklenecek miktar"
    )
    
    aciklama = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Stok giriş açıklaması (zorunlu)',
            'required': True
        }),
        label="Açıklama",
        help_text="Stok giriş sebebini açıklayın (tedarikçi, iade, vs.)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Varyantları daha anlaşılır şekilde göster
        self.fields['varyant'].queryset = UrunVaryanti.objects.filter(
            aktif=True, 
            stok_kaydedildi=True
        ).select_related('urun', 'renk', 'beden')


class StokCikisForm(forms.Form):
    """Stok çıkış formu"""
    varyant = forms.ModelChoiceField(
        queryset=UrunVaryanti.objects.filter(aktif=True, stok_kaydedildi=True, stok_miktari__gt=0),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label="Ürün Varyantı",
        help_text="Stok çıkışı yapılacak ürün varyantını seçin"
    )
    
    miktar = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Çıkış miktarı',
            'required': True
        }),
        label="Çıkış Miktarı",
        help_text="Stoktan çıkarılacak miktar"
    )
    
    aciklama = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Stok çıkış açıklaması (zorunlu)',
            'required': True
        }),
        label="Açıklama",
        help_text="Stok çıkış sebebini açıklayın (fire, hasar, vs.)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['varyant'].queryset = UrunVaryanti.objects.filter(
            aktif=True, 
            stok_kaydedildi=True,
            stok_miktari__gt=0
        ).select_related('urun', 'renk', 'beden')

    def clean(self):
        cleaned_data = super().clean()
        varyant = cleaned_data.get('varyant')
        miktar = cleaned_data.get('miktar')
        
        if varyant and miktar:
            if miktar > varyant.stok_miktari:
                raise forms.ValidationError(
                    f"Çıkış miktarı ({miktar}) mevcut stok miktarından ({varyant.stok_miktari}) fazla olamaz!"
                )
        
        return cleaned_data


class StokDuzeltmeForm(forms.Form):
    """Stok düzeltme formu"""
    varyant = forms.ModelChoiceField(
        queryset=UrunVaryanti.objects.filter(aktif=True, stok_kaydedildi=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label="Ürün Varyantı",
        help_text="Stok düzeltmesi yapılacak ürün varyantını seçin"
    )
    
    yeni_miktar = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Yeni stok miktarı',
            'required': True
        }),
        label="Yeni Stok Miktarı",
        help_text="Doğru stok miktarını girin"
    )
    
    aciklama = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Stok düzeltme açıklaması (zorunlu)',
            'required': True
        }),
        label="Açıklama",
        help_text="Stok düzeltme sebebini açıklayın (sayım, hata düzeltme, vs.)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['varyant'].queryset = UrunVaryanti.objects.filter(
            aktif=True, 
            stok_kaydedildi=True
        ).select_related('urun', 'renk', 'beden')


class StokSayimForm(forms.Form):
    """Stok sayım formu"""
    varyant = forms.ModelChoiceField(
        queryset=UrunVaryanti.objects.filter(aktif=True, stok_kaydedildi=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label="Ürün Varyantı",
        help_text="Stok sayımı yapılacak ürün varyantını seçin"
    )
    
    sayim_miktari = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sayım sonucu miktar',
            'required': True
        }),
        label="Sayım Miktarı",
        help_text="Fiziksel sayım sonucunda bulunan miktar"
    )
    
    aciklama = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Stok sayım açıklaması (zorunlu)',
            'required': True
        }),
        label="Açıklama",
        help_text="Sayım detaylarını açıklayın (tarih, sayım yapan kişi, vs.)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['varyant'].queryset = UrunVaryanti.objects.filter(
            aktif=True, 
            stok_kaydedildi=True
        ).select_related('urun', 'renk', 'beden')
