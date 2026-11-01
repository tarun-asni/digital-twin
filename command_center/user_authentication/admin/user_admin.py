from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from user_authentication.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_locked', 'failed_login_attempts', 'last_login')
    list_filter = ('role', 'is_locked', 'is_active', 'is_active', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('role', 'failed_login_attempts', 'is_locked', 'is_active', 'is_staff', 'is_superuser'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_staff'),
        }),
    )
    
    filter_horizontal = ()
    
    search_fields = ('username', 'email')
    ordering = ('username',)
    
    actions = ['unlock_accounts']
    
    def unlock_accounts(self, request, queryset):
        unlocked = 0
        for user in queryset.filter(is_locked=True):
            user.unlock_account()
            unlocked += 1
        self.message_user(request, f"{unlocked} account(s) unlocked.")
    unlock_accounts.short_description = "Unlock selected locked accounts"