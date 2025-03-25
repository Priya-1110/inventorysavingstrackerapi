import json
import base64
import uuid
import boto3
import requests
from django.shortcuts import render, redirect
from .forms import SavingsGoalForm, ExpenseAnalyzerForm, ExpenseEntryForm

def home_redirect(request):
    return redirect('savings_goal')

# Configs
SAVINGS_PLANNER_API = "https://s5n43ij2al.execute-api.eu-west-1.amazonaws.com/prod/plan-savings"
CURRENCY_API = "https://api.frankfurter.app/latest"
EMAIL_API = "https://574zxm1da6.execute-api.eu-west-1.amazonaws.com/default/x23271281-EmailSenderAPI"
EXPENSE_ANALYZER_API = "https://iuro44novi.execute-api.eu-west-1.amazonaws.com/dev/analyze-expenses"


def upload_chart_to_s3(base64_image):
    try:
        import uuid, base64, boto3

        print("[S3 Upload] Starting upload...")
        s3 = boto3.client("s3")
        file_data = base64.b64decode(base64_image.split(',')[1])
        filename = f"charts/chart-{uuid.uuid4().hex}.png"
        bucket = "smartsaver-charts"
        region = "eu-west-1"

        print("[S3 Upload] File name:", filename)

        s3.put_object(
            Bucket=bucket,
            Key=filename,
            Body=file_data,
            ContentType='image/png'  # ✅ DO NOT include ACL here
        )

        url = f"https://{bucket}.s3.{region}.amazonaws.com/{filename}"
        print("[S3 Upload] Upload successful:", url)
        return url

    except Exception as e:
        print("[S3 Upload] Upload failed:", str(e))
        return None



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

                # Currency Conversion
                if target_currency != "USD":
                    try:
                        rate_data = requests.get(f"{CURRENCY_API}?from=USD&to={target_currency}").json()
                        rate = float(rate_data["rates"].get(target_currency))
                        planner_data["monthly_savings_converted"] = round(planner_data["monthly_savings_required"] * rate, 2)
                        planner_data["converted_currency"] = target_currency
                    except:
                        planner_data["monthly_savings_converted"] = planner_data["monthly_savings_required"]
                        planner_data["converted_currency"] = "USD (error fallback)"
                else:
                    planner_data["monthly_savings_converted"] = planner_data["monthly_savings_required"]
                    planner_data["converted_currency"] = "USD"

                # Chart Data
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
                print("[Chart] Received base64 image:", chart_image_base64[:100])

                # Upload chart image to S3
                chart_url = upload_chart_to_s3(chart_image_base64) if chart_image_base64 else None

                # Send Email
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
                    planner_data["email_status"] = "✅ Email sent!" if res.status_code == 200 else "⚠️ Failed to send email."

                converted_data = planner_data

            except Exception as e:
                converted_data = {"error": f"API error: {str(e)}"}
    else:
        form = SavingsGoalForm()

    return render(request, "goal_result.html", {
        "form": form,
        "result": converted_data
    })
    
import json
import requests
from django.shortcuts import render
from .forms import ExpenseAnalyzerForm

EXPENSE_ANALYZER_API = "https://iuro44novi.execute-api.eu-west-1.amazonaws.com/dev/analyze-expenses"

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
            except Exception as e:
                analysis_result = {"error": f"Exception occurred: {str(e)}"}
    else:
        form = ExpenseAnalyzerForm()

    return render(request, "expense_result.html", {
        "form": form,
        "result": analysis_result
    })
