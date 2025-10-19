from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserSession, UserActivityLog, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Özelleştirilmiş kullanıcı admin paneli"""
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at', 'last_login')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Ek Bilgiler', {
            'fields': ('role', 'phone_number', 'address', 'birth_date', 'created_by')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:  # Düzenleme modunda
            readonly_fields.extend(['username', 'created_by'])
        return readonly_fields


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Kullanıcı profil admin paneli"""
    
    list_display = ('user', 'department', 'hire_date', 'salary')
    list_filter = ('department', 'hire_date')
    search_fields = ('user__username', 'user__email', 'department')
    
    fieldsets = (
        ('Kullanıcı Bilgileri', {
            'fields': ('user',)
        }),
        ('Profil Bilgileri', {
            'fields': ('profile_picture', 'department', 'hire_date', 'salary')
        }),
        ('İletişim Bilgileri', {
            'fields': ('emergency_contact', 'emergency_phone')
        }),
        ('Notlar', {
            'fields': ('notes',)
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Kullanıcı oturum admin paneli"""
    
    list_display = ('user', 'ip_address', 'login_time', 'logout_time', 'is_active')
    list_filter = ('is_active', 'login_time', 'logout_time')
    search_fields = ('user__username', 'ip_address', 'user_agent')
    ordering = ('-login_time',)
    
    readonly_fields = ('session_key', 'user_agent', 'login_time')
    
    fieldsets = (
        ('Oturum Bilgileri', {
            'fields': ('user', 'session_key', 'ip_address', 'is_active')
        }),
        ('Zaman Bilgileri', {
            'fields': ('login_time', 'logout_time')
        }),
        ('Teknik Bilgiler', {
            'fields': ('user_agent',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """Kullanıcı aktivite log admin paneli"""
    
    list_display = ('user', 'action', 'content_type', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'content_type')
    search_fields = ('user__username', 'description', 'ip_address')
    ordering = ('-timestamp',)
    
    readonly_fields = ('user', 'action', 'content_type', 'object_id', 'description', 'ip_address', 'timestamp')
    
    fieldsets = (
        ('Aktivite Bilgileri', {
            'fields': ('user', 'action', 'content_type', 'object_id')
        }),
        ('Detaylar', {
            'fields': ('description', 'ip_address', 'timestamp')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Satış Elemanı için özel Proxy Model ve Admin
class SaticiProxy(CustomUser):
    """Satış elemanları için proxy model"""
    class Meta:
        proxy = True
        verbose_name = "Satış Elemanı"
        verbose_name_plural = "Satış Elemanları"


@admin.register(SaticiProxy)
class SaticiAdmin(admin.ModelAdmin):
    """Satış elemanları için özel admin paneli"""
    
    list_display = ('username', 'get_full_name', 'email', 'phone_number', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    actions = ['assign_role_permissions']
    
    fieldsets = (
        ('Kişisel Bilgiler', {
            'fields': ('username', 'password', 'first_name', 'last_name', 'email')
        }),
        ('İletişim Bilgileri', {
            'fields': ('phone_number', 'address')
        }),
        ('Rol ve Yetki', {
            'fields': ('role', 'is_active', 'is_staff')
        }),
        ('Ek Bilgiler', {
            'fields': ('birth_date',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Sadece satış ile ilgili rolleri göster"""
        return super().get_queryset(request).filter(
            role__in=['admin', 'manager', 'cashier', 'satici']
        )
    
    def get_full_name(self, obj):
        """Tam ad gösterimi"""
        return f"{obj.first_name} {obj.last_name}" if obj.first_name and obj.last_name else obj.username
    get_full_name.short_description = "Ad Soyad"
    
    def save_model(self, request, obj, form, change):
        """Kayıt sırasında otomatik işlemler"""
        if not change:  # Yeni kayıt
            obj.created_by = request.user
            # Satış elemanı rolü belirlenmemişse otomatik ata
            if not obj.role or obj.role not in ['admin', 'manager', 'cashier', 'satici']:
                obj.role = 'satici'
        
        # Satış yapabilir rollerde is_staff'ı True yap
        if obj.role in ['admin', 'manager', 'cashier', 'satici']:
            obj.is_staff = True
        
        super().save_model(request, obj, form, change)
        
        # Rol izinlerini otomatik ata
        self.assign_permissions_to_user(obj)
    
    def assign_permissions_to_user(self, user):
        """Kullanıcıya rol bazlı izinleri ata"""
        from django.contrib.auth.models import Permission
        
        # Mevcut izinleri temizle
        user.user_permissions.clear()
        
        # Rol bazlı izin setleri
        role_permissions = {
            'admin': [
                # Tüm izinler
                'add_customuser', 'change_customuser', 'delete_customuser', 'view_customuser',
                'add_satis', 'change_satis', 'delete_satis', 'view_satis',
                'add_urun', 'change_urun', 'delete_urun', 'view_urun',
                'add_musteri', 'change_musteri', 'delete_musteri', 'view_musteri',
                'add_kasa', 'change_kasa', 'delete_kasa', 'view_kasa',
            ],
            'manager': [
                # Yönetici izinleri (kullanıcı silme hariç)
                'add_customuser', 'change_customuser', 'view_customuser',
                'add_satis', 'change_satis', 'view_satis',
                'add_urun', 'change_urun', 'view_urun',
                'add_musteri', 'change_musteri', 'view_musteri',
                'view_kasa',
            ],
            'cashier': [
                # Kasiyer izinleri
                'add_satis', 'change_satis', 'view_satis',
                'view_urun', 'change_urun',
                'add_musteri', 'change_musteri', 'view_musteri',
                'view_kasa',
            ],
            'satici': [
                # Satış elemanı izinleri
                'add_satis', 'view_satis',
                'view_urun',
                'add_musteri', 'view_musteri',
            ]
        }
        
        if user.role in role_permissions:
            permissions = Permission.objects.filter(
                codename__in=role_permissions[user.role]
            )
            user.user_permissions.set(permissions)
    
    def assign_role_permissions(self, request, queryset):
        """Seçili kullanıcılara rol izinlerini ata"""
        count = 0
        for user in queryset:
            self.assign_permissions_to_user(user)
            count += 1
        
        self.message_user(
            request,
            f"{count} kullanıcıya rol izinleri başarıyla atandı."
        )
    assign_role_permissions.short_description = "Seçili kullanıcılara rol izinlerini ata"
