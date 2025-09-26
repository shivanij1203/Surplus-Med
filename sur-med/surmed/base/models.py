from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class DonorModel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)
    phonenumber = models.PositiveIntegerField(blank=False, unique=True)
    email = models.EmailField(max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

class NgoModel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False, unique=True)
    phonenumber = models.IntegerField(blank=False)
    email = models.EmailField(max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

class MedModel(models.Model):
    user = models.ForeignKey(DonorModel, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)
    quantity = models.IntegerField()
    image = models.ImageField(upload_to='images/', default='images/default.png',blank=True)
    exp_date = models.DateField(blank = False)
    exp_date_ocr = models.CharField(max_length=255, default='No Ocr value detected')
    
    def __str__(self):
        return self.name