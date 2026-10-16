from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('course/create/', views.create_course, name='create_course'),
    path('course/<int:course_pk>/add-lesson/', views.add_lesson, name='add_lesson'),
    path('course/<int:course_pk>/enroll/', views.enroll_free_course, name='enroll_free_course'),
    path('my-courses/', views.student_dashboard, name='student_dashboard'),
    path('course/<int:course_pk>/add-review/', views.add_review, name='add_review'),
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('course/<int:course_pk>/lesson/<int:lesson_pk>/', views.lesson_detail, name='lesson_detail'),
    path('course/<int:course_pk>/certificate/', views.view_certificate, name='view_certificate'), # <-- مسار الشهادة الجديد
    path('lesson/<int:lesson_pk>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('course/<int:course_pk>/edit/', views.edit_course, name='edit_course'),
    path('course/<int:course_pk>/delete/', views.delete_course, name='delete_course'),
    path('lesson/<int:lesson_pk>/delete/', views.delete_lesson, name='delete_lesson'),
]