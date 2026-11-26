from django.contrib import admin

from .models import CaseEvidence, CaseNote, InvestigationCase

admin.site.register(InvestigationCase)
admin.site.register(CaseNote)
admin.site.register(CaseEvidence)
