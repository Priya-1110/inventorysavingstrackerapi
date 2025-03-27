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
from .forms import RegisterForm
from django.db import IntegrityError  # Add this
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from datetime import datetime
import datetime

# Redirect root to planner
def home_redirect(request):
    return redirect('register')

@login_required
def homepage_view(request):
    return render(request, "home.html")


# External API configs
SAVINGS_PLANNER_API = "https://s5n43ij2al.execute-api.eu-west-1.amazonaws.com/prod/plan-savings"
CURRENCY_API = "https://api.frankfurter.app/latest"
EMAIL_API = "https://574zxm1da6.execute-api.eu-west-1.amazonaws.com/default/x23271281-EmailSenderAPI"
EXPENSE_ANALYZER_API = "https://iuro44novi.execute-api.eu-west-1.amazonaws.com/dev/analyze-expenses"
PASSWORD_CHECKER_API = "https://jbcss4xjuua4s4ihxn5hv5glo40ejyau.lambda-url.eu-west-1.on.aws/"

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # ✅ Check if username exists before creating
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
    
# S3 chart upload function
def upload_chart_to_s3(base64_image):
    try:
        print("[S3 Upload] Starting upload...")
        s3 = boto3.client("s3")

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
def savings_goal_view(request):
    converted_data = None

    if request.method == "POST":
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal_amount = float(form.cleaned_data['goal_amount'])
            current_savings = float(form.cleaned_data['current_savings'])
            goal_date = str(form.cleaned_data['goal_date'])
            target_currency = form.cleaned_data['currency']
            user_email = form.cleaned_data.get("email")
            chart_image_base64 = form.cleaned_data.get("chart_image")

            print("[Chart] base64 length:", len(chart_image_base64 or ""))
            print("[Chart] Sample base64:", chart_image_base64[:50] if chart_image_base64 else "None")

            payload = {
                "goal_amount": goal_amount,
                "current_savings": current_savings,
                "goal_date": goal_date
            }

            try:
                planner_response = requests.post(SAVINGS_PLANNER_API, json=payload)
                raw_data = planner_response.json() if planner_response.status_code == 200 else {}
                body = raw_data.get("body", raw_data)
                planner_data = json.loads(body) if isinstance(body, str) else body

                # Currency conversion
                if target_currency != "USD":
                    try:
                        rate_data = requests.get(f"{CURRENCY_API}?from=USD&to={target_currency}").json()
                        rate = float(rate_data["rates"].get(target_currency))
                        planner_data["monthly_savings_converted"] = round(planner_data["monthly_savings_required"] * rate, 2)
                        planner_data["converted_currency"] = target_currency
                    except Exception as e:
                        print("[Currency] ❌ Error during conversion:", e)
                        planner_data["monthly_savings_converted"] = planner_data["monthly_savings_required"]
                        planner_data["converted_currency"] = "USD (error fallback)"
                else:
                    planner_data["monthly_savings_converted"] = planner_data["monthly_savings_required"]
                    planner_data["converted_currency"] = "USD"

                # Chart data
                crypto_data = planner_data.get("investment_suggestions", {}).get("recommended_crypto", [])
                etf_data = planner_data.get("investment_suggestions", {}).get("recommended_etf", {})

                etf_symbol = etf_data.get("symbol", "")
                etf_price = float(etf_data.get("price_usd", 0))
                etf_change = float(etf_data.get("change_percent", "0").replace("%", ""))

                labels = [f"{etf_symbol} Price", f"{etf_symbol} Change %"]
                values = [etf_price, etf_change]
                for coin in crypto_data:
                    labels.append(f"{coin['name']} ({coin['symbol'].upper()})")
                    values.append(coin["price_usd"])

                planner_data.update({
                    "etf_symbol": etf_symbol,
                    "etf_price": etf_price,
                    "etf_change": etf_change,
                    "chart_labels": labels,
                    "chart_values": values
                })

                # Upload chart to S3
                chart_url = upload_chart_to_s3(chart_image_base64) if chart_image_base64 else None
                print("[Chart] Final chart URL:", chart_url)

                # Send email
                if user_email:
                    crypto_lines = [
                        f"• {c['name']} ({c['symbol'].upper()}): ${c['price_usd']}" for c in crypto_data
                    ]
                    email_text = f"""
Hello,

Here is your personalized savings and investment plan:

🎯 Savings Goal:
- Monthly: {planner_data['monthly_savings_converted']} {planner_data['converted_currency']} ({planner_data['monthly_savings_required']} USD)
- Duration: {planner_data['months_remaining']} months
- Risk: {planner_data['risk_profile'].capitalize()}

📈 ETF:
- {etf_symbol} - ${etf_price}, Change: {etf_change}%

💹 Cryptos:
{chr(10).join(crypto_lines)}

📊 Chart Snapshot:
{chart_url if chart_url else "Chart not available"}

Thank you for using SmartSaver!
                    """

                    email_payload = {
                        "email": user_email,
                        "subject": "Your SmartSaver Financial Plan Summary",
                        "content": email_text.strip()
                    }

                    res = requests.post(EMAIL_API, json=email_payload)
                    print("[Email API] Status:", res.status_code)
                    print("[Email API] Response:", res.text)
                    planner_data["email_status"] = "✅ Email sent!" if res.status_code == 200 else "⚠️ Failed to send email."

                converted_data = planner_data
                save_to_dynamodb(request.user, planner_data, entry_type='savings_plan')
            except Exception as e:
                print("[Savings Planner] ❌ Exception:", e)
                converted_data = {"error": f"API error: {str(e)}"}

    else:
        form = SavingsGoalForm()
    return render(request, "goal_result.html", {
        "form": form,
        "result": converted_data
    })


