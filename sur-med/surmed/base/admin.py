from django.contrib import admin
from .models import DonorModel, NgoModel, MedModel
# Register your models here.
admin.site.register(DonorModel)
admin.site.register(MedModel)
admin.site.register(NgoModel)
