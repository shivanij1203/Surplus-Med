from django.urls import path
from . import views

app_name = 'decision_system'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('supply/submit/', views.supply_submit, name='supply_submit'),
    path('supply/list/', views.supply_list, name='supply_list'),
    path('supply/<int:pk>/', views.supply_detail, name='supply_detail'),
    path('supply/<int:pk>/review/', views.supply_review, name='supply_review'),
    path('supply/<int:pk>/decide/', views.supply_decide, name='supply_decide'),

    path('decision/<int:pk>/', views.decision_detail, name='decision_detail'),

    path('audit/', views.audit_log, name='audit_log'),
    path('audit/export/', views.export_audit, name='export_audit'),

    path('rules/', views.manage_rules, name='manage_rules'),
]
