import hmac
import hashlib
import json
import requests
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from courses.email_utils import send_enrollment_email
from courses.models import Coupon, Course, Enrollment
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

  # حساب المبلغ بعد تطبيق الكوبون إن وجد
  coupon_code = request.GET.get('coupon') or request.POST.get('coupon_code', '')
  coupon = None
  discounted_amount = course.price
  coupon_error = ''

  if coupon_code:
    try:
      coupon = Coupon.objects.get(code__iexact=coupon_code)
      if coupon.is_valid() and (coupon.course is None or coupon.course == course):
        discounted_amount = course.price - coupon.calculate_discount(course.price)
        if discounted_amount < 0:
          discounted_amount = Decimal('0.00')
      else:
        coupon_error = 'كود الخصم غير صالح أو منتهٍ الصلاحية أو مستنفد.'
        coupon = None
    except Coupon.DoesNotExist:
      coupon_error = 'كود الخصم غير موجود.'
      coupon = None

  # الدفع الإلكتروني عبر Paymob
  if request.method == 'POST':
    payment_method = request.POST.get('payment_method', 'vodafone_cash')

    if payment_method == 'paymob':
      # إنشاء سجل دفع معلق
      payment, _ = Payment.objects.update_or_create(
          student=request.user,
          course=course,
          status__in=['pending', 'pending_verification'],
          defaults={
              'amount': discounted_amount,
              'discounted_amount': discounted_amount if discounted_amount != course.price else None,
              'provider': 'Paymob',
              'payment_method': 'paymob',
              'coupon': coupon,
              'status': 'pending',
          }
      )

      # بدء سلسلة Paymob: Auth Token → Order → Payment Key → Redirect
      paymob_result = create_paymob_payment(request, course, payment)
      if paymob_result.get('error'):
        messages.error(request, paymob_result['error'])
        return redirect('initiate_payment', course_pk=course.pk)

      payment.paymob_order_id = paymob_result['order_id']
      payment.save()

      # توجيه المستخدم لصفحة الدفع على Paymob (iframe)
      iframe_url = paymob_result['iframe_url']
      return redirect(iframe_url)

    # الدفع اليدوي (فودافون كاش، إنستاباي، إلخ)
    receipt = request.FILES.get('receipt')

    if not receipt:
      messages.error(request, 'يرجى إرفاق صورة أو ملف إيصال الدفع.')
      return redirect('initiate_payment', course_pk=course.pk)

    payment, created = Payment.objects.update_or_create(
        student=request.user,
        course=course,
        status__in=['pending', 'pending_verification'],
        defaults={
            'amount': discounted_amount,
            'discounted_amount': discounted_amount if discounted_amount != course.price else None,
            'provider': 'ManualTransfer',
            'payment_method': payment_method,
            'coupon': coupon,
            'receipt': receipt,
            'status': 'pending_verification',
        }
    )
    
    messages.success(request, 'تم إرسال إيصال الدفع بنجاح! سيتم مراجعته وتفعيل اشتراكك قريباً.')
    return redirect('payment_success', payment_id=payment.id)

  # في حالة عرض صفحة الـ checkout فقط (GET)
  payment = Payment.objects.filter(
      student=request.user, course=course, status__in=['pending', 'pending_verification']
  ).first()

  return render(
      request, 'payments/checkout.html', {
          'course': course, 
          'payment': payment,
          'coupon': coupon,
          'coupon_code': coupon_code,
          'discounted_amount': discounted_amount,
          'coupon_error': coupon_error,
      }
  )


def create_paymob_payment(request, course, payment):
  """
  تنفيذ خطوات Paymob الثلاث:
  1. طلب Authentication Token
  2. إنشاء Order
  3. طلب Payment Key و توليد رابط الدفع (iframe)
  """
  try:
    # الخطوة 1: Authentication Token
    auth_url = f"{settings.PAYMOB_BASE_URL}/api/auth/tokens"
    auth_payload = {'api_key': settings.PAYMOB_API_KEY}
    auth_resp = requests.post(auth_url, json=auth_payload, timeout=30)
    auth_resp.raise_for_status()
    token = auth_resp.json().get('token')
    if not token:
      return {'error': 'فشل في الحصول على رمز المصادقة من Paymob'}

    # الخطوة 2: إنشاء Order
    order_url = f"{settings.PAYMOB_BASE_URL}/api/ecommerce/orders"
    order_payload = {
        'auth_token': token,
        'delivery_needed': 'false',
        'amount_cents': int(course.price * 100),
        'currency': 'EGP',
        'merchant_order_id': f'{payment.id}_{course.id}_{request.user.id}',
        'items': [
            {
                'name': course.title,
                'amount_cents': int(course.price * 100),
                'description': 'دفع اشتراك كورس EduPoint',
                'quantity': 1
            }
        ]
    }
    order_resp = requests.post(order_url, json=order_payload, timeout=30)
    order_resp.raise_for_status()
    order_data = order_resp.json()
    order_id = order_data.get('id')
    if not order_id:
      return {'error': 'فشل في إنشاء طلب الدفع على Paymob'}

    # الخطوة 3: طلب Payment Key
    payment_key_url = f"{settings.PAYMOB_BASE_URL}/api/acceptance/payment_keys"
    billing_data = {
        'apartment': '',
        'email': request.user.email or '',
        'floor': '',
        'first_name': request.user.first_name or request.user.username,
        'last_name': request.user.last_name or '',
        'street': '',
        'building': '',
        'phone_number': getattr(request.user.userprofile, 'phone', '') or '',
        'shipping_method': '',
        'country': 'EG',
        'city': '',
        'state': '',
        'zip_code': '',
    }
    key_payload = {
        'auth_token': token,
        'amount_cents': int(course.price * 100),
        'expiration': 3600,  # دقيقة واحدة
        'order_id': order_id,
        'currency': 'EGP',
        'billing_data': billing_data,
        'integration_id': settings.PAYMOB_INTEGRATION_ID,
    }
    key_resp = requests.post(payment_key_url, json=key_payload, timeout=30)
    key_resp.raise_for_status()
    key_data = key_resp.json()
    payment_key = key_data.get('token')
    if not payment_key:
      return {'error': 'فشل في إنشاء مفتاح الدفع من Paymob'}

    # توليد رابط الـ iframe الخاص بالدفع
    iframe_url = (
        f"https://accept.paymob.com/api/acceptance/iframes/{settings.PAYMOB_IFRAME_ID}"
        f"?payment_token={payment_key}"
    )

    return {
        'order_id': str(order_id),
        'payment_key': payment_key,
        'iframe_url': iframe_url,
    }

  except requests.RequestException as e:
    return {'error': f'خطأ في الاتصال بـ Paymob: {str(e)}'}
  except Exception as e:
    return {'error': f'خطأ غير متوقع: {str(e)}'}


