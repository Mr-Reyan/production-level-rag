from django.urls import path
from . import views
urlpatterns = [
    path('add/',views.add_document),
    path('search/',views.search),
    path('upload/',views.upload_pdf),
    path('ask/',views.ask)
]
