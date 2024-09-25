from django.db import models
from django.contrib.auth.models import User, Group

# TODO: Add blanks, nulls, and defaults
# TODO: Revise on_deletes
class Assignment(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField()
    weight = models.IntegerField()
    points = models.IntegerField()

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    grader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='graded_set')
    file = models.FileField()
    score = models.FloatField(null=True)