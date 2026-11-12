import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
  name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
  slug = models.SlugField(unique=True, verbose_name='الرابط المختصر')
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    verbose_name = 'تصنيف'
    verbose_name_plural = 'تصنيفات'
    ordering = ['name']

  def __str__(self):
    return self.name


class Course(models.Model):
  title = models.CharField(max_length=200)
  description = models.TextField()
  category = models.ForeignKey(
      Category, on_delete=models.SET_NULL, null=True, blank=True,
      related_name='courses', verbose_name='التصنيف'
  )
  instructor = models.ForeignKey(
      User, on_delete=models.CASCADE, related_name='courses'
  )
  price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
  is_free = models.BooleanField(default=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return self.title


from cloudinary.models import CloudinaryField
from django.contrib.auth.models import User
from django.db import models


class Lesson(models.Model):
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='lessons'
  )
  title = models.CharField(max_length=200)
  description = models.TextField(
      blank=True, null=True, help_text='وصف بسيط أو ملاحظات حول الدرس'
  )

  # استخدام Cloudinary لتخزين وبث الفيديوهات بـ Controls كاملة
  video_file = CloudinaryField(
      'video',
      resource_type='video',
      blank=True,
      null=True,
      help_text='رفع ملف الفيديو إلى السحاب (Cloudinary)',
  )

  video_url = models.URLField(
      blank=True,
      null=True,
      help_text='رابط يوتيوب اختياري في حال عدم رفع ملف',
  )

  attachment = models.FileField(
      upload_to='lesson_attachments/', blank=True, null=True
  )
  order = models.PositiveIntegerField(default=1)

  class Meta:
    ordering = ['order']

  def __str__(self):
    return f'{self.course.title} - {self.title}'


class Enrollment(models.Model):
  student = models.ForeignKey(
      User, on_delete=models.CASCADE, related_name='enrollments'
  )
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='enrollee_set'
  )
  enrolled_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f'{self.student.username} enrolled in {self.course.title}'


class Review(models.Model):
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='reviews'
  )
  student = models.ForeignKey(User, on_delete=models.CASCADE)
  rating = models.PositiveIntegerField(
      default=5, choices=[(i, str(i)) for i in range(1, 6)]
  )
  comment = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return (
        f'{self.student.username} - {self.course.title} ({self.rating} Stars)'
    )


class Certificate(models.Model):
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name='certificates',
  )
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='certificates'
  )
  certificate_id = models.UUIDField(
      default=uuid.uuid4, editable=False, unique=True
  )
  issued_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return (
        f'شهادة {self.student.get_full_name() or self.student.username}'
        f' - {self.course.title}'
    )


class InstructorPayout(models.Model):
  instructor = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name='payouts',
  )
  amount = models.DecimalField(max_digits=10, decimal_places=2)
  notes = models.TextField(
      blank=True, null=True
  )  # مثل: تحويل فودافون كاش / تحويل بنكي
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return (
        f'تحويل بقيمة {self.amount} لـ'
        f' {self.instructor.get_full_name() or self.instructor.username}'
    )


class LessonProgress(models.Model):
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name='lesson_progress',
  )
  lesson = models.ForeignKey(
      Lesson, on_delete=models.CASCADE, related_name='progress'
  )
  is_completed = models.BooleanField(default=False)
  watched_seconds = models.FloatField(default=0.0)
  completed_at = models.DateTimeField(auto_now=True)

  class Meta:
    unique_together = ('student', 'lesson')

  def __str__(self):
    return f'{self.student.username} - {self.lesson.title} (مكتمل)'


class Quiz(models.Model):
  lesson = models.OneToOneField(
      Lesson, on_delete=models.CASCADE, related_name='quiz'
  )
  title = models.CharField(max_length=200, default='اختبار الدرس')
  passing_score = models.PositiveIntegerField(
      default=70, help_text='النسبة المئوية المطلوبة للنجاح (مثلاً 70)'
  )
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    verbose_name = 'اختبار'
    verbose_name_plural = 'اختبارات'

  def __str__(self):
    return f'اختبار: {self.lesson.title}'


class Question(models.Model):
  quiz = models.ForeignKey(
      Quiz, on_delete=models.CASCADE, related_name='questions'
  )
  text = models.TextField(verbose_name='نص السؤال')
  order = models.PositiveIntegerField(default=1)

  class Meta:
    ordering = ['order']
    verbose_name = 'سؤال'
    verbose_name_plural = 'أسئلة'

  def __str__(self):
    return self.text[:60]


