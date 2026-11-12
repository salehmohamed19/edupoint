import base64
import io
import json
import time
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum
from django.urls import reverse
import qrcode
from .email_utils import (
    send_enrollment_email, send_quiz_pass_email,
    send_lesson_complete_email, send_certificate_email,
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from cloudinary.utils import cloudinary_url
from payments.models import Payment
from .models import (
    BundlePurchase,
    Category,
    Certificate,
    Choice,
    ContactMessage,
    Coupon,
    Course,
    CourseAnswer,
    CourseBundle,
    CourseQuestion,
    Enrollment,
    Favorite,
    InstructorPayout,
    InstructorRating,
    Lesson,
    LessonComment,
    LessonProgress,
    Notification,
    Quiz,
    QuizAttempt,
    Review,
)


def course_list(request):
  query = request.GET.get('q', '')
  category_id = request.GET.get('category', '')
  price_filter = request.GET.get('price', '')
  sort = request.GET.get('sort', '')

  courses = Course.objects.all().select_related('category', 'instructor')

  # بحث نصي بالاسم أو اسم المدرس
  if query:
    courses = courses.filter(
        models.Q(title__icontains=query) |
        models.Q(instructor__username__icontains=query)
    )

  # فلترة حسب التصنيف
  if category_id:
    courses = courses.filter(category_id=category_id)

  # فلترة حسب السعر (مجاني / مدفوع)
  if price_filter == 'free':
    courses = courses.filter(is_free=True)
  elif price_filter == 'paid':
    courses = courses.filter(is_free=False)

  # ترتيب النتائج
  if sort == 'price_asc':
    courses = courses.order_by('price')
  elif sort == 'price_desc':
    courses = courses.order_by('-price')
  elif sort == 'newest':
    courses = courses.order_by('-created_at')
  else:
    courses = courses.order_by('-created_at')

  categories = Category.objects.all()

  return render(
      request,
      'courses/course_list.html',
      {
          'courses': courses,
          'query': query,
          'categories': categories,
          'selected_category': category_id,
          'selected_price': price_filter,
          'selected_sort': sort,
      }
  )


def course_detail(request, pk):
  course = get_object_or_404(Course, pk=pk)
  is_enrolled = False

  if request.user.is_authenticated:
    if course.instructor == request.user:
      is_enrolled = True
    elif Enrollment.objects.filter(student=request.user, course=course).exists():
      is_enrolled = True
    elif (
        Payment.objects.filter(
            student=request.user, course=course, status='completed'
        )
        .exists()
    ):
      Enrollment.objects.get_or_create(student=request.user, course=course)
      is_enrolled = True

  all_lessons = list(course.lessons.all().order_by('order'))
  lessons_data = []

  if request.user.is_authenticated:
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            student=request.user, lesson__course=course, is_completed=True
        ).values_list('lesson_id', flat=True)
    )
  else:
    completed_lesson_ids = set()

  is_instructor_owner = request.user.is_authenticated and course.instructor == request.user

  is_favorite = False
  if request.user.is_authenticated:
    is_favorite = Favorite.objects.filter(student=request.user, course=course).exists()

  # تقييم المدرس
  instructor_avg_rating = None
  instructor_rating_count = 0
  user_instructor_rating = None
  if request.user.is_authenticated:
    ratings = InstructorRating.objects.filter(course=course)
    if ratings.exists():
      from django.db.models import Avg
      avg = ratings.aggregate(avg=Avg('rating'))['avg']
      instructor_avg_rating = round(avg, 1)
      instructor_rating_count = ratings.count()
    user_instructor_rating = InstructorRating.objects.filter(
        instructor=course.instructor, student=request.user, course=course
    ).first()

  for index, item in enumerate(all_lessons):
    is_completed = item.id in completed_lesson_ids

    if is_instructor_owner or index == 0:
      is_unlocked = True
    else:
      prev_item = all_lessons[index - 1]
      is_unlocked = prev_item.id in completed_lesson_ids

    lessons_data.append({
        'lesson': item,
        'is_completed': is_completed,
        'is_unlocked': is_unlocked,
    })

  return render(
      request,
      'courses/course_detail.html',
      {
          'course': course,
          'is_enrolled': is_enrolled,
          'is_favorite': is_favorite,
          'lessons_data': lessons_data,
          'instructor_avg_rating': instructor_avg_rating,
          'instructor_rating_count': instructor_rating_count,
          'user_instructor_rating': user_instructor_rating,
      },
  )


