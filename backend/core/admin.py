"""Django admin — gives the team a working data interface on Day 1.

History-tracked models use SimpleHistoryAdmin so the audit trail is browsable.
Related rows (parties, seized items, statements, sections, diary) are edited
inline on the Case page, reinforcing the 'one Case object' principle.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Case,
    CaseJudgment,
    CaseSection,
    DiaryEvent,
    Document,
    LandmarkJudgment,
    LegalSection,
    Party,
    SeizedItem,
    Statement,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Extend the stock UserAdmin with our custom fields.
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Police profile", {"fields": ("role", "police_station")}),
    )
    list_display = ("username", "get_full_name", "role", "police_station", "is_staff")
    list_filter = DjangoUserAdmin.list_filter + ("role",)


class PartyInline(admin.TabularInline):
    model = Party
    extra = 0


class SeizedItemInline(admin.TabularInline):
    model = SeizedItem
    extra = 0


class StatementInline(admin.TabularInline):
    model = Statement
    extra = 0


class CaseSectionInline(admin.TabularInline):
    model = CaseSection
    extra = 0
    autocomplete_fields = ("section",)


class DiaryEventInline(admin.TabularInline):
    model = DiaryEvent
    extra = 0


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    readonly_fields = ("generated_at",)


@admin.register(Case)
class CaseAdmin(SimpleHistoryAdmin):
    list_display = ("case_number", "fir_number", "police_station", "status", "io", "created_at")
    list_filter = ("status", "police_station")
    search_fields = ("case_number", "fir_number", "incident_place", "incident_narrative")
    date_hierarchy = "created_at"
    inlines = [
        PartyInline,
        SeizedItemInline,
        StatementInline,
        CaseSectionInline,
        DiaryEventInline,
        DocumentInline,
    ]


@admin.register(Party)
class PartyAdmin(SimpleHistoryAdmin):
    list_display = ("name", "role", "case", "phone", "parent_name")
    list_filter = ("role",)
    search_fields = ("name", "parent_name", "phone", "id_number")


@admin.register(SeizedItem)
class SeizedItemAdmin(SimpleHistoryAdmin):
    list_display = ("__str__", "case", "quantity", "seized_from", "seizure_date")
    search_fields = ("description", "seizure_place")


@admin.register(Statement)
class StatementAdmin(SimpleHistoryAdmin):
    list_display = ("__str__", "case", "party", "recorded_date")
    search_fields = ("text",)


@admin.register(LegalSection)
class LegalSectionAdmin(admin.ModelAdmin):
    list_display = ("code", "section_number", "title", "ipc_equivalent")
    list_filter = ("code",)
    search_fields = ("section_number", "title", "text", "ipc_equivalent")


@admin.register(CaseSection)
class CaseSectionAdmin(admin.ModelAdmin):
    list_display = ("case", "section", "suggested_by_ai", "confirmed")
    list_filter = ("suggested_by_ai", "confirmed")
    autocomplete_fields = ("section",)


@admin.register(LandmarkJudgment)
class LandmarkJudgmentAdmin(admin.ModelAdmin):
    list_display = ("title", "citation", "year", "court")
    search_fields = ("title", "citation", "summary", "principle")
    autocomplete_fields = ("sections",)
    filter_horizontal = ("sections",)


@admin.register(CaseJudgment)
class CaseJudgmentAdmin(admin.ModelAdmin):
    list_display = ("case", "judgment", "suggested_by_ai", "applied")
    list_filter = ("suggested_by_ai", "applied")
    autocomplete_fields = ("judgment",)


@admin.register(DiaryEvent)
class DiaryEventAdmin(admin.ModelAdmin):
    list_display = ("case", "event_type", "timestamp", "actor")
    list_filter = ("event_type",)
    date_hierarchy = "timestamp"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("case", "doc_type", "version", "generated_at")
    list_filter = ("doc_type",)
    readonly_fields = ("generated_at",)
