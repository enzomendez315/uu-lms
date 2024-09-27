from django.shortcuts import render
from django.contrib.auth.models import User, Group
from . import models
from django.http import Http404

def index(request):
    # Get all assignments
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", {'assignments': assignments})

def assignment(request, assignment_id):
    try:
        # Get assignment by ID
        assignment = models.Assignment.objects.get(id=assignment_id)

        # Get total number of submissions
        submissions_count = assignment.submission_set.count()

        # Get the user object for the grader
        grader = models.User.objects.get(username="g")

        # Get number of submissions assigned to the grader
        for_grading_count = assignment.submission_set.filter(grader=grader).count()

        # Get total number of students
        students_count = models.Group.objects.get(name="Students").user_set.count()

        additional_info = {
            'assignment': assignment,
            'submissions': submissions_count,
            'for_grading': for_grading_count,
            'students': students_count
        }
    except models.Assignment.DoesNotExist:
        raise Http404("Page does not exist.")
    return render(request, "assignment.html", additional_info)

def submissions(request, assignment_id):
    return render(request, "submissions.html")

def profile(request):
    # Get all assignments
    all_assignments = models.Assignment.objects.all()

    # Get the user object for the grader
    grader = models.User.objects.get(username="g")

    assignments = []

    for assignment in all_assignments:
        # Get number of submissions that have been graded
        graded_count = assignment.submission_set.filter(grader=grader, score__isnull=False).count()
        
        # Get number of submissions assigned to the grader
        for_grading_count = assignment.submission_set.filter(grader=grader).count()

        assignments.append([assignment.id, assignment.title, graded_count, for_grading_count])

    return render(request, "profile.html", {'assignments': assignments})

def login_form(request):
    return render(request, "login.html")