@login_required
def payment_success(request, payment_id):
  payment = get_object_or_404(
      Payment, pk=payment_id, student=request.user
  )

  return render(
      request, 'payments/success.html', {'payment': payment, 'course': payment.course}
  )


@csrf_exempt
@require_POST
def paymob_webhook(request):
  """
  Webhook من Paymob لإشعارنا بنتيجة الدفع.
  نتحقق من التوقيع (HMAC) ثم نفعل الاشتراك إذا نجح الدفع.
  """
  try:
    payload = request.body.decode('utf-8')
    data = json.loads(payload)

    # التحقق من HMAC Secret
    hmac_secret = settings.PAYMOB_HMAC_SECRET
    received_hmac = request.META.get('HTTP_HMAC', '') or data.get('hmac', '')

    # بناء سلسلة التوقيع حسب ترتيب حقول Paymob
    hmac_string = (
        f"{data.get('amount_cents', '')}"
        f"{data.get('created_at', '')}"
        f"{data.get('currency', '')}"
        f"{data.get('error_occurred', '')}"
        f"{data.get('has_parent_transaction', '')}"
        f"{data.get('id', '')}"
        f"{data.get('integration_id', '')}"
        f"{data.get('is_3d_secure', '')}"
        f"{data.get('is_auth', '')}"
        f"{data.get('is_capture', '')}"
        f"{data.get('is_refunded', '')}"
        f"{data.get('is_standalone_payment', '')}"
        f"{data.get('is_voided', '')}"
        f"{data.get('order', {}).get('id', '')}"
        f"{data.get('owner', {})}"
        f"{data.get('payload', {}).get('pan', '')}"
        f"{data.get('source_data', {}).get('pan', '')}"
        f"{data.get('success', '')}"
    )

    calculated_hmac = hmac.new(
        hmac_secret.encode('utf-8'),
        hmac_string.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(calculated_hmac, received_hmac):
      return HttpResponse('Invalid HMAC', status=400)

    # استخراج بيانات الطلب
    success = data.get('success', False)
    order_info = data.get('order', {})
    order_id = order_info.get('id')

    if not order_id:
      return HttpResponse('No order ID', status=400)

    # البحث عن الدفع في قاعدة بياناتنا
    try:
      payment = Payment.objects.get(paymob_order_id=str(order_id))
    except Payment.DoesNotExist:
      return HttpResponse('Payment not found', status=404)

    if success:
      if payment.status != 'completed':
        payment.status = 'completed'
        payment.paymob_transaction_id = str(data.get('id', ''))
        payment.transaction_id = str(data.get('id', ''))
        payment.save()

        # تفعيل الاشتراك للطالب
        _, created = Enrollment.objects.get_or_create(student=payment.student, course=payment.course)
        if created:
          send_enrollment_email(payment.student, payment.course)

        # إشعار نجاح (إذا وُجد نظام الإشعارات)
        try:
          from courses.models import Notification
          Notification.objects.create(
              user=payment.student,
              title='تم تفعيل اشتراكك ✅',
              message=f'تم دفع كورس "{payment.course.title}" بنجاح عبر Paymob ويمكنك مشاهدة الدروس الآن.',
              link=reverse('course_detail', args=[payment.course.id]),
          )
        except Exception:
          pass

    else:
      payment.status = 'failed'
      payment.save()

    return HttpResponse('OK', status=200)

  except json.JSONDecodeError:
    return HttpResponse('Invalid JSON', status=400)
  except Exception as e:
    return HttpResponse(f'Error: {str(e)}', status=500)