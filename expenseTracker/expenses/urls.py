from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvestmentViewSet, SavingsViewSet
from .views import homepage

router = DefaultRouter()
router.register(r'investments', InvestmentViewSet)
router.register(r'savings', SavingsViewSet)

urlpatterns = [
    path('', homepage, name='homepage'),
    path('api/', include(router.urls)),  # This is for the API-related routes
]
