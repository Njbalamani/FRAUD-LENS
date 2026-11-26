from django.contrib import admin

from .models import AuditLog

admin.site.site_title = "FraudLens Admin"
admin.site.site_header = "FraudLens Administration"
admin.site.index_title = "Synthetic fraud intelligence control panel"
admin.site.register(AuditLog)
