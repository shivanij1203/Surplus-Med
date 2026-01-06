from django.contrib import admin
from .models import Supply, Decision, Evidence, ReasonCode, EligibilityRule, AuditLog


@admin.register(ReasonCode)
class ReasonCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'decision_type', 'description', 'is_active', 'created_at')
    list_filter = ('decision_type', 'is_active')
    search_fields = ('code', 'description')
    ordering = ('code',)


@admin.register(EligibilityRule)
class EligibilityRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_type', 'is_active', 'is_blocking', 'created_at')
    list_filter = ('rule_type', 'is_active', 'is_blocking')
    search_fields = ('name', 'description')
    ordering = ('rule_type', 'name')


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ('supply_id', 'item_name', 'category', 'quantity', 'expiry_date', 'decision_status', 'submitted_by', 'submitted_date')
    list_filter = ('decision_status', 'category', 'packaging_status', 'storage_conditions')
    search_fields = ('supply_id', 'item_name', 'batch_number')
    readonly_fields = ('supply_id', 'custody_hash', 'submitted_date', 'created_at', 'updated_at')
    ordering = ('-submitted_date',)

    fieldsets = (
        ('Identification', {
            'fields': ('supply_id', 'submitted_by', 'submitted_date')
        }),
        ('Supply Information', {
            'fields': ('item_name', 'category', 'quantity', 'unit', 'description')
        }),
        ('Expiry and Batch', {
            'fields': ('expiry_date', 'batch_number')
        }),
        ('Condition', {
            'fields': ('packaging_status', 'storage_conditions')
        }),
        ('Status', {
            'fields': ('decision_status',)
        }),
        ('Audit', {
            'fields': ('custody_hash', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('supply', 'evidence_type', 'description', 'uploaded_by', 'uploaded_at')
    list_filter = ('evidence_type', 'uploaded_at')
    search_fields = ('supply__supply_id', 'description')
    readonly_fields = ('file_hash', 'uploaded_at')
    ordering = ('-uploaded_at',)


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ('supply', 'decision', 'decision_level', 'reason_code', 'decided_by', 'decision_date', 'eligibility_passed')
    list_filter = ('decision', 'decision_level', 'eligibility_passed', 'decision_date')
    search_fields = ('supply__supply_id', 'justification', 'reason_code__code')
    readonly_fields = ('decision_hash', 'decision_date')
    ordering = ('-decision_date',)

    fieldsets = (
        ('Decision Information', {
            'fields': ('supply', 'decision', 'decision_level', 'reason_code')
        }),
        ('Justification', {
            'fields': ('justification', 'notes')
        }),
        ('Decision Maker', {
            'fields': ('decided_by', 'decision_date')
        }),
        ('Eligibility Assessment', {
            'fields': ('eligibility_passed', 'eligibility_details')
        }),
        ('Audit', {
            'fields': ('decision_hash', 'is_superseded'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'supply', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'supply__supply_id')
    readonly_fields = ('action', 'user', 'supply', 'decision', 'timestamp', 'ip_address', 'details')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
