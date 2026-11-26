from django.conf import settings
from django.db import models


class Report(models.Model):
    FORMAT_CHOICES = (("pdf", "PDF"), ("csv", "CSV"), ("json", "JSON"))
    KIND_CHOICES = (
        ("summary", "Executive summary"),
        ("transactions", "Transaction detail"),
        ("findings", "Fraud findings"),
        ("cases", "Investigation cases"),
        ("custom", "Custom report"),
    )

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="reports")
    title = models.CharField(max_length=180)
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default="summary")
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="pdf")
    file_name = models.CharField(max_length=255)
    file_data = models.BinaryField()
    content_type = models.CharField(max_length=120, default="application/octet-stream")
    summary = models.JSONField(default=dict, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "kind"])]

    def __str__(self):
        return self.title
