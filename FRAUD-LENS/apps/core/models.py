from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30)
    content_type_label = models.CharField(max_length=120)
    object_id = models.CharField(max_length=80, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "action"])]

    def __str__(self):
        return f"{self.action} {self.content_type_label} {self.object_id}"
