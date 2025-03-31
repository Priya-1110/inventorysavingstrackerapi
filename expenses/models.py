from django.db import models
from django.contrib.auth.models import User

class SavingsPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal_amount = models.FloatField()
    current_savings = models.FloatField()
    goal_date = models.DateField()
    monthly_savings_required = models.FloatField()
    converted_currency = models.CharField(max_length=10, default='USD')
    monthly_savings_converted = models.FloatField(null=True, blank=True)
    etf_symbol = models.CharField(max_length=20, blank=True)
    etf_price = models.FloatField(null=True, blank=True)
    etf_change = models.FloatField(null=True, blank=True)
    email_status = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SavingsPlan for {self.user.username} - {self.goal_amount} by {self.goal_date}"

class ExpenseAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount_spent = models.FloatField()
    total_amount_target = models.FloatField()
    suggestions = models.TextField(blank=True)  # Store AI tips or analysis result here
    categories = models.JSONField(default=list)  # Stores a list of expense category dicts
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ExpenseAnalysis for {self.user.username} - Spent: {self.total_amount_spent}"
