# settings.py

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url 
# WhiteNoise does not need to be imported here but must be installed and referenced below.

# Load environment variables (useful for local development only)
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# --- CORE PRODUCTION SETTINGS ---

# SECURITY
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-change-this-in-production')

# DEBUG: Set to 'False' in Render environment variables for security.
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS: Must dynamically accept the Render domain.
# Render automatically sets the RENDER_EXTERNAL_HOSTNAME environment variable.
if os.environ.get('RENDER'):
    # In production on Render, pull the hostname automatically
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    ALLOWED_HOSTS = [
        RENDER_EXTERNAL_HOSTNAME,
        # Add your custom domains here if you use them
        # 'www.my-flowerbelle.com',
    ]
else:
    # Local development hosts
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Automatically append slashes to URLs (important to prevent 404s)
APPEND_SLASH = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Project apps
    'accounts',
    'inventory',
    'pos',
    'reports',
    'forecasting',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # --- PRODUCTION FIX: Add WhiteNoise middleware after SecurityMiddleware ---
    # This middleware is essential for serving static files on Render.
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'flowerbelle_backend.urls'

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

WSGI_APPLICATION = 'flowerbelle_backend.wsgi.application'

# --- PRODUCTION FIX: Database Configuration for Render ---
# Render provides the database connection details via the single DATABASE_URL environment variable.
DATABASES = {
    'default': dj_database_url.config(
        # Use the DATABASE_URL environment variable if present (production)
        default=os.environ.get('DATABASE_URL'),
        # Fallback to a development setting if DATABASE_URL is not set (local dev)
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- Standard Django Settings (Unchanged) ---
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# --- PRODUCTION FIX: Static Files for WhiteNoise ---
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # Location where 'collectstatic' will place files

# Media files (User-uploaded content - highly recommend using AWS S3 or similar in production)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User model
AUTH_USER_MODEL = 'accounts.User'

# --- CORS Settings ---
# CORS_ALLOWED_ORIGINS: Must include your React frontend's Render URL in production.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # --- PRODUCTION FIX: Add the expected Render URL for your React Frontend ---
    # Replace 'my-react-app' with the actual name of your Static Site service on Render.
    f"https://my-react-app.onrender.com", 
    # Add your custom domain if applicable
    # "https://www.my-flowerbelle.com",
]

# Include the RENDER_EXTERNAL_HOSTNAME for Django to accept CORS requests from itself
if RENDER_EXTERNAL_HOSTNAME:
    CORS_ALLOWED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")


CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt',
    'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]

CORS_EXPOSE_HEADERS = ['Content-Disposition', 'Content-Type']

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Ensure your JWT backend is here
        'rest_framework_simplejwt.authentication.JWTAuthentication', 
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    # Use the actual SECRET_KEY variable for signing and validation
    'SIGNING_KEY': SECRET_KEY, 
    'AUTH_HEADER_TYPES': ('Bearer',), 
}