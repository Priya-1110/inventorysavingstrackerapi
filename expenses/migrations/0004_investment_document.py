# Generated by Django 4.2.19 on 2025-03-04 21:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_investment_savings_delete_expense'),
    ]

    operations = [
        migrations.AddField(
            model_name='investment',
            name='document',
            field=models.FileField(blank=True, null=True, upload_to='investments/'),
        ),
    ]
