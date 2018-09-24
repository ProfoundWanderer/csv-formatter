from django.urls import path
from . import views


urlpatterns = [
    path('', views.uploadcsv, name='upload_csv'),
]
