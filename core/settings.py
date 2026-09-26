"""
Django settings for core project.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# در توسعه فعلاً همین بمونه، در پروداکشن باید عوض بشه
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-only-key-change-in-production')

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # اپ‌های محلی
    'accounts.apps.AccountsConfig',
    'dashboard.apps.DashboardConfig',
    'teacher.apps.TeacherConfig',
    'student.apps.StudentConfig',
    'school.apps.SchoolConfig',
    'face.apps.FaceConfig',
    'national.apps.NationalConfig',
    'province.apps.ProvinceConfig',
    'district.apps.DistrictConfig',

    # پکیج‌های جانبی
    'django_bootstrap5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

AUTH_USER_MODEL = 'accounts.User'

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

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ═══════════════════════════════════════════════
# تنظیمات احراز هویت چهره
# ═══════════════════════════════════════════════
FACE_AI_ENABLED = True
FACE_AI_MOCK = False
FACE_MODEL_DIR = BASE_DIR / 'models'
FACE_DETECTION_MODEL = 'buffalo_l'
FACE_RECOGNITION_MODEL = 'buffalo_l'
FACE_MATCH_THRESHOLD = 0.45
FACE_MIN_REFERENCE_IMAGES = 3
FACE_MAX_REFERENCE_IMAGES = 5
FACE_MIN_FACE_SIZE = 80
FACE_MAX_BLUR_THRESHOLD = 100.0
FACE_MIN_BRIGHTNESS = 40.0
FACE_MAX_BRIGHTNESS = 220.0
FACE_LIVENESS_ENABLED = True
FACE_MIN_FRAMES_FOR_LIVENESS = 3
FACE_MATCH_AGGREGATION_METHOD = 'MAX'
FACE_MATCH_TOP_K = 2
FACE_MAX_ATTEMPTS = 3
FACE_MIN_FRAMES = 5
FACE_MAX_FRAMES = 15
FACE_MAX_FRAME_SIZE_MB = 2
STORE_FACE_DEBUG_IMAGES = False

FACE_VERIFICATION_TIMEOUT_SECONDS = 60
FACE_GUIDE_MIN_X = 0.20
FACE_GUIDE_MAX_X = 0.80
FACE_GUIDE_MIN_Y = 0.12
FACE_GUIDE_MAX_Y = 0.88
FACE_GUIDE_MIN_WIDTH = 0.22
FACE_GUIDE_MAX_WIDTH = 0.70
FACE_GUIDE_MIN_HEIGHT = 0.22
FACE_GUIDE_MAX_HEIGHT = 0.85
FACE_STABLE_DURATION_MS = 700
FACE_INFERENCE_FPS = 15
HEAD_YAW_TURN_MIN_DEG = 18
HEAD_TURN_HOLD_MS = 250
BLINK_CLOSURE_THRESHOLD = 0.55
BLINK_OPEN_THRESHOLD = 0.25
BLINK_MIN_DURATION_MS = 60
BLINK_MAX_DURATION_MS = 900
FACE_EVIDENCE_MIN_FRAMES = 5
FACE_EVIDENCE_MAX_FRAMES = 12
FACE_EVIDENCE_CAPTURE_INTERVAL_MS = 130
FACE_MEDIAPIPE_MODULE_URL = 'face/mediapipe/vision_bundle.mjs'
FACE_MEDIAPIPE_WASM_BASE = 'face/mediapipe/wasm'
FACE_MEDIAPIPE_MODEL = 'face/mediapipe/face_landmarker.task'

# ═══════════════════════════════════════════════
# تنظیمات هوش مصنوعی
# ═══════════════════════════════════════════════
AI_QUESTION_GENERATION = {
    'API_KEY': os.getenv('GAPGPT_API_KEY', ''),
    'BASE_URL': 'https://api.gapgpt.app/v1',
    'MODEL': 'gapgpt-qwen-3.6',
    'MAX_TOKENS': 4096,
    'TEMPERATURE': 0.7,
    'TOP_P': 0.9,
    'TIMEOUT': 120,
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 2,
    'MAX_QUESTIONS_PER_REQUEST': 20,
    'MIN_QUESTIONS_PER_REQUEST': 1,
    'ENABLE_TOPIC_VALIDATION': True,
    'ENABLE_JSON_VALIDATION': True,
}

AI_RATE_LIMIT = {
    'REQUESTS_PER_MINUTE': 10,
    'REQUESTS_PER_HOUR': 100,
}