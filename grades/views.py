from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login, logout
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from . import models
from collections import defaultdict

@login_required
def index(request):
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", {"assignments": assignments})

@login_required
def assignment(request, assignment_id):
    errors = defaultdict(list)
    user = request.user
    
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
    except models.Assignment.DoesNotExist:
        errors["assignment"].append("Assignment ID is not valid.")
        raise Http404("Page does not exist.")
    
    try:
        # For Student Action Box
        student = user
        submission = models.Submission.objects.filter(author=student, assignment_id=assignment_id).first()
        # For TA Action Box
        grader = pick_grader(assignment) if submission is None else submission.grader
    except models.User.DoesNotExist:
        errors["user"].append("User does not exist.")

    # Get the number of submissions, submissions assigned to the grader, and the number of students
    submissions_count = assignment.submission_set.count()
    for_grading_count = assignment.submission_set.filter(grader=grader).count()
    students_count = models.Group.objects.get(name="Students").user_set.count()
    grade_percentage = f"{(submission.score / assignment.points) * 100}" if submission and submission.score is not None else ""
    
    additional_info = {
        "assignment": assignment,
        "submission": submission,
        "past_due": assignment.deadline < timezone.now(),
        "submissions": submissions_count,
        "grade_percentage": grade_percentage,
        "for_grading": for_grading_count,
        "students": students_count,
        "user": user,
        "is_student": is_student(user),
        "is_ta": is_ta(user),
        "errors": errors.items()
    }

    if request.method == "POST":
        if assignment.deadline < timezone.now():
            return HttpResponseBadRequest("Assignment is past due.")

        # Get the submitted file object
        submitted_file = request.FILES.get("submission-file")


        if submitted_file.size > 64 * 1024 * 1024:
            errors["size"].append("Size of file shouldn't be greater than 64 MiB")
            return render(request, "assignment.html", additional_info)
        
        if not submitted_file.name.endswith(".pdf") or not next(submitted_file.chunks()).startswith(b'%PDF-'):
            errors["type"].append("File is not a PDF")
            return render(request, "assignment.html", additional_info)

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

@login_required
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

    if not is_ta(user) and not user.is_superuser:
        raise PermissionDenied("Only admins and TA's can view this page")
    
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
                #submission.score = score
                submission.change_grade(user, score)
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

@login_required
def profile(request):
    user = request.user
    all_assignments = models.Assignment.objects.all()
    assignments = []
    current_grade = 0

    if user.is_superuser:
        for assignment in all_assignments:
            # Get the number of total graded submissions as well as the number of submissions overall
            assignments.append({
                "id": assignment.id,
                "title": assignment.title,
                "total_graded_count": assignment.submission_set.filter(score__isnull=False).count(),
                "total_submissions_count": assignment.submission_set.count()
            })
    elif is_ta(user):
        for assignment in all_assignments:
            # Get the number of submissions that have been graded and the number of submissions assigned to this TA
            assignments.append({
                "id": assignment.id,
                "title": assignment.title,
                "graded_count": assignment.submission_set.filter(grader=user, score__isnull=False).count(),
                "for_grading_count": assignment.submission_set.filter(grader=user).count()
            })
    else:
        earned_points = 0
        available_points = 0
        for assignment in all_assignments:
            """
            1. Submitted and graded - Show score (score on submission divided by maximum points in assignment)
            2. Submitted but not yet graded - Mark as 'Ungraded'
            3. Not submitted because the assignment isn't due yet - Mark as 'Not Due'
            4. Missing because the assignment is past due - Mark as 'Missing'
            """
            submission = assignment.submission_set.filter(author=user).first()
            if submission:
                if submission.score is not None:
                    grade_percentage = submission.score / assignment.points
                    status = f"{grade_percentage * 100}%"
                    earned_points += grade_percentage * assignment.weight
                    available_points += assignment.weight
                else:
                    status = "Ungraded"
            else:
                if assignment.deadline < timezone.now():
                    status = "Missing"
                    available_points += assignment.weight
                else:
                    status = "Not Due"

            # Get the number of submissions that have been graded and number of submissions assigned to the grader
            assignments.append({
                "id": assignment.id,
                "title": assignment.title,
                "status": status,
                "weight": assignment.weight
            })

            # print(f"{assignment.title}:")
            # if submission and submission.score is not None: print(f"grade_percentage: {grade_percentage}    weight: {assignment.weight}")
            # print(f"status: {status}    earned_points: {earned_points}    available_points: {available_points}")
            # print("")

        current_grade = "100.0%" if available_points == 0 else f"{round((earned_points / available_points) * 100, 1)}%"

    additional_info = {
        "assignments": assignments,
        "user": user,
        "is_ta": is_ta(user),
        "current_grade": current_grade
    }
    return render(request, "profile.html", additional_info)

def login_form(request):
    next_url = request.GET.get("next", "/profile/")

    if request.method == "POST":
        # Extract username and password
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        next_url = request.POST.get("next", "/profile/")
        user = authenticate(username=username, password=password)

        if url_has_allowed_host_and_scheme(next_url, None):
            if user is not None:
                # Authentication succeeded
                login(request, user)
                return redirect(next_url)
            else:
                # Credentials could not be authenticated
                error = "Username and password do not match"
                return render(request, "login.html", {"next": next_url, "error": error})
        else:
            return redirect("/")
    return render(request, "login.html", {"next": next_url})

def logout_form(request):
    logout(request)
    return redirect("/profile/login/")

@login_required
def show_upload(request, filename):
    try:
        submission = models.Submission.objects.get(file=filename)

        if not submission.file.name.endswith(".pdf") or not next(submission.file.chunks()).startswith(b'%PDF-'):
            raise Http404("File is not a PDF")
        
        response = HttpResponse(submission.view_submission(request.user).open())
        response["Content-Type"] = "application/pdf"
        response["Content-Disposition"] = f'attachment; filename="{submission.file.name}"'
        
        return response
    except models.Submission.DoesNotExist:
        raise Http404("Submission does not exist.")

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

def pick_grader(assignment):
    assistants = models.Group.objects.get(name="Teaching Assistants")
    grader = assistants.user_set.annotate(total_assigned=Count("graded_set", filter=Q(graded_set__assignment=assignment))).order_by("total_assigned").first()
    return grader

def is_student(user):
    return user.groups.filter(name="Students").exists()

def is_ta(user):
    return user.groups.filter(name="Teaching Assistants").exists()