@login_required
def enroll_free_course(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)

  if course.is_free:
    _, created = Enrollment.objects.get_or_create(
        student=request.user, course=course
    )
    if created:
      messages.success(
          request,
          f'تم انضمامك بنجاح إلى كورس "{course.title}"! استمتع بالدروس 🚀',
      )
      send_enrollment_email(request.user, course)
    else:
      messages.info(request, 'أنت مشترك بالفعل في هذا الكورس مسبقاً.')

  return redirect('course_detail', pk=course.pk)


@login_required
def create_course(request):
  if (
      hasattr(request.user, 'userprofile')
      and request.user.userprofile.user_type != 'instructor'
  ):
    messages.error(request, 'عذراً، هذا الحساب غير مخصص لإنشاء الكورسات.')
    return redirect('course_list')

  if request.method == 'POST':
    title = request.POST.get('title')
    description = request.POST.get('description')
    price = request.POST.get('price', 0)
    is_free = True if request.POST.get('is_free') == 'on' else False

    course = Course.objects.create(
        title=title,
        description=description,
        instructor=request.user,
        price=price if not is_free else 0,
        is_free=is_free,
    )
    messages.success(request, f'تم إنشاء ونشر كورس "{title}" بنجاح تام! 🎉')
    return redirect('course_detail', pk=course.pk)

  return render(request, 'courses/create_course.html')


@login_required
def edit_course(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)

  if course.instructor != request.user:
    messages.error(request, 'غير مسموح لك بتعديل هذا الكورس.')
    return redirect('instructor_dashboard')

  if request.method == 'POST':
    course.title = request.POST.get('title')
    course.description = request.POST.get('description')
    price = request.POST.get('price', 0)
    course.is_free = True if request.POST.get('is_free') == 'on' else False
    course.price = price if not course.is_free else 0
    course.save()

    messages.success(request, f'تم تحديث بيانات الكورس "{course.title}" بنجاح! ✏️')
    return redirect('instructor_dashboard')

  return render(request, 'courses/edit_course.html', {'course': course})


@login_required
def delete_course(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)

  if course.instructor != request.user:
    messages.error(request, 'غير مسموح لك بحذف هذا الكورس.')
    return redirect('instructor_dashboard')

  if request.method == 'POST':
    course_title = course.title
    course.delete()
    messages.success(request, f'تم حذف الكورس "{course_title}" بنجاح 🗑️')
    return redirect('instructor_dashboard')

  return render(request, 'courses/delete_course_confirm.html', {'course': course})


@login_required
def delete_lesson(request, lesson_pk):
  lesson = get_object_or_404(Lesson, pk=lesson_pk)
  course = lesson.course

  if course.instructor != request.user:
    messages.error(request, 'غير مسموح لك بحذف هذا الدرس.')
    return redirect('course_detail', pk=course.pk)

  if request.method == 'POST':
    lesson_title = lesson.title
    lesson.delete()
    messages.success(request, f'تم حذف الدرس "{lesson_title}" بنجاح 🗑️')
    return redirect('course_detail', pk=course.pk)

  return render(request, 'courses/delete_lesson_confirm.html', {'lesson': lesson, 'course': course})


@login_required
def add_lesson(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)

  if course.instructor != request.user:
    messages.error(request, 'غير مسموح لك بإضافة دروس لهذا الكورس.')
    return redirect('course_detail', pk=course.pk)

  if request.method == 'POST':
    title = request.POST.get('title')
    video_url = request.POST.get('video_url')
    video_file = request.FILES.get('video_file')
    description = request.POST.get('description')
    attachment = request.FILES.get('attachment')
    order = request.POST.get('order', 1)

    Lesson.objects.create(
        course=course,
        title=title,
        video_url=video_url,
        video_file=video_file,
        description=description,
        attachment=attachment,
        order=order,
    )
    messages.success(request, f'تم إضافة الدرس "{title}" بنجاح 📺')
    return redirect('course_detail', pk=course.pk)

  return render(request, 'courses/add_lesson.html', {'course': course})


@login_required
def edit_lesson(request, lesson_pk):
  lesson = get_object_or_404(Lesson, pk=lesson_pk)
  course = lesson.course

  if course.instructor != request.user:
    messages.error(request, 'غير مسموح لك بتعديل هذا الدرس.')
    return redirect('course_detail', pk=course.pk)

  if request.method == 'POST':
    lesson.title = request.POST.get('title')
    lesson.video_url = request.POST.get('video_url')

    if request.FILES.get('video_file'):
      lesson.video_file = request.FILES.get('video_file')

    lesson.description = request.POST.get('description')

    if request.FILES.get('attachment'):
      lesson.attachment = request.FILES.get('attachment')

    lesson.order = request.POST.get('order', 1)
    lesson.save()

    messages.success(request, f'تم تحديث الدرس "{lesson.title}" بنجاح! ✏️')
    return redirect('lesson_detail', course.pk, lesson.pk)

  return render(request, 'courses/edit_lesson.html', {'lesson': lesson, 'course': course})


