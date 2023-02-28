from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserTier, AppUser, UploadedImage

class AppUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('User tier', {'fields': ('tier',)}),
    )

admin.site.register(AppUser,AppUserAdmin)
admin.site.register(UploadedImage)

@admin.register(UserTier)
class UserTierAdmin(admin.ModelAdmin):
    list_display = ['name']

# Register your models here.