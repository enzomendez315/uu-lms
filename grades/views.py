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

        additional_info = {
            "assignment": assignment,
            "submissions": submissions_count,
            "for_grading": for_grading_count,
            "students": students_count
        }
    except models.Assignment.DoesNotExist:
        raise Http404("Page does not exist.")
    return render(request, "assignment.html", additional_info)

def submissions(request, assignment_id):
    if request.method == "POST":
        # Extract the submission ID's
        submission_ids = extract_data(request.POST)
        submissions = []
        errors = defaultdict(list)

        try:
            assignment = models.Assignment.objects.get(id=assignment_id)
        except models.Assignment.DoesNotExist:
            raise Http404("Page does not exist.")

        # submissions = models.Submission.objects.filter(id__in=submission_ids, assignment_id=assignment_id)
        # for submission in submissions:
        #     id = str(submission.id)
        #     value = request.POST[id]
        #     score = float(value) if value else None
        #     submission.score = score

        for submission_id in submission_ids:
            # Submission object must exist for these submission and assignment IDs
            try:
                submission = models.Submission.objects.get(id=submission_id, assignment_id=assignment_id)
            except models.Submission.DoesNotExist:
                errors[submission_id].append(f"Submission with ID {submission_id} does not exist.")

            # Submission ID must be valid
            try:
                value = request.POST[str(submission_id)]
            except KeyError:
                errors[submission_id].append(f"Submission ID {submission_id} is invalid.")

            # Score must be a number between 0 and the maximum number of points
            try:
                score = float(value) if value else None
                max_points = assignment.points
                if score and score < 0 or score > max_points:
                    score = None
                    errors[submission_id].append(f"Score {score} is outside of the valid range 0-{max_points}.")
                submission.score = score
            except ValueError:
                errors[submission_id].append(f"Score {score} must be a number.")

            author = submission.author.get_full_name()
            file = submission.file
            score = submission.score
            submissions.append([author, file, score])

        models.Submission.objects.bulk_update(submissions, ["score"])

        additional_info = {
            "assignment": assignment,
            "submissions": submissions,
            "errors": errors
        }
        
        if not errors:
            return redirect(f"/{assignment_id}/submissions")
    else:
        try:
            assignment = models.Assignment.objects.get(id=assignment_id)
            grader = models.User.objects.get(username="g")

            # Get submissions assigned to the grader and sort them by author's username
            for_grading = assignment.submission_set.filter(grader=grader).select_related("author").order_by("author__username")

            submissions = []
            errors = {}

            for submission in for_grading:
                # Get author's name, file url, and score
                author = submission.author.get_full_name()
                file = submission.file
                score = submission.score
                submissions.append([author, file, score])

            additional_info = {
                "assignment": assignment,
                "submissions": submissions,
                "errors": errors
            }
        except models.Assignment.DoesNotExist:
            raise Http404("Page does not exist.")
    return render(request, "submissions.html", additional_info)

def profile(request):
    all_assignments = models.Assignment.objects.all()
    grader = models.User.objects.get(username="g")
    assignments = []

    for assignment in all_assignments:
        # Get number of submissions that have been graded and number of submissions assigned to the grader
        graded_count = assignment.submission_set.filter(grader=grader, score__isnull=False).count()
        for_grading_count = assignment.submission_set.filter(grader=grader).count()
        assignments.append([assignment.id, assignment.title, graded_count, for_grading_count])
    return render(request, "profile.html", {"assignments": assignments})

def login_form(request):
    return render(request, "login.html")

def extract_data(request_data):
    submissions = []
    # Iterate through request.POST
    for key in request_data.keys():
        if key.startswith("grade-") and key.removeprefix("grade-"):
            # Convert ID to an integer
            id = int(key.removeprefix("grade-"))
            submissions.append(id)
    return submissions