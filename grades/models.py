from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied

class Assignment(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField()
    weight = models.IntegerField()
    points = models.IntegerField()

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    grader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="graded_set")
    file = models.FileField(blank=False)
    score = models.FloatField(null=True)

    def change_grade(self, user, new_score):
        if not user.is_superuser and user != self.grader:
            raise PermissionDenied("Only admins and TA's can change grades")
        self.score = new_score

    def view_submission(self, user):
        if user != self.author and user != self.grader and not user.is_superuser:
            raise PermissionDenied("Only admins, the author or the grader of this submission can view this file")
        return self.file