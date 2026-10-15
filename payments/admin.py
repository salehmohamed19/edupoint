from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
  list_display = (
      'id',
      'student',
      'course',
      'amount',
      'payment_method',
      'status',  # تم إضافتها هنا لتتوافق مع list_editable
      'status_colored',
      'created_at',
      'receipt_preview',
  )
  list_filter = ('status', 'payment_method', 'created_at')
  search_fields = (
      'student__username',
      'student__email',
      'course__title',
      'transaction_id',
  )
  list_editable = ('status',)  # تعديل حالة الطلب مباشرة من القائمة
  readonly_fields = ('receipt_preview_large', 'created_at')

  def status_colored(self, obj):
    colors = {
        'pending': 'orange',
        'pending_verification': '#d97706',
        'completed': 'green',
        'failed': 'red',
    }
    color = colors.get(obj.status, 'black')
    return format_html(
        '<span style="color: {}; font-weight: bold;">{}</span>',
        color,
        obj.get_status_display(),
    )

  status_colored.short_description = 'لون الحالة'

  def receipt_preview(self, obj):
    if obj.receipt:
      return format_html(
          '<a href="{}" target="_blank"><img src="{}" width="50" height="50"'
          ' style="object-fit: cover; border-radius: 4px;" /></a>',
          obj.receipt.url,
          obj.receipt.url,
      )
    return 'لا يوجد إيصال'

  receipt_preview.short_description = 'معاينة الإيصال'

  def receipt_preview_large(self, obj):
    if obj.receipt:
      return format_html(
          '<a href="{}" target="_blank"><img src="{}" width="300"'
          ' style="border-radius: 8px; border: 1px solid #ccc;" /></a><br><a'
          ' href="{}" target="_blank" style="display:inline-block; margin-top:'
          ' 10px;">فتح الصورة بالحجم الكامل 🔍</a>',
          obj.receipt.url,
          obj.receipt.url,
          obj.receipt.url,
      )
    return 'لا يوجد إيصال مرفق'

  receipt_preview_large.short_description = 'صورة الإيصال الكاملة للمراجعة'

  