from courses.models import Course, Enrollment
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Payment


@login_required
def initiate_payment(request, course_pk):
  course = get_object_or_404(Course, pk=course_pk)

  # لو الكورس مجاني، سجله مباشرة بدون دفع
  if course.is_free:
    Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, f'تم انضمامك بنجاح إلى كورس "{course.title}" 🚀')
    return redirect('course_detail', pk=course.pk)

  # التحقق إذا كان لدى الطالب عملية دفع سابقة مكتملة أو قيد المراجعة لنفس الكورس
  existing_payment = Payment.objects.filter(
      student=request.user, course=course, status__in=['completed', 'pending_verification']
  ).first()
  
  if existing_payment:
    if existing_payment.status == 'completed':
      messages.info(request, 'أنت مشترك بالفعل في هذا الكورس.')
      return redirect('course_detail', pk=course.pk)
    else:
      messages.info(request, 'لديك طلب دفع سابق قيد المراجعة من قِبل الإدارة.')
      return redirect('course_detail', pk=course.pk)

  # إذا أرسل المستخدم بيانات الدفع والإيصال عبر نموذج POST
  if request.method == 'POST':
    payment_method = request.POST.get('payment_method', 'vodafone_cash')
    receipt = request.FILES.get('receipt')

    if not receipt:
      messages.error(request, 'يرجى إرفاق صورة أو ملف إيصال الدفع.')
      return redirect('initiate_payment', course_pk=course.pk)

    # إنشاء سجل الدفع اليدوي
    payment = Payment.objects.create(
        student=request.user,
        course=course,
        amount=course.price,
        provider='ManualTransfer',
        payment_method=payment_method,
        receipt=receipt,
        status='pending_verification',
    )
    
    messages.success(request, 'تم إرسال إيصال الدفع بنجاح! سيتم مراجعته وتفعيل اشتراكك قريباً.')
    return redirect('payment_success', payment_id=payment.id)

  # إنشاء سجل مبدئي عرضي لعرض المبلغ في صفحة التشيك آوت
  payment, _ = Payment.objects.get_or_create(
      student=request.user,
      course=course,
      status='pending',
      defaults={'amount': course.price}
  )

  return render(
      request, 'payments/checkout.html', {'course': course, 'payment': payment}
  )


@login_required
def payment_success(request, payment_id):
  payment = get_object_or_404(
      Payment, pk=payment_id, student=request.user
  )

  return render(
      request, 'payments/success.html', {'payment': payment, 'course': payment.course}
  )