class Choice(models.Model):
  question = models.ForeignKey(
      Question, on_delete=models.CASCADE, related_name='choices'
  )
  text = models.CharField(max_length=255, verbose_name='نص الخيار')
  is_correct = models.BooleanField(default=False, verbose_name='إجابة صحيحة؟')

  class Meta:
    verbose_name = 'خيار'
    verbose_name_plural = 'خيارات'

  def __str__(self):
    return self.text


class QuizAttempt(models.Model):
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts'
  )
  quiz = models.ForeignKey(
      Quiz, on_delete=models.CASCADE, related_name='attempts'
  )
  score = models.PositiveIntegerField(default=0)
  total_questions = models.PositiveIntegerField(default=0)
  passed = models.BooleanField(default=False)
  completed_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-completed_at']
    verbose_name = 'محاولة اختبار'
    verbose_name_plural = 'محاولات الاختبارات'

  def __str__(self):
    return f'{self.student.username} - {self.quiz.title}'


class QuizAnswer(models.Model):
  attempt = models.ForeignKey(
      QuizAttempt, on_delete=models.CASCADE, related_name='answers'
  )
  question = models.ForeignKey(
      Question, on_delete=models.CASCADE
  )
  choice = models.ForeignKey(
      Choice, on_delete=models.CASCADE, null=True, blank=True
  )

  class Meta:
    unique_together = ('attempt', 'question')
    verbose_name = 'إجابة اختبار'
    verbose_name_plural = 'إجابات الاختبارات'

  def __str__(self):
    return f'إجابة {self.attempt.student.username} على {self.question.text[:30]}'


class ContactMessage(models.Model):
  name = models.CharField(max_length=100, verbose_name='اسم المرسل')
  email = models.EmailField(verbose_name='البريد الإلكتروني')
  subject = models.CharField(max_length=200, verbose_name='الموضوع')
  message = models.TextField(verbose_name='محتوى الرسالة')
  created_at = models.DateTimeField(auto_now_add=True)
  is_read = models.BooleanField(default=False, verbose_name='مقروءة؟')

  class Meta:
    ordering = ['-created_at']
    verbose_name = 'رسالة تواصل'
    verbose_name_plural = 'رسائل التواصل'

  def __str__(self):
    return f'{self.name} - {self.subject}'


class Favorite(models.Model):
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites'
  )
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='favorited_by'
  )
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ('student', 'course')
    verbose_name = 'مفضلة'
    verbose_name_plural = 'المفضلات'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.student.username} - {self.course.title}'


class Notification(models.Model):
  user = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
  )
  title = models.CharField(max_length=200, verbose_name='عنوان الإشعار')
  message = models.TextField(verbose_name='محتوى الإشعار')
  is_read = models.BooleanField(default=False, verbose_name='مقروء؟')
  created_at = models.DateTimeField(auto_now_add=True)
  link = models.CharField(
      max_length=200, blank=True, null=True,
      verbose_name='رابط الانتقال (اختياري)'
  )

  class Meta:
    ordering = ['-created_at']
    verbose_name = 'إشعار'
    verbose_name_plural = 'إشعارات'

  def __str__(self):
    return f'{self.user.username} - {self.title}'


class CourseQuestion(models.Model):
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='course_questions'
  )
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_questions'
  )
  title = models.CharField(max_length=200, verbose_name='عنوان السؤال')
  content = models.TextField(verbose_name='محتوى السؤال')
  created_at = models.DateTimeField(auto_now_add=True)
  is_resolved = models.BooleanField(default=False, verbose_name='تم الإجابة؟')

  class Meta:
    ordering = ['-created_at']
    verbose_name = 'سؤال'
    verbose_name_plural = 'أسئلة الكורס'

  def __str__(self):
    return self.title


class CourseAnswer(models.Model):
  question = models.ForeignKey(
      CourseQuestion, on_delete=models.CASCADE, related_name='answers'
  )
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_answers'
  )
  content = models.TextField(verbose_name='محتوى الإجابة')
  created_at = models.DateTimeField(auto_now_add=True)
  is_accepted = models.BooleanField(default=False, verbose_name='إجابة مقبولة؟')

  class Meta:
    ordering = ['-is_accepted', 'created_at']
    verbose_name = 'إجابة'
    verbose_name_plural = 'الإجابات'

  def __str__(self):
    return self.content[:60]


