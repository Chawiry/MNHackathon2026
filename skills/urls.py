from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.me, name="my_skills"),
    path("me/self-assess/", views.self_assess, name="self_assess"),
    path("me/certificates/", views.submit_certificate, name="submit_certificate"),
    path("record/", views.record_skill, name="record_skill"),
    path("record-certificate/", views.record_certificate, name="record_certificate"),
    path("records/<int:pk>/approve/", views.approve_proficiency, name="approve_proficiency"),
    path("records/<int:pk>/reject/", views.reject_proficiency, name="reject_proficiency"),
    path("certificates/<int:pk>/approve/", views.approve_certificate, name="approve_certificate"),
    path("certificates/<int:pk>/reject/", views.reject_certificate, name="reject_certificate"),
]