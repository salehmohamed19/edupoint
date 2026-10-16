from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from payments.models import Payment
from .models import (
    Certificate,
    Course,
    Enrollment,
    InstructorPayout,
    Lesson,
    LessonProgress,
    Review,
)


def course_list(request):
  query = request.GET.get('q', '')
  courses = Course.objects.all()
  if query:
    courses = courses.filter(title__icontains=query)
  return render(
      request, 'courses/course_list.html', {'courses': courses, 'query': query}
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

  # حساب حالة القفل والفتح للدروس لعرضها بدقة في صفحة تفاصيل الكورس
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
          'lessons_data': lessons_data,
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
  
  # التأكد أن المدرس هو مالك الكورس
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

  # التأكد أن المستخدم هو مدرس الكورس مالك الدرس
  if course.instructor != request.user:
    messages.error(request, 'غير مسموح لك بتعديل هذا الدرس.')
    return redirect('course_detail', pk=course.pk)

  if request.method == 'POST':
    lesson.title = request.POST.get('title')
    lesson.video_url = request.POST.get('video_url')
    
    # تحديث ملف الفيديو إن وجد ملف جديد مرفوع
    if request.FILES.get('video_file'):
      lesson.video_file = request.FILES.get('video_file')
      
    lesson.description = request.POST.get('description')
    
    # تحديث الملف المرفق إن وجد ملف جديد
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
  return render(
      request, 'courses/student_dashboard.html', {'enrollments': enrollments}
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

  all_lessons = list(course.lessons.all().order_by('order'))

  # --- نظام القفل والتتابع الصارم ---
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

  # بناء حالة القفل والفتح لكل درس بدقة تامة
  lessons_data = []
  completed_lesson_ids = set(
      LessonProgress.objects.filter(
          student=request.user, lesson__course=course, is_completed=True
      ).values_list('lesson_id', flat=True)
  )

  for index, item in enumerate(all_lessons):
    is_completed = item.id in completed_lesson_ids

    # الدرس الأول مفتوح دائماً، والباقي لا يفتح إلا بإتمام الدرس السابق فعلياً
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

  # معالجة روابط الفيديو
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

  return render(
      request,
      'courses/lesson_detail.html',
      {
          'course': course,
          'lesson': lesson,
          'lessons_data': lessons_data,
          'embed_url': embed_url,
          'is_enrolled': is_enrolled,
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

  # --- نظام قفل الشهادة حتى إتمام جميع دروس الكورس ---
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

  return render(
      request,
      'courses/certificate.html',
      {'course': course, 'certificate': certificate},
  )

from django.http import JsonResponse
from django.urls import reverse

@login_required
def mark_lesson_complete(request, lesson_pk):
  lesson = get_object_or_404(Lesson, pk=lesson_pk)
  course = lesson.course

  # التحقق من أن الطالب مشترك
  is_enrolled = Enrollment.objects.filter(
      student=request.user, course=course
  ).exists()
  if not is_enrolled and course.instructor != request.user:
    return JsonResponse({'status': 'error', 'message': 'غير مشترك'}, status=403)

  # تسجيل إتمام الدرس
  progress, _ = LessonProgress.objects.get_or_create(
      student=request.user, lesson=lesson
  )
  progress.is_completed = True
  progress.save()

  # البحث عن الدرس التالي
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