from django.urls import path
from . import views

urlpatterns = [
    path('overview/', views.OverviewReportView.as_view(), name='report-overview'),
    path('resources/', views.ResourceReportView.as_view(), name='report-resources'),
    path('export/pdf/', views.ExportPDFView.as_view(), name='report-export-pdf'),
    path('export/excel/', views.ExportExcelView.as_view(), name='report-export-excel'),
]
