from django.db import models
from django.contrib.auth.models import User

class Investment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    investment_name = models.CharField(max_length=100)
    amount_invested = models.FloatField()
    current_value = models.FloatField()
    date_of_investment = models.DateField()
    investment_type = models.CharField(max_length=100)  # New field added
    document = models.FileField(upload_to='investments/', blank=True, null=True)  # S3 upload path

    def __str__(self):
        return self.investment_name


class Savings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal_name = models.CharField(max_length=100)
    target_amount = models.FloatField()
    current_amount = models.FloatField()
    deadline = models.DateField()

    def __str__(self):
        return self.goal_name
