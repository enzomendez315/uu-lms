from django.shortcuts import render, redirect
from django.contrib.auth.models import User, Group
from . import models
from django.http import Http404
from collections import defaultdict

def index(request):
    assignments = models.Assignment.objects.all()
    return render(request, "index.html", {"assignments": assignments})

def assignment(request, assignment_id):
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
        submissions_count = assignment.submission_set.count()
        grader = models.User.objects.get(username="g")

        # Get number of submissions assigned to the grader and total number of students
        for_grading_count = assignment.submission_set.filter(grader=grader).count()
        students_count = models.Group.objects.get(name="Students").user_set.count()

        # For Student Action Box
        student = models.User.objects.get(username="a")
        submission = models.Submission.objects.get(author=student, assignment_id=assignment_id)

        additional_info = {
            "assignment": assignment,
            "submissions": submissions_count,
            "for_grading": for_grading_count,
            "students": students_count,
            "submission": submission
        }
    except models.Assignment.DoesNotExist:
        raise Http404("Page does not exist.")
    return render(request, "assignment.html", additional_info)

def submissions(request, assignment_id):
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
    except models.Assignment.DoesNotExist:
        raise Http404("Page does not exist.")
    
    submissions = []
    errors = defaultdict(list)
    invalid_submission_ids = []
    additional_info = {"assignment": assignment}
    
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
                errors[submission_id].append(f"Score value must be a valid number.")

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
        grader = models.User.objects.get(username="g")

        # Get submissions assigned to the grader and sort them by author's username
        for_grading = assignment.submission_set.filter(grader=grader).select_related("author").order_by("author__username")

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
    return render(request, "profile.html", {"assignments": assignments})

def login_form(request):
    return render(request, "login.html")

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