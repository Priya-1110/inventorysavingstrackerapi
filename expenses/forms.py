from django import forms
from datetime import date
import requests
import json

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


PASSWORD_CHECKER_API = "https://jbcss4xjuua4s4ihxn5hv5glo40ejyau.lambda-url.eu-west-1.on.aws/"

class RegisterForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
    
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
    
        # Check password strength via API
        try:
            response = requests.post(PASSWORD_CHECKER_API, json={"password": password})
            print("[Password Checker] Status:", response.status_code)
            print("[Password Checker] Response:", response.text)
    
            if response.status_code == 200:
                result = response.json()
    
                strength = result.get("strength")
                suggestions = result.get("suggestions", [])
    
                if strength == "weak":
                    error_message = "Weak password. "
                    if suggestions:
                        error_message += "Suggestions: " + ", ".join(suggestions)
                    raise forms.ValidationError(error_message)
    
            else:
                raise forms.ValidationError("Could not validate password. Service returned an error.")
        except Exception as e:
            raise forms.ValidationError(f"Password strength check failed: {str(e)}")
