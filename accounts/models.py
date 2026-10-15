from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
  USER_TYPE_CHOICES = (
      ('student', 'طالب'),
      ('instructor', 'مدرس'),
  )
  user = models.OneToOneField(User, on_delete=models.CASCADE)
  user_type = models.CharField(
      max_length=20, choices=USER_TYPE_CHOICES, default='student'
  )
  full_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="الاسم الكامل للشهادات")
  phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم الهاتف")
  bio = models.TextField(blank=True, null=True)

  def __str__(self):
    return f'{self.user.username} - {self.get_user_type_display()}'


# إشارة لضمان إنشاء UserProfile افتراضياً لأي مستخدم جديد
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
  if created:
    default_name = instance.get_full_name() or instance.username
    UserProfile.objects.get_or_create(
        user=instance, defaults={'user_type': 'student', 'full_name': default_name}
    )


# إشارة آمنة تلتقط بيانات جوجل وتحدث الاسم الكامل في الـ UserProfile
@receiver(post_save, sender=SocialAccount)
def update_profile_from_google(sender, instance, created, **kwargs):
  if instance.provider == 'google':
    user = instance.user
    full_name = instance.extra_data.get('name')
    email = instance.extra_data.get('email')

    if email and not user.email:
      user.email = email
      user.save()

    if full_name:
      profile, _ = UserProfile.objects.get_or_create(user=user)
      if not profile.full_name or profile.full_name == user.username:
        profile.full_name = full_name
        profile.save()