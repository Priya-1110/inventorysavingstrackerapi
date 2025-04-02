import json
import base64
import uuid
import boto3
import requests
from django.shortcuts import render, redirect
from .forms import SavingsGoalForm, ExpenseAnalyzerForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login
from django.contrib import messages
from .forms import RegisterForm
from django.db import IntegrityError  # Add this
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from datetime import datetime
import datetime
import openai
import os
import decimal
from together import Together
from .models import SavingsPlan, ExpenseAnalysis
from dotenv import load_dotenv


@login_required
def homepage_view(request):
    return render(request, "home.html")


# External API configs
SAVINGS_PLANNER_API = "https://s5n43ij2al.execute-api.eu-west-1.amazonaws.com/prod/plan-savings"
CURRENCY_API = "https://api.frankfurter.app/latest"
EMAIL_API = "https://574zxm1da6.execute-api.eu-west-1.amazonaws.com/default/x23271281-EmailSenderAPI"
EXPENSE_ANALYZER_API = "https://iuro44novi.execute-api.eu-west-1.amazonaws.com/dev/analyze-expenses"
PASSWORD_CHECKER_API = "https://jbcss4xjuua4s4ihxn5hv5glo40ejyau.lambda-url.eu-west-1.on.aws/"
# Home redirect

def home_redirect(request):
    return redirect('register')

# Register View

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            if User.objects.filter(username=username).exists():
                form.add_error("username", "Username already taken.")
            elif User.objects.filter(email=email).exists():
                form.add_error("email", "Email already in use.")
            else:
                try:
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.save()
                    messages.success(request, "Registration successful. Please log in.")
                    return redirect("login")
                except IntegrityError:
                    form.add_error(None, "An account with this username already exists.")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})

# Upload to S3 with debug

def upload_chart_to_s3(base64_image):
    try:
        print("[S3 Upload] Starting upload...")
        s3 = boto3.client("s3")

        if not base64_image or "," not in base64_image:
            print("[S3 Upload] ❌ Invalid base64 image")
            return None

        file_data = base64.b64decode(base64_image.split(',')[1])
        filename = f"charts/chart-{uuid.uuid4().hex}.png"
        bucket = "smartsaver-charts"
        region = "eu-west-1"

        print(f"[S3 Upload] Uploading to: {bucket}/{filename}")

        s3.put_object(
            Bucket=bucket,
            Key=filename,
            Body=file_data,
            ContentType='image/png'
        )

        url = f"https://{bucket}.s3.{region}.amazonaws.com/{filename}"
        print("[S3 Upload] ✅ Upload successful:", url)
        return url

    except Exception as e:
        print("[S3 Upload] ❌ Upload failed:", str(e))
        return None

# Savings Planner View

