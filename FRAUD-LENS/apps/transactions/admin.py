from django.contrib import admin

from .models import FinancialAccount, Transaction, TransactionImport, TransactionRelationship

admin.site.register(FinancialAccount)
admin.site.register(Transaction)
admin.site.register(TransactionImport)
admin.site.register(TransactionRelationship)
