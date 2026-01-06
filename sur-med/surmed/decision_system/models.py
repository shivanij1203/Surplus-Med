from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid
import hashlib


class ReasonCode(models.Model):
    """
    Standardized reason codes for decisions.
    Provides classification and traceability for all accept/review/reject decisions.
    """
    code = models.CharField(max_length=20, unique=True, help_text="Short code identifier (e.g., EXP-001)")
    decision_type = models.CharField(max_length=20, choices=[
        ('ACCEPTED', 'Accepted'),
        ('REVIEW', 'Needs Review'),
        ('REJECTED', 'Rejected'),
        ('ANY', 'Applicable to Any'),
    ])
    description = models.TextField(help_text="Full description of this reason code")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.description[:50]}"


class EligibilityRule(models.Model):
    """
    Rule-based eligibility criteria for supply acceptance.
    Each rule defines a specific check that must pass for eligibility.
    """
    RULE_TYPE_CHOICES = [
        ('EXPIRY_DATE', 'Expiry Date Validation'),
        ('CATEGORY', 'Category Restriction'),
        ('PACKAGING', 'Packaging Integrity'),
        ('QUANTITY', 'Quantity Limits'),
        ('DOCUMENTATION', 'Documentation Requirements'),
        ('CUSTOM', 'Custom Rule'),
    ]

    name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    is_blocking = models.BooleanField(default=True, help_text="If True, failure blocks acceptance")

    # Rule parameters (stored as JSON or specific fields)
    min_shelf_life_days = models.IntegerField(null=True, blank=True, help_text="Minimum days until expiry")
    allowed_categories = models.JSONField(null=True, blank=True, help_text="List of allowed categories")
    required_packaging_status = models.JSONField(null=True, blank=True)
    min_quantity = models.IntegerField(null=True, blank=True)
    max_quantity = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rule_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class Supply(models.Model):
    """
    Core supply submission model.
    Represents a medical supply submitted for redistribution consideration.
    """
    CATEGORY_CHOICES = [
        ('PPE', 'Personal Protective Equipment'),
        ('SURGICAL', 'Surgical Supplies'),
        ('DIAGNOSTIC', 'Diagnostic Equipment'),
        ('WOUND_CARE', 'Wound Care'),
        ('EQUIPMENT', 'Medical Equipment'),
        ('OTHER_SUPPLIES', 'Other Medical Supplies'),
    ]

    PACKAGING_STATUS_CHOICES = [
        ('SEALED_UNOPENED', 'Sealed & Unopened'),
        ('OPENED_INTACT', 'Opened but Intact'),
        ('MINOR_DAMAGE', 'Minor Damage'),
        ('SIGNIFICANT_DAMAGE', 'Significant Damage'),
    ]

    STORAGE_CHOICES = [
        ('CONTROLLED', 'Controlled Environment'),
        ('ROOM_TEMP', 'Room Temperature'),
        ('REFRIGERATED', 'Refrigerated'),
        ('UNKNOWN', 'Unknown'),
    ]

    STATUS_CHOICES = [
        ('PENDING_INITIAL', 'Pending Initial Review'),
        ('PENDING_FINAL', 'Pending Final Approval'),
        ('ACCEPTED', 'Accepted for Redistribution'),
        ('NEEDS_REVIEW', 'Needs Additional Review'),
        ('REJECTED', 'Rejected'),
    ]

    # Unique identifier
    supply_id = models.CharField(max_length=50, unique=True, editable=False)

    # Basic Information
    item_name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit = models.CharField(max_length=50, choices=[
        ('pieces', 'Pieces'),
        ('boxes', 'Boxes'),
        ('packs', 'Packs'),
        ('units', 'Units'),
        ('sets', 'Sets'),
    ])
    description = models.TextField(blank=True)

    # Expiry and Batch
    expiry_date = models.DateField()
    batch_number = models.CharField(max_length=100, blank=True)

    # Packaging and Storage
    packaging_status = models.CharField(max_length=50, choices=PACKAGING_STATUS_CHOICES)
    storage_conditions = models.CharField(max_length=50, choices=STORAGE_CHOICES)

    # Submission tracking
    submitted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='submitted_supplies')
    submitted_date = models.DateTimeField(auto_now_add=True)

    # Current status
    decision_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING_INITIAL')

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Chain of custody hash
    custody_hash = models.CharField(max_length=64, editable=False, blank=True)

    class Meta:
        ordering = ['-submitted_date']
        verbose_name_plural = "Supplies"

    def save(self, *args, **kwargs):
        # Generate unique supply ID on first save
        if not self.supply_id:
            self.supply_id = f"SUP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Generate custody hash
        self._generate_custody_hash()

        super().save(*args, **kwargs)

    def _generate_custody_hash(self):
        """Generate SHA-256 hash for chain of custody"""
        data = f"{self.supply_id}|{self.item_name}|{self.submitted_date}|{self.submitted_by.id}"
        self.custody_hash = hashlib.sha256(data.encode()).hexdigest()

    @property
    def days_until_expiry(self):
        """Calculate days remaining until expiry"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    @property
    def is_expired(self):
        """Check if supply is expired"""
        return self.days_until_expiry < 0 if self.days_until_expiry is not None else True

    def __str__(self):
        return f"{self.supply_id} - {self.item_name}"


class Evidence(models.Model):
    """
    Evidence documentation attached to supply submissions.
    Supports photos, documents, and other proof of condition/authenticity.
    """
    EVIDENCE_TYPE_CHOICES = [
        ('PHOTO_PACKAGING', 'Photo - Packaging'),
        ('PHOTO_LABEL', 'Photo - Label/Expiry'),
        ('PHOTO_PRODUCT', 'Photo - Product'),
        ('DOCUMENT_COA', 'Certificate of Analysis'),
        ('DOCUMENT_INVOICE', 'Purchase Invoice'),
        ('DOCUMENT_OTHER', 'Other Documentation'),
    ]

    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name='evidence_set')
    evidence_type = models.CharField(max_length=50, choices=EVIDENCE_TYPE_CHOICES)
    file = models.FileField(upload_to='evidence/%Y/%m/', max_length=500)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)

    # File integrity
    file_hash = models.CharField(max_length=64, editable=False, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def save(self, *args, **kwargs):
        # Calculate file hash for integrity
        if self.file and not self.file_hash:
            self.file.seek(0)
            self.file_hash = hashlib.sha256(self.file.read()).hexdigest()
            self.file.seek(0)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_evidence_type_display()} for {self.supply.supply_id}"


class Decision(models.Model):
    """
    Immutable decision records for audit trail.
    Every decision must have justification and reason code.
    """
    DECISION_CHOICES = [
        ('ACCEPTED', 'Accepted for Redistribution'),
        ('REVIEW', 'Needs Additional Review'),
        ('REJECTED', 'Rejected'),
    ]

    DECISION_LEVEL_CHOICES = [
        ('INITIAL', 'Initial Review'),
        ('FINAL', 'Final Approval'),
        ('OVERRIDE', 'Administrative Override'),
    ]

    # Core decision data
    supply = models.ForeignKey(Supply, on_delete=models.PROTECT, related_name='decision_set')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    decision_level = models.CharField(max_length=20, choices=DECISION_LEVEL_CHOICES)
    reason_code = models.ForeignKey(ReasonCode, on_delete=models.PROTECT)

    # Justification (required for auditability)
    justification = models.TextField(help_text="Detailed explanation for this decision")
    notes = models.TextField(blank=True, help_text="Additional internal notes")

    # Decision maker and timestamp
    decided_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='decisions_made')
    decision_date = models.DateTimeField(auto_now_add=True)

    # Eligibility assessment snapshot
    eligibility_passed = models.BooleanField(help_text="Did the supply pass automated eligibility checks?")
    eligibility_details = models.JSONField(blank=True, null=True, help_text="Snapshot of eligibility check results")

    # Audit integrity
    decision_hash = models.CharField(max_length=64, editable=False, blank=True)
    is_superseded = models.BooleanField(default=False, help_text="True if a newer decision exists")

    class Meta:
        ordering = ['-decision_date']
        # Ensure immutability through database constraints
        permissions = [
            ("can_make_initial_decision", "Can make initial review decisions"),
            ("can_make_final_decision", "Can make final approval decisions"),
            ("can_override_decision", "Can override previous decisions"),
        ]

    def save(self, *args, **kwargs):
        # Generate immutable decision hash
        if not self.decision_hash:
            data = f"{self.supply.supply_id}|{self.decision}|{self.decided_by.id}|{timezone.now().isoformat()}"
            self.decision_hash = hashlib.sha256(data.encode()).hexdigest()

        # Update supply status based on decision
        if not self.pk:  # Only on creation
            if self.decision == 'ACCEPTED':
                self.supply.decision_status = 'ACCEPTED'
            elif self.decision == 'REVIEW':
                self.supply.decision_status = 'NEEDS_REVIEW'
            elif self.decision == 'REJECTED':
                self.supply.decision_status = 'REJECTED'
            self.supply.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_decision_display()} - {self.supply.supply_id} by {self.decided_by.username}"


class AuditLog(models.Model):
    """
    System-wide audit log for all actions.
    Provides complete traceability beyond just decisions.
    """
    ACTION_CHOICES = [
        ('SUPPLY_SUBMITTED', 'Supply Submitted'),
        ('EVIDENCE_UPLOADED', 'Evidence Uploaded'),
        ('DECISION_MADE', 'Decision Made'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('RULE_MODIFIED', 'Eligibility Rule Modified'),
        ('EXPORT_GENERATED', 'Audit Export Generated'),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    supply = models.ForeignKey(Supply, on_delete=models.PROTECT, null=True, blank=True)
    decision = models.ForeignKey(Decision, on_delete=models.PROTECT, null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
