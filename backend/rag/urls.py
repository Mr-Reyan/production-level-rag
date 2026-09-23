from django.urls import path
from rag import views

urlpatterns = [
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("ask/", views.ask, name="ask"),
]