@login_required
def savings_goal_view(request):
    converted_data = None
    if request.method == "POST":
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal_amount = float(form.cleaned_data['goal_amount'])
            current_savings = float(form.cleaned_data['current_savings'])
            goal_date = form.cleaned_data['goal_date']
            currency = form.cleaned_data['currency']
            user_email = form.cleaned_data.get("email")
            chart_image_base64 = form.cleaned_data.get("chart_image")

            payload = {
                "goal_amount": goal_amount,
                "current_savings": current_savings,
                "goal_date": str(goal_date)
            }

            try:
                response = requests.post(SAVINGS_PLANNER_API, json=payload)
                data = response.json() if response.status_code == 200 else {}

                if "monthly_savings_required" not in data:
                    raise ValueError("Missing 'monthly_savings_required' in API response.")

                # Currency Conversion
                if currency != "USD":
                    try:
                        rate = requests.get(f"{CURRENCY_API}?from=USD&to={currency}").json()["rates"][currency]
                        data["monthly_savings_converted"] = round(data["monthly_savings_required"] * rate, 2)
                        data["converted_currency"] = currency
                    except:
                        data["monthly_savings_converted"] = data["monthly_savings_required"]
                        data["converted_currency"] = "USD"
                else:
                    data["monthly_savings_converted"] = data["monthly_savings_required"]
                    data["converted_currency"] = "USD"

                # Add ETF & Crypto Info
                etf = data.get("investment_suggestions", {}).get("recommended_etf", {})
                crypto = data.get("investment_suggestions", {}).get("recommended_crypto", [])

                labels = [f"{etf.get('symbol', '')} Price", f"{etf.get('symbol', '')} Change %"]
                values = [float(etf.get("price_usd", 0)), float(etf.get("change_percent", "0").replace("%", ""))]
                for coin in crypto:
                    labels.append(f"{coin['name']} ({coin['symbol'].upper()})")
                    values.append(coin["price_usd"])

                data.update({
                    "etf_symbol": etf.get("symbol", ""),
                    "etf_price": float(etf.get("price_usd", 0)),
                    "etf_change": float(etf.get("change_percent", "0").replace("%", "")),
                    "chart_labels": labels,
                    "chart_values": values,
                })

                # Send Email Summary (without chart)
                if user_email:
                    crypto_lines = "\n".join([f"- {coin['name']} ({coin['symbol'].upper()}): ${coin['price_usd']}" for coin in crypto])
                    email_content = f"""
Hello!

Here's your SmartSaver savings plan:

🎯 Savings Goal:
- Monthly Saving: {data['monthly_savings_converted']} {data['converted_currency']}
- Duration: {data['months_remaining']} months
- Risk Profile: {data['risk_profile'].capitalize()}

📈 ETF:
- {etf.get('symbol', '')} - ${etf.get('price_usd', 0)}, Change: {etf.get('change_percent', '0')}

💹 Cryptocurrencies:
{crypto_lines}

Thanks for using SmartSaver!
                    """.strip()

                    email_payload = {
                        "email": user_email,
                        "subject": "📊 Your SmartSaver Savings Plan",
                        "content": email_content
                    }

                    res = requests.post(EMAIL_API, json=email_payload)
                    if res.status_code == 200:
                        messages.success(request, "📬 Email sent successfully!")
                        data["email_status"] = "📬 Email sent!"
                    else:
                        messages.warning(request, "⚠️ Email could not be sent.")
                        data["email_status"] = "⚠️ Failed to send email."

                # Save to DB
                SavingsPlan.objects.create(
                    user=request.user,
                    goal_amount=goal_amount,
                    current_savings=current_savings,
                    goal_date=goal_date,
                    monthly_savings_required=data['monthly_savings_required'],
                    monthly_savings_converted=data['monthly_savings_converted'],
                    converted_currency=data['converted_currency'],
                    etf_symbol=data['etf_symbol'],
                    etf_price=data['etf_price'],
                    etf_change=data['etf_change']
                )

                converted_data = data

            except Exception as e:
                print("[Planner Exception]", e)
                converted_data = {"error": str(e)}

    else:
        form = SavingsGoalForm()

    return render(request, "goal_result.html", {"form": form, "result": converted_data})
# Expense Analyzer

@login_required
def expense_analyzer_view(request):
    result = None
    if request.method == "POST":
        form = ExpenseAnalyzerForm(request.POST)
        categories = []
        count = int(request.POST.get("category_count", 0))
        for i in range(count):
            cat = request.POST.get(f"category_{i}")
            amt = request.POST.get(f"amount_{i}")
            if cat and amt:
                categories.append({"category": cat, "amount": float(amt)})
        if form.is_valid():
            payload = {
                "total_amount_spent": float(form.cleaned_data['total_amount_spent']),
                "total_amount_target": float(form.cleaned_data['total_amount_target']),
                "expenses": categories
            }
            try:
                response = requests.post(EXPENSE_ANALYZER_API, json=payload)
                parsed = json.loads(response.json().get("body", '{}')) if response.status_code == 200 else {}
                result = parsed
                # Save to model
                ExpenseAnalysis.objects.create(
                    user=request.user,
                    total_amount_spent=payload['total_amount_spent'],
                    total_amount_target=payload['total_amount_target'],
                    suggestions=parsed.get("tip", ""),
                    categories=categories
                )
            except Exception as e:
                result = {"error": str(e)}
    else:
        form = ExpenseAnalyzerForm()
    return render(request, "expense_result.html", {"form": form, "result": result})

