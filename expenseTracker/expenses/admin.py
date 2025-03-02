from django.contrib import admin
from .models import Investment, Savings

# Customize the admin interface for Investment model
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'investment_name', 'amount_invested', 'current_value', 'investment_type', 'date_of_investment')
    search_fields = ('investment_name', 'investment_type', 'user__username')
    list_filter = ('investment_type', 'date_of_investment')
    ordering = ('-date_of_investment',)
    date_hierarchy = 'date_of_investment'

# Customize the admin interface for Savings model
class SavingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal_name', 'target_amount', 'current_amount', 'deadline')
    search_fields = ('goal_name', 'user__username')
    list_filter = ('deadline',)
    ordering = ('-deadline',)
    date_hierarchy = 'deadline'

# Register models with custom admin configuration
admin.site.register(Investment, InvestmentAdmin)
admin.site.register(Savings, SavingsAdmin)
