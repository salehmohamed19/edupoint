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
    path('course/<int:course_pk>/certificate/', views.view_certificate, name='view_certificate'),
    path('lesson/<int:lesson_pk>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    
    # --- أضف هذا السطر هنا لتختفي المشكلة فوراً ---
    path('lesson/<int:lesson_pk>/save-progress/', views.save_video_progress, name='save_video_progress'),
    path('lesson/<int:lesson_pk>/signed-video-url/', views.get_signed_video_url, name='get_signed_video_url'),
    path('course/<int:course_pk>/lesson/<int:lesson_pk>/quiz/', views.quiz_detail, name='quiz_detail'),
    path('course/<int:course_pk>/lesson/<int:lesson_pk>/quiz/submit/', views.submit_quiz, name='submit_quiz'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('course/<int:course_pk>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('my-favorites/', views.favorite_list, name='favorite_list'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('course/<int:course_pk>/questions/', views.course_questions, name='course_questions'),
    path('course/<int:course_pk>/questions/add/', views.add_course_question, name='add_course_question'),
    path('question/<int:question_pk>/answer/', views.add_course_answer, name='add_course_answer'),
    path('verify-certificate/', views.verify_certificate, name='verify_certificate'),
    path('verify-certificate/<uuid:certificate_id>/', views.verify_certificate, name='verify_certificate_detail'),
    path('bundles/', views.bundle_list, name='bundle_list'),
    path('bundle/<int:bundle_pk>/', views.bundle_detail, name='bundle_detail'),
    path('lesson/<int:lesson_pk>/comment/', views.add_lesson_comment, name='add_lesson_comment'),
    path('course/<int:course_pk>/rate-instructor/', views.add_instructor_rating, name='add_instructor_rating'),
    
    path('course/<int:course_pk>/edit/', views.edit_course, name='edit_course'),
    path('course/<int:course_pk>/delete/', views.delete_course, name='delete_course'),
    path('lesson/<int:lesson_pk>/edit/', views.edit_lesson, name='edit_lesson'),
    path('lesson/<int:lesson_pk>/delete/', views.delete_lesson, name='delete_lesson'),
]