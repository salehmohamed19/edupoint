from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_notification_email(user, subject, message, html_message=None):
    """
    إرسال إشعار بريد إلكتروني لمستخدم.
    """
    if not user.email:
        return False

    try:
        send_mail(
            subject=subject,
            message=strip_tags(html_message) if html_message else message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def send_enrollment_email(user, course):
    """إيميل عند الاشتراك في كورس"""
    subject = f'تم اشتراكك في كورس "{course.title}" ✅'
    html_message = render_to_string('emails/enrollment.html', {
        'user': user,
        'course': course,
    })
    return send_notification_email(user, subject, f'مرحباً {user.username}, تم اشتراكك في كورس "{course.title}" بنجاح!', html_message)


def send_quiz_pass_email(user, lesson, score):
    """إيميل عند 성공 في اختبار"""
    subject = f'تهانينا! لقد نجحت في اختبار درس "{lesson.title}" 🎉'
    html_message = render_to_string('emails/quiz_pass.html', {
        'user': user,
        'lesson': lesson,
        'score': score,
    })
    return send_notification_email(user, subject, f'تهانينا {user.username}! لقد نجحت في اختبار درس "{lesson.title}" بدرجة {score}%.', html_message)


def send_lesson_complete_email(user, lesson):
    """إيميل عند إتمام درس"""
    subject = f'لقد أكملت درس "{lesson.title}" ✅'
    html_message = render_to_string('emails/lesson_complete.html', {
        'user': user,
        'lesson': lesson,
    })
    return send_notification_email(user, subject, f'مرحباً {user.username}, لقد أكملت درس "{lesson.title}" بنجاح!', html_message)


def send_certificate_email(user, course, certificate):
    """إيميل عند إصدار شهادة"""
    subject = f'شهادتك جاهزة: "{course.title}" 🏆'
    html_message = render_to_string('emails/certificate.html', {
        'user': user,
        'course': course,
        'certificate': certificate,
    })
    return send_notification_email(user, subject, f'تهانينا {user.username}! شهادتك في كورس "{course.title}" جاهزة للتحميل.', html_message)
