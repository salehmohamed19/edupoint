import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Course(models.Model):
  title = models.CharField(max_length=200)
  description = models.TextField()
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