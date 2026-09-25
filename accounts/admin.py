from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile, APIToken


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'پروفایل دانش‌آموز'
    fk_name = 'user'


# accounts/admin.py
# فقط fieldsets تغییر‌یافته

class CustomUserAdmin(UserAdmin):
    inlines = (StudentProfileInline,)
    list_display = ('username', 'first_name', 'last_name', 'role',
                    'national_id', 'province', 'district', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active', 'province', 'district')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'national_id')
    fieldsets = UserAdmin.fieldsets + (
        ('اطلاعات اضافی', {
            'fields': ('role', 'national_id', 'province', 'district'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        if obj.role == 'student':
            return super().get_inline_instances(request, obj)
        return list()


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key_short', 'created_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('key', 'created_at')

    def key_short(self, obj):
        if obj.key:
            return f"{obj.key[:10]}..."
        return "-"
    key_short.short_description = 'کلید'


admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile)
admin.site.site_header = 'پنل مدیریت سامانه پایش هوشمند'
admin.site.site_title = 'سامانه پایش هوشمند'
admin.site.index_title = 'داشبورد مدیریت'