# Dashboard View

@login_required
def user_dashboard_view(request):
    savings = SavingsPlan.objects.filter(user=request.user).order_by("-created_at")
    expenses = ExpenseAnalysis.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard.html", {"savings": savings, "expenses": expenses})


timestamp = datetime.datetime.now().isoformat()

import boto3
from decimal import Decimal
from datetime import datetime

def save_to_dynamodb(user, data, entry_type):
    if not user.is_authenticated:
        return

    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('SmartSaverUserData')
        timestamp = datetime.now().isoformat()

        # Convert floats to Decimal (DynamoDB requirement)
        def convert_floats(obj):
            if isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(i) for i in obj]
            elif isinstance(obj, float):
                return Decimal(str(obj))
            return obj

        item = {
            'user_id': str(user.id),
            'timestamp': timestamp,
            'type': entry_type,
            'data': convert_floats(data),
        }

        table.put_item(Item=item)
        print("[DynamoDB] ✅ Data saved.")

    except Exception as e:
        print("[DynamoDB] ❌ Failed to save:", str(e))

@login_required
@csrf_exempt
def delete_entry_view(request):
    if request.method == "POST":
        entry_type = request.POST.get("type")
        entry_id = request.POST.get("id")

        if not entry_type or not entry_id:
            print("[Delete] ❌ Missing type or id")
            return redirect('dashboard')

        try:
            if entry_type == "savings":
                SavingsPlan.objects.filter(id=entry_id, user=request.user).delete()
            elif entry_type == "expense":
                ExpenseAnalysis.objects.filter(id=entry_id, user=request.user).delete()
            print(f"[Delete] ✅ Deleted {entry_type} entry with ID: {entry_id}")
        except Exception as e:
            print(f"[Delete] ❌ Failed to delete: {e}")

    return redirect('dashboard')

    

# Handle Decimal for JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)
@login_required
@csrf_exempt
def generate_ai_tip_entry(request):
    try:
        recent_savings = list(SavingsPlan.objects.filter(user=request.user).order_by("-created_at")[:3])
        recent_expenses = list(ExpenseAnalysis.objects.filter(user=request.user).order_by("-created_at")[:2])

        if not recent_savings and not recent_expenses:
            return render(request, "ai_tip.html", {
                "tip": "No data found to generate a personalized insight. Try planning or analyzing first!"
            })

        summary = ""

        for entry in recent_savings:
            summary += f"\nSavings Plan:\n"
            summary += f"- Goal Amount: {entry.goal_amount}\n"
            summary += f"- Monthly Required: {entry.monthly_savings_required} USD\n"
            summary += f"- Converted: {entry.monthly_savings_converted} {entry.converted_currency}\n"

        for entry in recent_expenses:
            summary += f"\nExpense Analysis:\n"
            summary += f"- Spent: {entry.total_amount_spent}, Target: {entry.total_amount_target}\n"
            summary += f"- Suggestions: {entry.suggestions}\n"

        prompt = f"""
You are a smart financial advisor AI. Based on the user's recent savings plans and expense analysis, provide one highly personalized financial tip that could help them improve. Be specific and helpful.

User Financial History:
{summary}

Personalized Financial Advice:
"""

        client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[{"role": "user", "content": prompt}]
        )

        tip = response.choices[0].message.content.strip()
        return render(request, "ai_tip.html", {"tip": tip})

    except Exception as e:
        print("[AI TIP] ❌ Error:", e)
        return render(request, "ai_tip.html", {"tip": "AI insight generation failed."})
