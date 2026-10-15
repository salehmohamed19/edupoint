from courses.models import Course
from django.contrib.auth.models import User
from django.db import models


class Payment(models.Model):
  student = models.ForeignKey(User, on_delete=models.CASCADE)
  course = models.ForeignKey(Course, on_delete=models.CASCADE)
  amount = models.DecimalField(max_digits=8, decimal_places=2)
  provider = models.CharField(max_length=50, default='ManualPayment')
  
  # تفاصيل الدفع اليدوي
  payment_method = models.CharField(
      max_length=50,
      choices=[
          ('vodafone_cash', 'فودافون كاش'),
          ('instapay', 'إنستاباي (Instapay)'),
          ('bank_transfer', 'تحويل بنكي'),
          ('fawry', 'خدمة فوري'),
      ],
      default='vodafone_cash',
  )
  receipt = models.FileField(
      upload_to='payment_receipts/',
      blank=True,
      null=True,
      help_text='صورة أو ملف إيصال الدفع لتأكيد العملية',
  )
  
  transaction_id = models.CharField(max_length=255, blank=True, null=True)
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