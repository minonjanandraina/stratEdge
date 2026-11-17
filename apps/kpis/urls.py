from django.urls import path
from . import views

urlpatterns = [
    path('latest/', views.KPILatestView.as_view(), name='kpi-latest'),
    path('history/', views.KPIHistoryView.as_view(), name='kpi-history'),
    path('calculate/', views.KPICalculateView.as_view(), name='kpi-calculate'),
    path('evm/', views.EVMCurvesView.as_view(), name='kpi-evm'),
]
