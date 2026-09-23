from django.urls import path
from chats import views

urlpatterns = [
    path("chats/", views.list_chats, name="list_chats"),
    path("chats/<uuid:chat_id>/", views.chat_detail, name="chat_detail"),
]
