from django.db import models
from django.utils import timezone
# from django.core.files.storage import FileSystemStorage

# need to download file from here
# fs = FileSystemStorage(location='/csv/unformatted')


class Document(models.Model):
    document = models.FileField(upload_to='csv/')  # , storage=fs)
    upload_start = models.DateTimeField(auto_now_add=True)
    upload_finished = models.DateTimeField(default=timezone.now)
