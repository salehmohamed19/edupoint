import uuid
from courses.models import Enrollment
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from .models import UserProfile


def register_view(request):
  if request.method == 'POST':
    email = request.POST.get('email')
    password = request.POST.get('password')
    user_type = request.POST.get('user_type', 'student')

    if User.objects.filter(email=email).exists():
      return render(
          request,
          'accounts/register.html',
          {'error': 'البريد الإلكتروني مسجل مسبقاً!'},
      )

    base_username = email.split('@')[0]
    username = base_username
    while User.objects.filter(username=username).exists():
      username = f'{base_username}_{uuid.uuid4().hex[:4]}'

    user = User.objects.create_user(
        username=username, email=email, password=password
    )
    
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.user_type = user_type
    profile.full_name = username  # اسم افتراضي مبدئي
    profile.save()

    # تحديد الـ backend صراحة لحل مشكلة تعدد الbackends عند التسجيل اليدوي
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    
    messages.success(request, f'تم إنشاء الحساب بنجاح! اسم المستخدم الخاص بك هو: {username}')
    return redirect('course_list')

  return render(request, 'accounts/register.html')


def login_view(request):
  if request.method == 'POST':
    identifier = request.POST.get('username')
    password = request.POST.get('password')

    user = authenticate(request, username=identifier, password=password)
    if user is None:
      try:
        matched_user = User.objects.get(email=identifier)
        user = authenticate(
            request, username=matched_user.username, password=password
        )
      except User.DoesNotExist:
        user = None

    if user is not None:
      login(request, user)
      messages.success(request, 'تم تسجيل الدخول بنجاح! أهلاً بك.')
      return redirect('course_list')
    else:
      return render(
          request,
          'accounts/login.html',
          {'error': 'بيانات الدخول غير صحيحة!'},
      )

  return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
  logout(request)
  messages.info(request, 'تم تسجيل الخروج بنجاح.')
  return redirect('course_list')


@login_required
def profile_view(request):
  user = request.user
  profile, _ = UserProfile.objects.get_or_create(user=user)
  enrollments = Enrollment.objects.filter(student=user)

  if request.method == 'POST':
    # معالجة تغيير كلمة المرور
    if 'old_password' in request.POST or 'new_password1' in request.POST:
      if user.has_usable_password():
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
          user = form.save()
          update_session_auth_hash(request, user)
          messages.success(request, 'تم تغيير كلمة المرور بنجاح 🔒')
          return redirect('profile')
        else:
          messages.error(request, 'يرجى التأكد من صحة بيانات كلمة المرور الحالية والجديدة.')
      else:
        new_pass = request.POST.get('new_password1')
        confirm_pass = request.POST.get('new_password2')
        if new_pass and new_pass == confirm_pass:
          user.set_password(new_pass)
          user.save()
          update_session_auth_hash(request, user)
          messages.success(request, 'تم تعيين كلمة المرور لحسابك بنجاح ✨')
          return redirect('profile')
        else:
          messages.error(request, 'كلمات المرور غير متطابقة.')

    # معالجة تحديث البيانات الشخصية (الاسم، البريد، الهاتف)
    else:
      full_name = request.POST.get('full_name', '').strip()
      phone = request.POST.get('phone', '').strip()
      email = request.POST.get('email', '').strip()

      if full_name:
        profile.full_name = full_name
      if phone:
        profile.phone = phone
      
      if email and email != user.email:
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
          messages.error(request, 'البريد الإلكتروني مستخدم من قبل حساب آخر!')
          return redirect('profile')
        user.email = email
        user.save()

      profile.save()
      messages.success(request, 'تم تحديث بيانات البروفايل والشهادات بنجاح ✅')
      return redirect('profile')

  return render(
      request,
      'accounts/profile.html',
      {
          'profile': profile,
          'enrollments': enrollments,
          'has_password': user.has_usable_password(),
      },
  )