from django.contrib import admin

from .models import Certificate, CertificateAward, Skill, SkillCategory, SkillProficiency


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)


@admin.register(SkillProficiency)
class SkillProficiencyAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "level", "status", "updated_at")
    list_filter = ("status", "level", "skill__category")
    search_fields = ("user__username", "skill__name")
    autocomplete_fields = ("user", "skill")
    date_hierarchy = "updated_at"


class CertificateAwardInline(admin.TabularInline):
    model = CertificateAward
    extra = 1
    autocomplete_fields = ("certificate",)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer")
    search_fields = ("name", "issuer")
    inlines = [CertificateAwardInline]


@admin.register(CertificateAward)
class CertificateAwardAdmin(admin.ModelAdmin):
    list_display = ("user", "certificate", "obtained_on", "expires_on")
    search_fields = ("user__username", "certificate__name")
    autocomplete_fields = ("user", "certificate")