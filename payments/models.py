from courses.models import Coupon, Course
from django.contrib.auth.models import User
from django.db import models


class Payment(models.Model):
  student = models.ForeignKey(User, on_delete=models.CASCADE)
  course = models.ForeignKey(Course, on_delete=models.CASCADE)
  amount = models.DecimalField(max_digits=8, decimal_places=2)
  discounted_amount = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text='المبلغ بعد تطبيق خصم الكوبون')
  provider = models.CharField(max_length=50, default='ManualPayment')
  
  # تفاصيل الدفع اليدوي
  payment_method = models.CharField(
      max_length=50,
      choices=[
          ('vodafone_cash', 'فودافون كاش'),
          ('instapay', 'إنستاباي (Instapay)'),
          ('bank_transfer', 'تحويل بنكي'),
          ('fawry', 'خدمة فوري'),
          ('paymob', 'Paymob (دفع إلكتروني)'),
      ],
      default='vodafone_cash',
  )
  coupon = models.ForeignKey(
      Coupon, on_delete=models.SET_NULL, null=True, blank=True,
      related_name='payments', verbose_name='كوبون الخصم المستخدم'
  )
  receipt = models.FileField(
      upload_to='payment_receipts/',
      blank=True,
      null=True,
      help_text='صورة أو ملف إيصال الدفع لتأكيد العملية',
  )
  
  transaction_id = models.CharField(max_length=255, blank=True, null=True)
  paymob_order_id = models.CharField(max_length=255, blank=True, null=True, help_text='رقم الطلب في Paymob')
  paymob_transaction_id = models.CharField(max_length=255, blank=True, null=True, help_text='رقم المعاملة في Paymob')
  status = models.CharField(
      max_length=30,
      choices=[
          ('pending', 'قيد الانتظار'),
          ('pending_verification', 'قيد المراجعة (بانتظار الموافقة)'),
          ('completed', 'مكتمل ومفعل'),
          ('failed', 'فشل'),
      ],
      default='pending',
  )
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f'Payment {self.id} - {self.student.username} - {self.status}'