import os
from pathlib import Path
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api

BASE_DIR = Path(__file__).resolve().parent.parent

# قراءة الـ Secret Key والـ Debug من بيئة Render الأمنية مع الحفاظ على القيمة الافتراضية محلياً
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-here')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# السماح بالوصول من كافة النطاقات على Render
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # ترتيب تطبيقات Cloudinary الصحيح
    'cloudinary',
    'cloudinary_storage',

    # متطلبات نظام Allauth لتسجيل الدخول عبر جوجل
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # تطبيقاتنا
    'accounts',
    'courses',
    'payments',
]

SITE_ID = 1

# مصادقة الـ Backends الخاصة بـ Django و Allauth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # مرشح الملفات الثابتة الضروري لـ Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # ميدكير Allauth الضروري
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'edupoint.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'edupoint.wsgi.application'

# إعدادات قاعدة البيانات (تدعم PostgreSQL على Render وتعمل بـ SQLite محلياً)
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# إعدادات الملفات الثابتة (Static) والوسائط (Media) متوافقة مع Render و WhiteNoise
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/'
MEDIA_ROOT = BASE_DIR

# --- إعدادات Cloudinary لرفع ودفق الفيديوهات بالسحاب ---
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'u7ribala',
    'API_KEY': '249242137422639',
    'API_SECRET': 'AxkTF05o-S4afauIA1bUxL1REBw',
}

# التهيئة المباشرة لمكتبة Cloudinary لمنع خطأ Must supply api_key
cloudinary.config(
    cloud_name='u7ribala',
    api_key='249242137422639',
    api_secret='AxkTF05o-S4afauIA1bUxL1REBw',
    secure=True,
)

# تعيين Cloudinary كمُخزن افتراضي لملفات الوسائط المرفوعة
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# إعدادات إعادة التوجيه بعد تسجيل الدخول بنجاح عبر جوجل
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# تخطي صفحة التأكيد الانتقالية لتسجيل الدخول السريع عبر جوجل
SOCIALACCOUNT_LOGIN_ON_GET = True

# إعدادات Allauth الحديثة والمستقرة لمنع التعارضات وتجنب التحذيرات
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = False