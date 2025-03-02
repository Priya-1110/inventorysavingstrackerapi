from rest_framework import viewsets
from .models import Investment, Savings
from .serializers import InvestmentSerializer, SavingsSerializer
from rest_framework.permissions import AllowAny
from django.http import HttpResponse

class InvestmentViewSet(viewsets.ModelViewSet):
    queryset = Investment.objects.all()
    serializer_class = InvestmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class SavingsViewSet(viewsets.ModelViewSet):
    queryset = Savings.objects.all()
    serializer_class = SavingsSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
        

def homepage(request):
    return HttpResponse("Welcome to the Investment and Savings Tracker API!")