class Coupon(models.Model):
  code = models.CharField(max_length=20, unique=True, verbose_name='كود الخصم')
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='coupons',
      help_text='الكورس الذي يطبق عليه الخصم (اترك فارغاً ليطبق على كل الكورسات)',
      null=True, blank=True
  )
  discount_type = models.CharField(
      max_length=10,
      choices=[('percentage', 'نسبة مئوية'), ('fixed', 'مبلغ ثابت')],
      default='percentage',
      verbose_name='نوع الخصم'
  )
  discount_value = models.DecimalField(
      max_digits=8, decimal_places=2,
      help_text='إذا كانت نسبة مئوية اكتب الرقم (مثل 20 لـ 20%). إذا كان مبلغ ثابت اكتب القيمة بالجنيه.',
      verbose_name='قيمة الخصم'
  )
  usage_limit = models.PositiveIntegerField(
      default=1, verbose_name='عدد مرات الاستخدام المسموح'
  )
  used_count = models.PositiveIntegerField(default=0, verbose_name='عدد مرات الاستخدام')
  expires_at = models.DateTimeField(
      blank=True, null=True, verbose_name='تاريخ انتهاء الصلاحية'
  )
  is_active = models.BooleanField(default=True, verbose_name='نشط؟')
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']
    verbose_name = 'كوبون خصم'
    verbose_name_plural = 'كوبونات الخصم'

  def __str__(self):
    return self.code

  def is_valid(self):
    from django.utils import timezone
    if not self.is_active:
      return False
    if self.expires_at and timezone.now() > self.expires_at:
      return False
    if self.used_count >= self.usage_limit:
      return False
    return True

  def calculate_discount(self, amount):
    if self.discount_type == 'percentage':
      return amount * (self.discount_value / 100)
    return self.discount_value


class CourseBundle(models.Model):
  title = models.CharField(max_length=200, verbose_name='عنوان الباقة')
  description = models.TextField(verbose_name='وصف الباقة')
  courses = models.ManyToManyField(
      Course, related_name='bundles', verbose_name='الكורסات في الباقة'
  )
  price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name='سعر الباقة')
  is_active = models.BooleanField(default=True, verbose_name='نشطة؟')
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']
    verbose_name = 'باقة كورسات'
    verbose_name_plural = 'باقات الكورسات'

  def __str__(self):
    return self.title

  def total_individual_price(self):
    return sum(c.price for c in self.courses.all())

  def savings(self):
    return self.total_individual_price() - self.price


class BundlePurchase(models.Model):
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bundle_purchases'
  )
  bundle = models.ForeignKey(
      CourseBundle, on_delete=models.CASCADE, related_name='purchases'
  )
  amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
  purchased_at = models.DateTimeField(auto_now_add=True)
  status = models.CharField(
      max_length=30,
      choices=[
          ('pending', 'قيد الانتظار'),
          ('completed', 'مكتمل'),
          ('failed', 'فشل'),
      ],
      default='pending',
  )

  class Meta:
    ordering = ['-purchased_at']
    verbose_name = 'شراء باقة'
    verbose_name_plural = 'عمليات شراء الباقات'

  def __str__(self):
    return f'{self.student.username} - {self.bundle.title}'


class LessonComment(models.Model):
  lesson = models.ForeignKey(
      Lesson, on_delete=models.CASCADE, related_name='comments'
  )
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_comments'
  )
  content = models.TextField(verbose_name='محتوى التعليق')
  created_at = models.DateTimeField(auto_now_add=True)
  is_approved = models.BooleanField(default=True, verbose_name='موافق عليه؟')

  class Meta:
    ordering = ['-created_at']
    verbose_name = 'تعليق درس'
    verbose_name_plural = 'تعليقات الدروس'

  def __str__(self):
    return f'{self.student.username} - {self.lesson.title}'


class InstructorRating(models.Model):
  instructor = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='instructor_ratings'
  )
  student = models.ForeignKey(
      settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_instructor_ratings'
  )
  course = models.ForeignKey(
      Course, on_delete=models.CASCADE, related_name='instructor_ratings'
  )
  rating = models.PositiveIntegerField(
      default=5, choices=[(i, str(i)) for i in range(1, 6)],
      verbose_name='التقييم (نجوم)'
  )
  comment = models.TextField(blank=True, null=True, verbose_name='تعليق اختياري')
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ('student', 'course')
    ordering = ['-created_at']
    verbose_name = 'تقييم مدرس'
    verbose_name_plural = 'تقييمات المدرسين'

  def __str__(self):
    return f'{self.student.username} قيم {self.instructor.username} بـ {self.rating} نجوم'