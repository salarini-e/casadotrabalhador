import os
from pathlib import Path
from .envvars import load_envars


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

env_vars=load_envars(BASE_DIR)

db_name = env_vars['db_name']
db_user = env_vars['db_user']
db_host = env_vars['db_host']
db_passwd = env_vars['db_pw']
SECRET_KEY = env_vars['django_secret_key']
debug_mode = env_vars['debug_mode']
sqlite_mode = env_vars['sqlite_mode']
email_user = env_vars['email_sistema']
email_pass = env_vars['email_pw']


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = debug_mode

ALLOWED_HOSTS = ['localhost', '192.168.0.106', 'casadotrabalhador.pmnf.rj.gov.br', '127.0.0.1', '187.95.40.73', 'trabalhador.esalarini.com.br']

try:
    hCAPTCHA_PUBLIC_KEY = env_vars['hCAPTCHA_Public_Key']
    hCAPTCHA_PRIVATE_KEY = env_vars['hCAPTCHA_Secret_Key']
except:
    RECAPTCHA_PUBLIC_KEY = ''
    RECAPTCHA_PRIVATE_KEY = ''

# Application definition

INSTALLED_APPS = [
    'rest_framework.authtoken',
    'rest_framework',
    'widget_tweaks',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap5',
    'vagas',
    'api',
    'fontawesomefree',
    'autenticacao',
    'curriculo'

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

ROOT_URLCONF = 'balcao_de_emprego.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'balcao_de_emprego.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

if sqlite_mode:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_name + ".db",
        }
    }
else: 
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',

            'NAME': db_name,
            'PORT': '',

            'USER': db_user,
            'PASSWORD': db_passwd,
            'HOST': db_host,
        }
    }



# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ]
}
# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
# STATIC_ROOT = '/home/turismo/site/turismo/equipamentos/static'
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'settings/media')


LOGIN_URL='/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
# EMAIL_FILE_PATH = os.path.join(BASE_DIR, "sent_mail")
DEFAULT_FROM_EMAIL = 'Secretaria Municipal de Turismo e Marketing <turismo@sme.novafriburgo.rj.gov.br>'

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = email_user
EMAIL_HOST_PASSWORD = email_pass
X_FRAME_OPTIONS = 'SAMEORIGIN'

# JWT_AUTH = {
#     'JWT_ENCODE_HANDLER':
#     'rest_framework_jwt.utils.jwt_encode_handler',

#     'JWT_DECODE_HANDLER':
#     'rest_framework_jwt.utils.jwt_decode_handler',

#     'JWT_PAYLOAD_HANDLER':
#     'rest_framework_jwt.utils.jwt_payload_handler',

#     'JWT_PAYLOAD_GET_USER_ID_HANDLER':
#     'rest_framework_jwt.utils.jwt_get_user_id_from_payload_handler',

#     'JWT_RESPONSE_PAYLOAD_HANDLER':
#     'rest_framework_jwt.utils.jwt_response_payload_handler',

#     'JWT_SECRET_KEY': SECRET_KEY,
#     'JWT_GET_USER_SECRET_KEY': None,
#     'JWT_PUBLIC_KEY': None,
#     'JWT_PRIVATE_KEY': None,
#     'JWT_ALGORITHM': 'HS256',
#     'JWT_VERIFY': True,
#     'JWT_VERIFY_EXPIRATION': True,
#     'JWT_LEEWAY': 0,

#     'JWT_AUDIENCE': None,
#     'JWT_ISSUER': None,

#     'JWT_ALLOW_REFRESH': False,

#     'JWT_AUTH_HEADER_PREFIX': 'JWT',
#     'JWT_AUTH_COOKIE': None,

# }
