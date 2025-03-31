from django.contrib import admin
from .models import SavingsPlan,ExpenseAnalysis

# Register models with custom admin configuration
admin.site.register(SavingsPlan)
admin.site.register(ExpenseAnalysis)