@login_required
def student_dashboard(request):
  enrollments = Enrollment.objects.filter(student=request.user)

  # جلب أحدث درس تابع للطلاب قام بمشاهدة جزء منه ولم يكمله بعد
  last_progress = LessonProgress.objects.filter(
      student=request.user, is_completed=False, watched_seconds__gt=0
  ).order_by('-completed_at').first()

  return render(
      request,
      'courses/student_dashboard.html',
      {
          'enrollments': enrollments,
          'last_progress': last_progress,
      },
  )


@login_required
def add_review(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)
  if request.method == 'POST':
    rating = request.POST.get('rating', 5)
    comment = request.POST.get('comment')
    Review.objects.create(
        course=course, student=request.user, rating=rating, comment=comment
    )
    messages.success(request, 'تم إضافة تقييمك ورأيك بنجاح، شكراً لمشاركتك! ⭐')
  return redirect('course_detail', pk=course.pk)


@login_required
def instructor_dashboard(request):
  if (
      hasattr(request.user, 'userprofile')
      and request.user.userprofile.user_type != 'instructor'
  ):
    return redirect('course_list')

  courses = Course.objects.filter(instructor=request.user)
  total_courses = courses.count()
  total_students = Enrollment.objects.filter(course__in=courses).count()
  total_lessons = Lesson.objects.filter(course__in=courses).count()
  total_completions = LessonProgress.objects.filter(
      lesson__course__in=courses, is_completed=True
  ).count()

  completed_payments = Payment.objects.filter(
      course__in=courses, status='completed'
  )
  raw_gross_sales = (
      completed_payments.aggregate(total=Sum('amount'))['total'] or 0
  )
  total_gross_sales = Decimal(str(raw_gross_sales))

  INSTRUCTOR_SHARE_PERCENTAGE = Decimal('0.80')
  PLATFORM_FEE_PERCENTAGE = Decimal('0.20')

  total_instructor_earnings = total_gross_sales * INSTRUCTOR_SHARE_PERCENTAGE
  platform_commission = total_gross_sales * PLATFORM_FEE_PERCENTAGE

  total_payouts_received = (
      InstructorPayout.objects.filter(instructor=request.user).aggregate(
          total=Sum('amount')
      )['total']
      or 0
  )
  total_payouts_received = Decimal(str(total_payouts_received))
  remaining_balance = total_instructor_earnings - total_payouts_received
  payout_history = InstructorPayout.objects.filter(
      instructor=request.user
  ).order_by('-created_at')

  course_financials = []
  for course in courses:
    course_payments = completed_payments.filter(course=course)
    raw_course_sales = (
        course_payments.aggregate(total=Sum('amount'))['total'] or 0
    )
    course_sales = Decimal(str(raw_course_sales))
    course_students = Enrollment.objects.filter(course=course).count()
    course_net = course_sales * INSTRUCTOR_SHARE_PERCENTAGE

    course_financials.append({
        'course': course,
        'students_count': course_students,
        'total_sales': course_sales,
        'net_earnings': course_net,
    })

  return render(
      request,
      'courses/instructor_dashboard.html',
      {
          'courses': courses,
          'total_courses': total_courses,
          'total_students': total_students,
          'total_lessons': total_lessons,
          'total_completions': total_completions,
          'total_gross_sales': total_gross_sales,
          'instructor_net_earnings': total_instructor_earnings,
          'total_payouts_received': total_payouts_received,
          'remaining_balance': remaining_balance,
          'platform_commission': platform_commission,
          'course_financials': course_financials,
          'payout_history': payout_history,
      },
  )


