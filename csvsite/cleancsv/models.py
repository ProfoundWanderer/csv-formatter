from django.db import models
from django.utils import timezone


class Document(models.Model):
    document = models.FileField(upload_to='csv/')
    upload_start = models.DateTimeField(auto_now_add=True)
    upload_finished = models.DateTimeField(default=timezone.now)
