from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    industry = models.CharField(max_length=120, default="financial-services")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_ANALYST = "analyst"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Administrator"),
        (ROLE_ANALYST, "Fraud analyst"),
        (ROLE_VIEWER, "Viewer"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER)
    phone = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["username"]

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def is_analyst_role(self):
        return self.role in {self.ROLE_ADMIN, self.ROLE_ANALYST} or self.is_superuser
