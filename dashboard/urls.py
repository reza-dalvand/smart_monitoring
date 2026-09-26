from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # داشبورد اصلی (روتر بر اساس نقش)
    path('', views.dashboard_home, name='home'),
]