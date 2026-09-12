import os
from django.core.exceptions import ValidationError


MAX_PDF_SIZE_MB = 20
MAX_IMAGE_SIZE_MB = 5


def _mb_to_bytes(mb):
    return mb * 1024 * 1024


def validate_pdf_file(value):
    """
    اعتبارسنجی فایل PDF:
    - فقط فرمت PDF
    - حداکثر 20 مگابایت
    """
    ext = os.path.splitext(value.name)[1].lower()

    if ext != '.pdf':
        raise ValidationError('فقط فایل PDF مجاز است.')

    if value.size > _mb_to_bytes(MAX_PDF_SIZE_MB):
        raise ValidationError('حجم فایل PDF نباید بیشتر از ۲۰ مگابایت باشد.')


def validate_image_file(value):
    """
    اعتبارسنجی تصویر:
    - فقط JPG / JPEG / PNG
    - حداکثر 5 مگابایت
    """
    ext = os.path.splitext(value.name)[1].lower()

    if ext not in ['.jpg', '.jpeg', '.png']:
        raise ValidationError('فقط تصاویر JPG، JPEG و PNG مجاز هستند.')

    if value.size > _mb_to_bytes(MAX_IMAGE_SIZE_MB):
        raise ValidationError('حجم تصویر نباید بیشتر از ۵ مگابایت باشد.')