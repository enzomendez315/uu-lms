from django.shortcuts import render, redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout
from . import models
from django.http import Http404, HttpResponse
from collections import defaultdict

def index(request):
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", {"assignments": assignments})

def assignment(request, assignment_id):
    errors = defaultdict(list)
    
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
    except models.Assignment.DoesNotExist:
        errors["assignment"].append("Assignment ID is not valid.")
        raise Http404("Page does not exist.")
    
    try:
        # For Student Action Box
        student = models.User.objects.get(username="a")
        # For TA Action Box
        grader = models.User.objects.get(username="g")
    except models.User.DoesNotExist:
        errors["user"].append("User does not exist.")

    # For Student Action Box
    submission = models.Submission.objects.filter(author=student, assignment_id=assignment_id).first()

    # Get the number of submissions, submissions assigned to the grader, and the number of students
    submissions_count = assignment.submission_set.count()
    for_grading_count = assignment.submission_set.filter(grader=grader).count()
    students_count = models.Group.objects.get(name="Students").user_set.count()

    user = request.user
    
    additional_info = {
        "assignment": assignment,
        "submission": submission,
        "submissions": submissions_count,
        "for_grading": for_grading_count,
        "students": students_count,
        "user": user,
        "is_student": is_student(user),
        "is_ta": is_ta(user),
        "errors": errors
    }

    if request.method == "POST":
        # Get the submitted file object
        submitted_file = request.FILES.get(f"submission-file")

        # Update the file of the existing submission
        if submission:
            submission.file = submitted_file
        # Create a new submission
        else:
            submission = models.Submission(
                assignment=assignment,
                author=student,
                grader=grader,
                file=submitted_file,
                score=None
            )
        submission.save()

        return redirect(f"/{assignment_id}/")
    
    return render(request, "assignment.html", additional_info)

def submissions(request, assignment_id):
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
    except models.Assignment.DoesNotExist:
        raise Http404("Page does not exist.")
    
    submissions = []
    errors = defaultdict(list)
    invalid_submission_ids = []
    user = request.user
    additional_info = {"assignment": assignment,}
    
    if request.method == "POST":
        # Extract the submission ID's
        submission_ids = extract_data(request.POST)
        submissions_list = []

        for submission_id in submission_ids:
            # Submission object must exist for these submission and assignment IDs
            try:
                submission = models.Submission.objects.get(id=submission_id, assignment_id=assignment_id)
            except models.Submission.DoesNotExist:
                invalid_submission_ids.append(f"Submission ID 'grade-{submission_id}' does not exist.")
                continue

            # Score must be a number between 0 and the maximum number of points
            try:
                value = request.POST[f"grade-{submission_id}"]
                score = float(value) if value != "" else None
                max_points = assignment.points
                if score is not None and (score < 0 or score > max_points):
                    errors[submission_id].append(f"Score {score} is not in valid range 0-{max_points}.")
                    score = None
                submission.score = score
                submissions_list.append(submission)
            except (KeyError, ValueError):
                errors[submission_id].append("Score value must be a valid number.")

            submissions.append({
                "author": submission.author.get_full_name(),
                "file": submission.file.url if submission.file else None,
                "score": submission.score,
                "id": submission.id,
                "errors": errors[submission_id]
            })

        models.Submission.objects.bulk_update(submissions_list, ["score"])
        
        if all(not error for error in errors.values()) and not invalid_submission_ids:
            return redirect(f"/{assignment_id}/submissions")
    else:
        if user.is_superuser:
            # Get all submissions
            for_grading = assignment.submission_set.select_related("author").all()
        elif is_ta(user):
            # Get submissions assigned to this TA
            for_grading = assignment.submission_set.filter(grader=user).select_related("author").order_by("author__username")
        else:
            # Empty list for students
            for_grading = []

        for submission in for_grading:
            submissions.append({
                "author": submission.author.get_full_name(),
                "file": submission.file.url if submission.file else None,
                "score": submission.score,
                "id": submission.id,
                "errors": []
            })

    additional_info["submissions"] = submissions
    additional_info["invalid_submission_ids"] = invalid_submission_ids
    return render(request, "submissions.html", additional_info)

def profile(request):
    all_assignments = models.Assignment.objects.all()
    grader = models.User.objects.get(username="g")
    assignments = []

    for assignment in all_assignments:
        # Get number of submissions that have been graded and number of submissions assigned to the grader
        assignments.append({
            "id": assignment.id,
            "title": assignment.title,
            "graded_count": assignment.submission_set.filter(grader=grader, score__isnull=False).count(),
            "for_grading_count": assignment.submission_set.filter(grader=grader).count()
        })

    additional_info = {
        "assignments": assignments,
        "user": request.user
    }
    return render(request, "profile.html", additional_info)

def login_form(request):
    if request.method == "POST":
        # Extract username and password
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(username=username, password=password)

        if user is not None:
            # Authentication succeeded
            login(request, user)
            return redirect("/profile/")
        else:
            # Credentials could not be authenticated
            return render(request, "login.html")
    return render(request, "login.html")

def logout_form(request):
    logout(request)
    return redirect("/profile/login/")

def show_upload(request, filename):
    try:
        submission = models.Submission.objects.get(file=filename)
    except models.Submission.DoesNotExist:
        raise Http404("Submission does not exist.")
    return HttpResponse(submission.file.open())

def extract_data(request_data):
    submissions = []
    # Iterate through request.POST
    for key in request_data.keys():
        if key.startswith("grade-") and key.removeprefix("grade-"):
            try:
                # Convert ID to an integer
                id = int(key.removeprefix("grade-"))
                submissions.append(id)
            except ValueError:
                continue
    return submissions

def is_student(user):
    return user.groups.filter(name="Students").exists()

def is_ta(user):
    return user.groups.filter(name="Teaching Assistants").exists()