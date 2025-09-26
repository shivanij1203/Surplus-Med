from django.urls import path
from .views import *
urlpatterns = [
    path('', home, name='home'),
    path('donorreg/', donor_register, name='donorReg'),
    path('ngoreg/', ngo_registration, name='ngoReg'),
    path('donorlog/', donor_login, name='donorLog'),
    path('ngolog/', ngo_login, name='ngolog'),
    path('upload/', upload_med, name='uploadMed'),
    path('view/', view_med, name='viewMed'),
    path('logout/', logout_user, name='logout'),
    path('aboutus/', about_us, name='aboutus'),
    path('view/<name>', checkout, name='checkout')
]