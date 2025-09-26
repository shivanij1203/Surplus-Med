from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import MedModel, NgoModel, DonorModel
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models import  Q
from django.contrib.auth.forms import UserCreationForm
from datetime import date, datetime
import pytesseract
import re
import cv2
from PIL import Image
from io import BytesIO
# Create your views here.

def ExtractDetails(image_path):
    text = pytesseract.image_to_string(Image.open(image_path), lang = 'eng')
    text = text.replace('\n', " ")
    text = text.replace('  '," ")
    regex_expdate = re.compile('EXP.\d{2}[-/]\d{4}')
    regex_expdate2 = re.compile('EXP.\d{2}[-/]\d{2}')
    regex_expdate3 = re.compile('EXP\.\d{2}/\d{4}')
    regex_expdate4 = re.compile('EXPIRY DATE \d{2}/\d{4}')
    regex_expdate5 = re.compile('Exp\.Date:\d{1,2}[A-Z]{3}\d{4}')
    regex_expdate6 = re.compile('Exp\.Date:\s*\d{1,2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{4}')
    regex_expdate7 = re.compile('EXP:\s*\d{1,2}/\d{1,2}/\d{2}')
    regex_expdate8 = re.compile('Exp\.\s*\d{1,2}/\d{4}')
    regex_expdate9 = re.compile('EXP\d{2}/\d{4}')
    regex_expdate10 = re.compile('Exp\.\s*Date\s*:\s*\d{2}-\d{4}')
    patterns = [regex_expdate, regex_expdate2, regex_expdate3, regex_expdate4, regex_expdate5, regex_expdate6, regex_expdate7, regex_expdate8, regex_expdate9, regex_expdate10]
    extracted_text = ''
    i = 0
    while i < len(patterns):
        extracted_text = patterns[i].findall(text)
        if len(extracted_text) != 0:
            break
        i += 1
    return extracted_text

def home(request):
    return render(request, 'home.html')

def donor_register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        phonenum = request.POST['phonenum']
        email = request.POST['email']
        ins = User.objects.create_user(username=username, password=password)
        DonorModel.objects.create(user = ins, name = username, phonenumber = phonenum, email = email)
        return redirect('home')
    context = {}
    return render(request, 'donor_registration.html', context)

def ngo_registration(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        phonenum = request.POST['phonenum']
        email = request.POST['email']
        ins = User.objects.create_user(username=username, password=password)
        NgoModel.objects.create(user=ins, name=username, phonenumber=phonenum, email=email)
        return render(request, 'home.html')
    context = {}
    return render(request, 'ngo_registration.html', context)


def donor_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            try:
                del request.session['ngo']
            except:
                pass
            login(request,user)
            request.session['donor'] = 'donor'
            return render(request, 'home.html')
        return render(request, 'login_error.html')
    return render(request, 'donor_login.html')

def ngo_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request,username=username, password=password)
        print(user)
        if user is not None:
            try:
                del request.session['donor']
            except:
                pass
            login(request,user)
            request.session['ngo'] = 'ngo'
            return render(request, 'home.html')
        return HttpResponse("ERROR. USERNAME OR PASSWORD WRONG")
    return render(request, 'ngo_login.html')

def upload_med(request):
    context={}
    if request.user.is_authenticated:
        curr_user = request.user
        try:
            donor_prof = DonorModel.objects.get(user = curr_user)
        except:
            return HttpResponse('<h2 style="color : red">You are not Loggin as Donor please login through Donor Id</h2>')
        if donor_prof is not None:
            if request.method == 'GET':
                username = donor_prof.name
                context['username'] = username
                return render(request, 'upload_med.html', context)
            if request.method == 'POST':
                print('form got')
                user = curr_user
                name = request.POST['name']
                quantity = request.POST['quantity']
                image = request.FILES['med_image']
                exp_date = request.POST['exp_date']
                buffer = BytesIO()
                for chunk in image:
                    buffer.write(chunk)
                buffer.seek(0)
                ocr_date = ExtractDetails(buffer)
                if ocr_date is None:
                    ocr_date = exp_date
                # if date.today() > datetime.strptime(exp_date, '%Y-%m-%d'):
                #     return HttpResponse('<strong> We can\'t upload the medicine in the database due to expiry date')
                print('creating instance')
                med_ins = MedModel(user=donor_prof, name=name, quantity=quantity, image=image, exp_date=exp_date, exp_date_ocr = ocr_date)
                print('saving instance')
                med_ins.save()
                print('instance saved')
                return redirect('home')
            
    return HttpResponse('<strong style="color : red">You are not authenticated. Please LogIn / SignUp first</strong>')

def view_med(request):
    if request.user.is_authenticated:
        context = {}
        try:
            ngo_prof = NgoModel.objects.get(user = request.user)
        except:
            return HttpResponse('<p>We dont find any NGO profile based on this username</p>')
        if ngo_prof is not None:
            if request.method == 'POST':
                query = request.POST.get('q')
                if query != '':
                    med_list = MedModel.objects.filter(Q(name__icontains = query))
                    med_list = [med for med in med_list if med.exp_date > date.today()]
                    print(med_list)
                    context['all_meds'] = med_list
                else:
                    return HttpResponse('<strong>No medicine found with that name</strong>')
            else:
                med_list = MedModel.objects.all()
                med_list = [med for med in med_list if med.exp_date > date.today()]
                context['all_meds'] = med_list
            return render(request, 'view_med.html', context)
    return HttpResponse('<strong style="color : red">You are not authenticated. Please LogIn / SignUp first</strong>')

def about_us(request):
    return render(request, 'aboutus.html')

def logout_user(request):
    logout(request)
    return redirect('home')

def checkout(request, name):
    med = MedModel.objects.get(name=name)
    context = {}
    if request.method == 'POST':
        quotes = int(request.POST['amount'])
        
        left_number = med.quantity - quotes
        if left_number < 0:
            return HttpResponse('<strong>Hey reduce the quotes. There arent that many number of quotes.</strong>')
        elif left_number > 0:
            med.quantity = left_number
            med.save()
            return HttpResponse('<strong>Order Placed</strong>')
        else:
            med.delete()
            return HttpResponse('<strong>Order Placed</strong>')
    context['med'] = med
    return render(request, 'checkout.html', context)