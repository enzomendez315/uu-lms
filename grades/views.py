from django.shortcuts import render
from . import models

def index(request):
    return render(request, "index.html")

def assignment(request, assignment_id):
    return render(request, "assignment.html")

def submissions(request, assignment_id):
    return render(request, "submissions.html")

def profile(request):
    return render(request, "profile.html")

def login_form(request):
    return render(request, "login.html")