@login_required
def lesson_detail(request, course_pk, lesson_pk):
  course = get_object_or_404(Course, pk=course_pk)
  lesson = get_object_or_404(Lesson, pk=lesson_pk, course=course)

  is_instructor_owner = course.instructor == request.user
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()

  if (
      not is_enrolled
      and Payment.objects.filter(
          student=request.user, course=course, status='completed'
      ).exists()
  ):
    Enrollment.objects.get_or_create(student=request.user, course=course)
    is_enrolled = True

  if not (is_instructor_owner or is_enrolled):
    messages.error(
        request, 'يجب الاشتراك أو شراء الكورس أولاً لمشاهدة هذا الدرس.'
    )
    return redirect('course_detail', pk=course.pk)

  # إذا كان للدرس اختبار ولم يجتازه الطالب، إعادة التوجيه للاختبار قبل عرض الفيديو
  if not is_instructor_owner:
    try:
      quiz = lesson.quiz
      has_passed = QuizAttempt.objects.filter(
          student=request.user, quiz=quiz, passed=True
      ).exists()
      if not has_passed:
        messages.error(
            request, 'يجب सफल في اختبار هذا الدرس قبل مشاهدة الفيديو 🔒'
        )
        return redirect('quiz_detail', course.pk, lesson.pk)
    except Quiz.DoesNotExist:
      pass

  all_lessons = list(course.lessons.all().order_by('order'))

  if not is_instructor_owner:
    try:
      current_index = all_lessons.index(lesson)
    except ValueError:
      current_index = 0

    if current_index > 0:
      previous_lesson = all_lessons[current_index - 1]
      prev_completed = LessonProgress.objects.filter(
          student=request.user, lesson=previous_lesson, is_completed=True
      ).exists()

      if not prev_completed:
        messages.error(
            request,
            'عذراً، هذا الدرس مقفل. يجب إنهاء مشاهدة الدرس السابق حتى نهايته'
            ' أولاً 🔒',
        )
        return redirect('lesson_detail', course.pk, previous_lesson.pk)

  lessons_data = []
  completed_lesson_ids = set(
      LessonProgress.objects.filter(
          student=request.user, lesson__course=course, is_completed=True
      ).values_list('lesson_id', flat=True)
  )

  for index, item in enumerate(all_lessons):
    is_completed = item.id in completed_lesson_ids

    if is_instructor_owner or index == 0:
      is_unlocked = True
    else:
      prev_item = all_lessons[index - 1]
      is_unlocked = prev_item.id in completed_lesson_ids

    lessons_data.append({
        'lesson': item,
        'is_completed': is_completed,
        'is_unlocked': is_unlocked,
    })

  raw_url = lesson.video_url or ''
  embed_url = ''
  if 'youtube.com/watch?v=' in raw_url:
    video_id = raw_url.split('watch?v=')[1].split('&')[0]
    embed_url = f'https://www.youtube.com/embed/{video_id}'
  elif 'youtu.be/' in raw_url:
    video_id = raw_url.split('youtu.be/')[1].split('?')[0]
    embed_url = f'https://www.youtube.com/embed/{video_id}'
  elif 'drive.google.com' in raw_url:
    if '/file/d/' in raw_url:
      try:
        file_id = raw_url.split('/file/d/')[1].split('/')[0]
        embed_url = f'https://drive.google.com/file/d/{file_id}/preview'
      except IndexError:
        embed_url = raw_url
    elif 'id=' in raw_url:
      try:
        file_id = raw_url.split('id=')[1].split('&')[0]
        embed_url = f'https://drive.google.com/file/d/{file_id}/preview'
      except IndexError:
        embed_url = raw_url
  else:
    embed_url = raw_url

  # جلب وقت التوقف المسبق للدرس
  current_progress = LessonProgress.objects.filter(
      student=request.user, lesson=lesson
  ).first()
  saved_seconds = current_progress.watched_seconds if current_progress else 0.0

  # جلب تعليقات الدرس
  lesson_comments = LessonComment.objects.filter(
      lesson=lesson, is_approved=True
  ).select_related('student')

  return render(
      request,
      'courses/lesson_detail.html',
      {
          'course': course,
          'lesson': lesson,
          'lessons_data': lessons_data,
          'embed_url': embed_url,
          'is_enrolled': is_enrolled,
          'saved_seconds': saved_seconds,
          'lesson_comments': lesson_comments,
      },
  )


