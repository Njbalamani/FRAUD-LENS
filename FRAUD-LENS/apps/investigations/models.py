import uuid

from django.conf import settings
from django.db import models


class InvestigationCase(models.Model):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("investigating", "Investigating"),
        ("escalated", "Escalated"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    )
    PRIORITY_CHOICES = (("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="cases")
    case_id = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_cases")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_cases")
    findings = models.ManyToManyField("detection.FraudFinding", blank=True, related_name="cases")
    tags = models.JSONField(default=list, blank=True)
    resolution_notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [models.Index(fields=["organization", "status"])]

    def save(self, *args, **kwargs):
        if not self.case_id:
            self.case_id = f"FL-CASE-{self.organization_id:03d}-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.case_id} - {self.title}"


class CaseNote(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="case_notes")
    case = models.ForeignKey(InvestigationCase, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.case.case_id}"


class CaseEvidence(models.Model):
    EVIDENCE_TYPES = (("file", "File"), ("screenshot", "Screenshot"), ("json", "JSON"), ("link", "Link"), ("note", "Note"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="case_evidence")
    case = models.ForeignKey(InvestigationCase, on_delete=models.CASCADE, related_name="evidence")
    evidence_type = models.CharField(max_length=30, choices=EVIDENCE_TYPES, default="file")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_data = models.BinaryField(null=True, blank=True)
    url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
