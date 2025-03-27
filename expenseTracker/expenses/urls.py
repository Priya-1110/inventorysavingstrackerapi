from django.urls import path
from .views import (
    savings_goal_view,
    home_redirect,
    expense_analyzer_view,
    register_view,
    homepage_view,
    user_dashboard_view,
    delete_entry_view,
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', home_redirect),
    path('home/', homepage_view, name='home'),
    path('savings-goal/', savings_goal_view, name='savings_goal'),
    path('analyze-expenses/', expense_analyzer_view, name='analyze_expenses'),
    path('dashboard/', user_dashboard_view, name='dashboard'),
    path('delete-entry/', delete_entry_view, name='delete_entry'),
    # 🧑‍💻 User Auth
    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