@login_required
def view_certificate(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()

  if not is_enrolled and course.instructor != request.user:
    messages.error(request, 'يجب أن تكون مشتركاً في الكورس لعرض الشهادة.')
    return redirect('course_detail', pk=course.pk)

  if course.instructor != request.user:
    total_lessons = course.lessons.count()
    completed_lessons = LessonProgress.objects.filter(
        student=request.user, lesson__course=course, is_completed=True
    ).count()

    if total_lessons > 0 and completed_lessons < total_lessons:
      messages.error(
          request,
          'لا يمكنك استعراض أو الحصول على الشهادة إلا بعد إتمام مشاهدة جميع'
          ' دروس الكورس بالكامل 🔒🏆',
      )
      return redirect('course_detail', pk=course.pk)

  certificate, created = Certificate.objects.get_or_create(
      student=request.user, course=course
  )

  # إرسال إيميل الشهادة عند إنشائها لأول مرة
  if created:
    send_certificate_email(request.user, course, certificate)

  # إنشاء رمز QR للتحقق من الشهادة
  verify_url = request.build_absolute_uri(
      reverse('verify_certificate_detail', args=[certificate.certificate_id])
  )
  qr = qrcode.QRCode(version=1, box_size=10, border=4)
  qr.add_data(verify_url)
  qr.make(fit=True)
  qr_img = qr.make_image(fill_color='#4f46e5', back_color='white')
  buffer = io.BytesIO()
  qr_img.save(buffer, format='PNG')
  qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

  return render(
      request,
      'courses/certificate.html',
      {
          'course': course,
          'certificate': certificate,
          'qr_code_base64': qr_code_base64,
      },
  )


@login_required
def mark_lesson_complete(request, lesson_pk):
  lesson = get_object_or_404(Lesson, pk=lesson_pk)
  course = lesson.course

  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()
  if not is_enrolled and course.instructor != request.user:
    return JsonResponse({'status': 'error', 'message': 'غير مشترك'}, status=403)

  progress, _ = LessonProgress.objects.get_or_create(
      student=request.user, lesson=lesson
  )
  progress.is_completed = True
  progress.save()

  # إنشاء إشعار عند إتمام الدرس
  Notification.objects.create(
      user=request.user,
      title='إتمام درس ✅',
      message=f'لقد أنهيت درس "{lesson.title}" بنجاح',
      link=reverse('lesson_detail', args=[course.pk, lesson.pk]),
  )
  # إرسال إيميل إتمام الدرس
  send_lesson_complete_email(request.user, lesson)

  all_lessons = list(course.lessons.all().order_by('order'))
  try:
    current_index = all_lessons.index(lesson)
    next_lesson = (
        all_lessons[current_index + 1]
        if current_index + 1 < len(all_lessons)
        else None
    )
  except ValueError:
    next_lesson = None

  if next_lesson:
    next_url = reverse('lesson_detail', args=[course.pk, next_lesson.pk])
  else:
    next_url = reverse('course_detail', args=[course.pk])

  return JsonResponse({'status': 'success', 'next_url': next_url})


@login_required
def save_video_progress(request, lesson_pk):
  """دالة جديدة لحفظ الثواني التي شاهدها الطالب دورياً عبر AJAX"""
  if request.method == 'POST':
    lesson = get_object_or_404(Lesson, pk=lesson_pk)
    try:
      data = json.loads(request.body)
      current_time = float(data.get('current_time', 0))

      progress, _ = LessonProgress.objects.get_or_create(
          student=request.user, lesson=lesson
      )
      progress.watched_seconds = current_time
      progress.save()

      return JsonResponse({'status': 'success'})
    except Exception as e:
      return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
  return JsonResponse({'status': 'invalid method'}, status=405)


@login_required
def get_signed_video_url(request, lesson_pk):
  """
  توليد رابط فيديو موقع ومؤقت من Cloudinary (Signed URL)
  لمنع تحميل الفيديو مباشرة أو مشاركته خارج المنصة.
  الرابط صالح لمدة ساعة واحدة فقط ويتطلب صلاحية مشاهدة الدرس.
  """
  lesson = get_object_or_404(Lesson, pk=lesson_pk)
  course = lesson.course

  # التحقق من صلاحية المشاهدة (نفس المنطق المستخدم في lesson_detail)
  is_instructor_owner = course.instructor == request.user
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()

  if (
      not is_enrolled
      and Payment.objects.filter(
          student=request.user, course=course, status='completed'
      ).exists()
  ):
    Enrollment.objects.get_or_create(student=request.user, course=course)
    is_enrolled = True

  if not (is_instructor_owner or is_enrolled):
    return JsonResponse(
        {'error': 'غير مسموح لك بمشاهدة هذا الفيديو'}, status=403
    )

  if not lesson.video_file:
    return JsonResponse({'error': 'لا يوجد فيديو مرفوع لهذا الدرس'}, status=404)

  # الرابط الموقع صالح لمدة ساعة (3600 ثانية)
  expires_at = int(time.time()) + 3600

  signed_url, _ = cloudinary_url(
      lesson.video_file.public_id,
      resource_type='video',
      sign_url=True,
      secure=True,
      expires_at=expires_at,
      # 압축 وتشفير لضمان التشغيل على المتصفحات والهواتف
      video_codec='h264',
      fetch_format='mp4',
  )

  return JsonResponse({'signed_url': signed_url})


@login_required
def quiz_detail(request, course_pk, lesson_pk):
  """عرض اختبار الدرس للطلاب المشتركين والمسموح لهم بالمشاهدة"""
  course = get_object_or_404(Course, pk=course_pk)
  lesson = get_object_or_404(Lesson, pk=lesson_pk, course=course)

  is_instructor_owner = course.instructor == request.user
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()
  if not is_enrolled and course.instructor != request.user:
    messages.error(request, 'يجب الاشتراك في الكورس أولاً لاختبار هذا الدرس.')
    return redirect('course_detail', pk=course.pk)

  try:
    quiz = lesson.quiz
  except Quiz.DoesNotExist:
    messages.error(request, 'لا يوجد اختبار مرفق بهذا الدرس حالياً.')
    return redirect('lesson_detail', course.pk, lesson.pk)

  # إذا كان الطالب قد اجتاز الاختبار بالفعل، أعرض له النتيجة أو انتقل للدرس التالي
  previous_passed = QuizAttempt.objects.filter(
      student=request.user, quiz=quiz, passed=True
  ).exists()
  last_attempt = QuizAttempt.objects.filter(
      student=request.user, quiz=quiz
  ).order_by('-completed_at').first()

  if request.method == 'POST' and not previous_passed:
    return submit_quiz(request, course_pk, lesson_pk)

  questions = quiz.questions.all().prefetch_related('choices')

  return render(
      request,
      'courses/quiz_detail.html',
      {
          'course': course,
          'lesson': lesson,
          'quiz': quiz,
          'questions': questions,
          'previous_passed': previous_passed,
          'last_attempt': last_attempt,
          'is_instructor_owner': is_instructor_owner,
      }
  )


@login_required
def submit_quiz(request, course_pk, lesson_pk):
  """استلام إجابات الاختبار، حساب النتيجة، وتحديد النجاح أو الرسوب"""
  course = get_object_or_404(Course, pk=course_pk)
  lesson = get_object_or_404(Lesson, pk=lesson_pk, course=course)

  try:
    quiz = lesson.quiz
  except Quiz.DoesNotExist:
    return JsonResponse({'error': 'لا يوجد اختبار'}, status=404)

  if request.method != 'POST':
    return JsonResponse({'error': 'طريقة غير مسموحة'}, status=405)

  questions = quiz.questions.all()
  total = questions.count()
  if total == 0:
    return JsonResponse({'error': 'الاختبار لا يحتوي على أسئلة'}, status=400)

  correct_count = 0
  for question in questions:
    selected_choice_id = request.POST.get(f'question_{question.id}')
    if not selected_choice_id:
      continue
    try:
      choice = Choice.objects.get(pk=selected_choice_id, question=question)
      if choice.is_correct:
        correct_count += 1
    except Choice.DoesNotExist:
      continue

  score = int((correct_count / total) * 100)
  passed = score >= quiz.passing_score

  attempt = QuizAttempt.objects.create(
      student=request.user,
      quiz=quiz,
      score=score,
      total_questions=total,
      passed=passed,
  )

  # حفظ إجابات الطالب
  for question in questions:
    selected_choice_id = request.POST.get(f'question_{question.id}')
    if selected_choice_id:
      try:
        choice = Choice.objects.get(pk=selected_choice_id, question=question)
        QuizAnswer.objects.create(
            attempt=attempt, question=question, choice=choice
        )
      except Choice.DoesNotExist:
        pass

  if passed:
    # إتمام الدرس تلقائياً عند نجاح الاختبار
    progress, _ = LessonProgress.objects.get_or_create(
        student=request.user, lesson=lesson
    )
    progress.is_completed = True
    progress.save()
    messages.success(
        request, f'ممتاز! لقد نجحت في الاختبار بدرجة {score}% وتم إتمام الدرس ✅'
    )
    # إنشاء إشعار لنجاح الاختبار
    Notification.objects.create(
        user=request.user,
        title='نجاح في الاختبار 🎉',
        message=f'لقد نجحت في اختبار درس "{lesson.title}" بدرجة {score}%',
        link=reverse('lesson_detail', args=[course.pk, lesson.pk]),
    )
    # إرسال إيميل نجاح الاختبار
    send_quiz_pass_email(request.user, lesson, score)
    return redirect('lesson_detail', course.pk, lesson.pk)
  else:
    messages.error(
        request, f'للأسف لم تنجح. درجاتك {score}% والنجاح يتطلب {quiz.passing_score}% على الأقل. يمكنك المحاولة مرة أخرى.'
    )
    return redirect('quiz_detail', course.pk, lesson.pk)


def about_view(request):
  """صفحة حول المنصة"""
  return render(request, 'courses/about.html')


def contact_view(request):
  """صفحة اتصل بنا واستلام الرسائل"""
  if request.method == 'POST':
    name = request.POST.get('name')
    email = request.POST.get('email')
    subject = request.POST.get('subject')
    message = request.POST.get('message')

    if not all([name, email, subject, message]):
      messages.error(request, 'يرجى ملء جميع الحقول.')
      return render(request, 'courses/contact.html')

    ContactMessage.objects.create(
        name=name, email=email, subject=subject, message=message
    )
    messages.success(request, 'تم إرسال رسالتك بنجاح! سنرد عليك في أقرب وقت ممكن 📨')
    return redirect('contact')

  return render(request, 'courses/contact.html')


@login_required
def toggle_favorite(request, course_pk):
  """إضافة أو إزالة الكورس من المفضلة عبر AJAX"""
  course = get_object_or_404(Course, pk=course_pk)
  favorite, created = Favorite.objects.get_or_create(
      student=request.user, course=course
  )
  if not created:
    favorite.delete()
    return JsonResponse({'status': 'removed', 'message': 'تم إزالة الكورس من المفضلة'})
  return JsonResponse({'status': 'added', 'message': 'تم إضافة الكورس للمفضلة'})


@login_required
def favorite_list(request):
  """عرض الكورسات المفضلة للطالب"""
  favorites = Favorite.objects.filter(student=request.user).select_related('course')
  return render(
      request,
      'courses/favorite_list.html',
      {'favorites': favorites}
  )


@login_required
def notification_list(request):
  """عرض إشعارات المستخدم"""
  notifications = Notification.objects.filter(user=request.user)
  unread_count = notifications.filter(is_read=False).count()
  return render(
      request,
      'courses/notification_list.html',
      {'notifications': notifications, 'unread_count': unread_count}
  )


@login_required
def mark_notification_read(request, notification_id):
  """تحديد إشعار كمقروء"""
  notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
  notification.is_read = True
  notification.save()
  if notification.link:
    return redirect(notification.link)
  return redirect('notification_list')


@login_required
def course_questions(request, course_pk):
  """عرض جميع أسئلة وإجابات الكورس"""
  course = get_object_or_404(Course, pk=course_pk)
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists() or course.instructor == request.user
  if not is_enrolled:
    messages.error(request, 'يجب الاشتراك في الكورس لمشاهدة أسئلته.')
    return redirect('course_detail', pk=course.pk)

  questions = course.course_questions.all().prefetch_related('answers__student')
  return render(
      request,
      'courses/course_questions.html',
      {'course': course, 'questions': questions}
  )


@login_required
def add_course_question(request, course_pk):
  """إضافة سؤال جديد للكورس"""
  course = get_object_or_404(Course, pk=course_pk)
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists() or course.instructor == request.user
  if not is_enrolled:
    messages.error(request, 'يجب الاشتراك في الكورس لإضافة سؤال.')
    return redirect('course_detail', pk=course.pk)

  if request.method == 'POST':
    title = request.POST.get('title')
    content = request.POST.get('content')
    if not title or not content:
      messages.error(request, 'يرجى ملء جميع الحقول.')
      return redirect('course_questions', course.pk)
    CourseQuestion.objects.create(
        course=course, student=request.user, title=title, content=content
    )
    messages.success(request, 'تم إرسال سؤالك بنجاح! سيتم الرد عليك قريباً 📨')
    return redirect('course_questions', course.pk)

  return redirect('course_questions', course.pk)


@login_required
def add_course_answer(request, question_pk):
  """إضافة إجابة على سؤال (للمدرس أو أي مستجيب)"""
  question = get_object_or_404(CourseQuestion, pk=question_pk)
  course = question.course
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists() or course.instructor == request.user
  if not is_enrolled:
    messages.error(request, 'غير مسموح لك بالإجابة على هذا السؤال.')
    return redirect('course_questions', course.pk)

  if request.method == 'POST':
    content = request.POST.get('content')
    if not content:
      messages.error(request, 'يرجى كتابة الإجابة.')
      return redirect('course_questions', course.pk)
    CourseAnswer.objects.create(
        question=question, student=request.user, content=content
    )
    messages.success(request, 'تم إضافة إجابتك بنجاح ✍️')
    return redirect('course_questions', course.pk)

  return redirect('course_questions', course.pk)


def bundle_list(request):
  """عرض جميع الباقات المتاحة"""
  bundles = CourseBundle.objects.filter(is_active=True).prefetch_related('courses')
  return render(request, 'courses/bundle_list.html', {'bundles': bundles})


@login_required
def add_instructor_rating(request, course_pk):
  """تقييم المدرس لدورة معينة"""
  course = get_object_or_404(Course, pk=course_pk)

  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()
  if not is_enrolled:
    messages.error(request, 'يجب الاشتراك في الكورس لتقييم المدرس.')
    return redirect('course_detail', pk=course.pk)

  if request.method == 'POST':
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    if not rating:
      messages.error(request, 'يرجى اختيار تقييم.')
      return redirect('course_detail', pk=course.pk)
    try:
      rating = int(rating)
      if rating < 1 or rating > 5:
        raise ValueError()
    except ValueError:
      messages.error(request, 'التقييم يجب أن يكون بين 1 و 5 نجوم.')
      return redirect('course_detail', pk=course.pk)

    InstructorRating.objects.update_or_create(
        instructor=course.instructor,
        student=request.user,
        course=course,
        defaults={'rating': rating, 'comment': comment},
    )
    messages.success(request, 'تم تقييم المدرس بنجاح ✅')
    return redirect('course_detail', pk=course.pk)

  return redirect('course_detail', pk=course.pk)


@login_required
def add_lesson_comment(request, lesson_pk):
  """إضافة تعليق على درس"""
  lesson = get_object_or_404(Lesson, pk=lesson_pk)
  course = lesson.course

  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists() or course.instructor == request.user
  if not is_enrolled:
    messages.error(request, 'يجب الاشتراك في الكورس لإضافة تعليق.')
    return redirect('lesson_detail', course.pk, lesson.pk)

  if request.method == 'POST':
    content = request.POST.get('content')
    if not content:
      messages.error(request, 'يرجى كتابة التعليق.')
      return redirect('lesson_detail', course.pk, lesson.pk)
    LessonComment.objects.create(
        lesson=lesson, student=request.user, content=content
    )
    messages.success(request, 'تم إضافة تعليقك بنجاح ✍️')
    return redirect('lesson_detail', course.pk, lesson.pk)

  return redirect('lesson_detail', course.pk, lesson.pk)


def bundle_detail(request, bundle_pk):
  """تفاصيل الباقة وخيار الشراء"""
  bundle = get_object_or_404(CourseBundle, pk=bundle_pk)
  
  if request.method == 'POST' and request.user.is_authenticated:
    # إنشاء عملية شراء للباقة
    purchase = BundlePurchase.objects.create(
        student=request.user,
        bundle=bundle,
        amount_paid=bundle.price,
        status='completed',
    )
    # تسجيل الطالب في جميع الكورسات في الباقة
    for course in bundle.courses.all():
      Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, f'تم شراء باقة "{bundle.title}" بنجاح! يمكنك الآن الوصول لجميع الكورسات 🚀')
    return redirect('course_list')

  return render(request, 'courses/bundle_detail.html', {'bundle': bundle})


def verify_certificate(request, certificate_id=None):
  """التحقق من صحة شهادة عبر معرفها الفريد (متاح للجميع بدون تسجيل دخول)"""
  if certificate_id is None:
    # عرض نموذج التحقق فقط
    return render(request, 'courses/verify_certificate.html', {'found': None})

  try:
    certificate = Certificate.objects.get(certificate_id=certificate_id)
  except Certificate.DoesNotExist:
    return render(
        request,
        'courses/verify_certificate.html',
        {'found': False, 'certificate_id': certificate_id}
    )

  # حساب نسبة الإكمال للتأكد
  total_lessons = certificate.course.lessons.count()
  completed_lessons = LessonProgress.objects.filter(
      student=certificate.student, lesson__course=certificate.course,
      is_completed=True
  ).count()

  return render(
      request,
      'courses/verify_certificate.html',
      {
          'found': True,
          'certificate': certificate,
          'total_lessons': total_lessons,
          'completed_lessons': completed_lessons,
      }
  )