# Expense Analyzer View
def expense_analyzer_view(request):
    analysis_result = None
    if request.method == "POST":
        form = ExpenseAnalyzerForm(request.POST)
        categories = []
        count = int(request.POST.get("category_count", 0))

        for i in range(count):
            category = request.POST.get(f"category_{i}")
            amount = request.POST.get(f"amount_{i}")
            if category and amount:
                categories.append({"category": category, "amount": float(amount)})

        if form.is_valid() and categories:
            payload = {
                "total_amount_spent": float(form.cleaned_data['total_amount_spent']),
                "total_amount_target": float(form.cleaned_data['total_amount_target']),
                "expenses": categories
            }

            try:
                response = requests.post(EXPENSE_ANALYZER_API, json=payload)
                if response.status_code == 200:
                    api_raw = response.json()
                    if isinstance(api_raw.get("body"), str):
                        analysis_result = json.loads(api_raw["body"])
                    else:
                        analysis_result = api_raw.get("body", {})
                    print("[Expense API] Final parsed result:", analysis_result)
                    
                else:
                    analysis_result = {"error": f"API returned status {response.status_code}"}
                    
                save_to_dynamodb(request.user, analysis_result, entry_type='expense_analysis')

            except Exception as e:
                analysis_result = {"error": f"Exception occurred: {str(e)}"}
    else:
        form = ExpenseAnalyzerForm()
    return render(request, "expense_result.html", {
        "form": form,
        "result": analysis_result
    })

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
def user_dashboard_view(request):
    user_data = []

    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('SmartSaverUserData')

        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(str(request.user.id))
        )

        user_data = response.get("Items", [])
        user_data.sort(key=lambda x: x['timestamp'], reverse=True)

    except Exception as e:
        print("[DynamoDB] ❌ Error fetching data:", str(e))

    return render(request, "dashboard.html", {
        "user_data": user_data
    })

@login_required
@csrf_exempt
def delete_entry_view(request):
    if request.method == "POST":
        timestamp = request.POST.get("timestamp")

        if not timestamp:
            print("[Delete] ❌ No timestamp provided")
            return redirect('dashboard')

        try:
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.Table('SmartSaverUserData')

            table.delete_item(
                Key={
                    'user_id': str(request.user.id),
                    'timestamp': request.POST.get("timestamp")
                }
            )
            print(f"[Delete] ✅ Deleted entry at {timestamp}")
        except Exception as e:
            print("[Delete] ❌ Failed to delete:", str(e))

    return redirect('dashboard')