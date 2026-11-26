from django.contrib import admin

from .models import DetectionRun, FraudFinding, ModelPerformance, RiskScore

admin.site.register(DetectionRun)
admin.site.register(FraudFinding)
admin.site.register(RiskScore)
admin.site.register(ModelPerformance)
