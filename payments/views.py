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

  # التحقق إذا كان لدى الطالب اشتراك مكتمل أو طلب قيد المراجعة حالياً
  existing_completed = Payment.objects.filter(
      student=request.user, course=course, status='completed'
  ).exists()
  
  if existing_completed:
    messages.info(request, 'أنت مشترك بالفعل في هذا الكورس.')
    return redirect('course_detail', pk=course.pk)

  # إذا أرسل المستخدم بيانات الدفع والإيصال عبر نموذج POST
  if request.method == 'POST':
    payment_method = request.POST.get('payment_method', 'vodafone_cash')
    receipt = request.FILES.get('receipt')

    if not receipt:
      messages.error(request, 'يرجى إرفاق صورة أو ملف إيصال الدفع.')
      return redirect('initiate_payment', course_pk=course.pk)

    # البحث عن أي طلب سابق معلق أو قيد المراجعة لنفس الطالب والكورس وتحديثه بدلاً من التكرار
    payment, created = Payment.objects.update_or_create(
        student=request.user,
        course=course,
        status__in=['pending', 'pending_verification'],
        defaults={
            'amount': course.price,
            'provider': 'ManualTransfer',
            'payment_method': payment_method,
            'receipt': receipt,
            'status': 'pending_verification',
        }
    )
    
    messages.success(request, 'تم إرسال إيصال الدفع بنجاح! سيتم مراجعته وتفعيل اشتراكك قريباً.')
    return redirect('payment_success', payment_id=payment.id)

  # في حالة عرض صفحة الـ checkout فقط (GET) - لا نقوم بإنشاء سجل فارغ في قاعدة البيانات
  # بل نأخذ السجل القديم المعلق إن وجد لعرض بياناته أو نترك الكورس للعرض فقط
  payment = Payment.objects.filter(
      student=request.user, course=course, status__in=['pending', 'pending_verification']
  ).first()

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