from django.contrib import admin

from .models import (
    Certificate,
    CertificateAward,
    Skill,
    SkillCategory,
    SkillCriticalityAssessment,
    SkillFutureDemand,
    SkillProficiency,
    SkillRelationship,
)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "description")
    list_filter = ("domain",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)


@admin.register(SkillRelationship)
class SkillRelationshipAdmin(admin.ModelAdmin):
    list_display = ("from_skill", "to_skill", "kind", "weight")
    list_filter = ("kind",)
    autocomplete_fields = ("from_skill", "to_skill")


@admin.register(SkillProficiency)
class SkillProficiencyAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "level", "status", "last_used", "validation_source", "updated_at")
    list_filter = ("status", "level", "skill__category", "validation_source")
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


@admin.register(SkillCriticalityAssessment)
class SkillCriticalityAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "skill",
        "department",
        "criticality_score",
        "business_impact",
        "strategic_relevance",
        "time_to_replace_months",
        "version",
        "assessed_at",
    )
    list_filter = ("department", "version")
    autocomplete_fields = ("skill", "department", "assessed_by")


@admin.register(SkillFutureDemand)
class SkillFutureDemandAdmin(admin.ModelAdmin):
    list_display = (
        "skill",
        "direction",
        "future_importance",
        "confidence_level",
        "horizon",
        "source",
    )
    list_filter = ("direction", "confidence_level")
    autocomplete_fields = ("skill",)