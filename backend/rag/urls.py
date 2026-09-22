from django.urls import path
from rag import views

urlpatterns = [
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("ask/", views.ask, name="ask"),
    path("chats/", views.list_chats, name="list_chats"),
    path("chats/<uuid:chat_id>/", views.chat_detail, name="chat_detail"),
]

