from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from imageocean.settings import ALLOWED_IMAGE_EXTENSIONS
from .custom_exceptions import InvalidExpirationRange, InvalidExpirationSeconds

def validate_image(image):
    """Image validator"""
    ext = image.name.split('.')[-1]
    if not ext.lower() in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(message="Invalid file extension allowed extensions are .JPG and .PNG")

def match_content_type_and_save_format(original_format):
    """
    Matches the original image format and returns the corresponding content type and save format.

    Args:
        original_format (str): The original image format.

    Returns:
        Tuple[str, str]: A tuple containing the content type and save format that corresponds to the original format.

    Raises:
        ValueError: If the original format is not supported.
    """

    match original_format:
        case 'PNG':
            content_type = 'image/png'
            save_format = 'PNG'
        case 'JPG' | 'JPEG':
            content_type = 'image/jpeg'
            save_format = 'JPEG'
        case _:
            raise ValueError('Unsupported image format')
    return content_type, save_format

def validate_height(view_func):
    """
    A decorator that validates the height parameter of a view function.

    Args:
        view_func: The view function to be decorated.

    Returns:
        The decorated view function.
    """

    def wrapper(request, pk, height, name):
        try:
            height = int(height)
            if height < 10 or height > 1000:
                raise ValueError('Height should be between 1 and 1000.')
            if height not in request.user.tier.thumbnail_sizes:
                raise ValueError('Your account tier does not allow You to create thumbail of this height')
        except ValueError as err_msg:
            return HttpResponseBadRequest(str(err_msg))
        return view_func(request, pk, height, name)
    return wrapper

def validate_expiration_seconds(expiration_seconds):
    """
    Validate the given expiration time in seconds.

    Parameters:
    - expiration_seconds (int or str): The expiration time in seconds.

    Returns:
    - int: The validated expiration time in seconds.

    Raises:
    - InvalidExpirationSeconds: If the expiration_seconds is not an integer.
    - InvalidExpirationRange: If the expiration_seconds is not within the valid range of 300-30000 seconds.
    """

    try:
        expiration_seconds = int(expiration_seconds)
    except ValueError:
        raise InvalidExpirationSeconds('expiration_seconds must be an integer')
    if expiration_seconds < 300 or expiration_seconds > 30000:
        raise InvalidExpirationRange('expiration_seconds must be between 300 and 30000 seconds')
    return expiration_seconds
