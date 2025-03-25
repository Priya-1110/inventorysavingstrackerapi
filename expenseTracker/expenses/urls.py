from django.urls import path
from .views import savings_goal_view, home_redirect,expense_analyzer_view

urlpatterns = [
    path('', home_redirect),
    path('savings-goal/', savings_goal_view, name='savings_goal'),
    path('analyze-expenses/', expense_analyzer_view, name='analyze_expenses'),
]
