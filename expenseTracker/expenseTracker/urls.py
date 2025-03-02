from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('expenses.urls')),  # This will route '/' to your app's URLs
    path('api/', include('expenses.urls')),  # For API-related routes
]
