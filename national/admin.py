from django.contrib import admin
from .models import Province, District, School, NationalAuditLog, NationalPolicy


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'code', 'is_active')
    list_filter = ('province', 'is_active')
    search_fields = ('name', 'province__name')


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'school_type', 'is_active')
    list_filter = ('school_type', 'is_active', 'district__province')
    search_fields = ('name', 'district__name', 'district__province__name')


@admin.register(NationalAuditLog)
class NationalAuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'scope', 'scope_name', 'created_at')
    list_filter = ('action', 'scope')
    search_fields = ('user__username', 'scope_name')
    readonly_fields = ('user', 'action', 'scope', 'scope_id',
                       'scope_name', 'details', 'ip_address', 'created_at')


@admin.register(NationalPolicy)
class NationalPolicyAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('key',)