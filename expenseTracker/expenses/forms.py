from django import forms
from datetime import date

class SavingsGoalForm(forms.Form):
    goal_amount = forms.DecimalField(
        label="Goal Amount (USD)",
        min_value=1,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    current_savings = forms.DecimalField(
        label="Current Savings (USD)",
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    goal_date = forms.DateField(
        label="Goal Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        initial=date.today
    )
    currency = forms.ChoiceField(
        label="Display Currency",
        choices=[("USD", "USD"), ("INR", "INR"), ("EUR", "EUR")],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    email = forms.EmailField(
        label="Your Email (optional)",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    chart_image = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

class ExpenseEntryForm(forms.Form):
    category = forms.CharField(label="Category", max_length=100)
    amount = forms.DecimalField(label="Amount", min_value=0, decimal_places=2)

class ExpenseAnalyzerForm(forms.Form):
    total_amount_target = forms.DecimalField(label="Budget Target", min_value=0, decimal_places=2)
    total_amount_spent = forms.DecimalField(label="Total Spent", min_value=0, decimal_places=2)
