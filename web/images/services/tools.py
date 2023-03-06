import os
import datetime
from django.http import Http404
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from io import BytesIO
from PIL import Image
from .validators import validate_expiration_seconds

def create_thumbnail_data(image_path, height):
    """
    Create a thumbnail of an image with the specified height.

    Args:
        image_path (str): The path to the image.
        height (int): The height of the thumbnail.

    Returns:
        bytes: The bytes of the thumbnail image.
    """

    if not os.path.exists(image_path):
        raise Http404
    img = Image.open(image_path)
    if img.height != height:
        ratio = height / float(img.height)
        size = (int(img.width * ratio), height)
        img.thumbnail(size, Image.ANTIALIAS)
    thumb_io = BytesIO()
    img.save(thumb_io, img.format.upper())
    thumb_data = thumb_io.getvalue()
    thumb_io.close()
    return thumb_data

def create_binary_image_data(image_path):
    """
    Create a binary version of an image.

    Args:
        image_path (str): The path to the image.

    Returns:
        bytes: The bytes of the binary image.
    """

    if not os.path.exists(image_path):
        raise Http404
    img = Image.open(image_path)
    binary_image = img.convert('L') # JPEG, PNG does not support '1' mode
    binary_io = BytesIO()
    binary_image.save(binary_io, img.format.upper())
    binary_image_data = binary_io.getvalue()
    binary_io.close()
    return binary_image_data

def create_thumbnail_urls(request, instance, thumbnail_sizes):
    """
    Create a list of dictionaries containing URLs to image thumbnails of different sizes.

    Args:
    - request: The HTTP request object.
    - instance: An instance of the `UploadedImage` model for which the thumbnail URLs need to be created.
    - thumbnail_sizes: A list of integers representing the heights of the desired thumbnail images.

    Returns:
    - A list of dictionaries, where each dictionary contains a single key-value pair:
      - The key is a string representing the size of the thumbnail in pixels (e.g., "100px").
      - The value is a string representing the URL to the corresponding thumbnail image.
    """

    thumbnails_urls = []
    for size in thumbnail_sizes:
        thumbnail_url = reverse(
            'images:thumbnail_view',
            kwargs={
                'pk': instance.pk,
                'height': size,
                'name': os.path.basename(instance.image_url.path),
            },
        )
        thumbnail_url = request.build_absolute_uri(thumbnail_url)
        thumbnails_urls.append({f"{size}px": thumbnail_url})
    return thumbnails_urls

def crete_expiring_link(request, pk, uploaded_image, expiration_seconds):
    """
    Create a URL to an image that expires after a certain number of seconds.

    Args:
    - request: The HTTP request object.
    - pk: An integer representing the primary key of the `UploadedImage` model instance.
    - uploaded_image: An instance of the `UploadedImage` model.
    - expiration_seconds: An integer representing the number of seconds after which the URL should expire.

    Returns:
    - A string representing the URL to the binary image.
    """

    valid_expiration_seconds = validate_expiration_seconds(expiration_seconds)
    expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=valid_expiration_seconds)
    expiration_time_str = expiration_time.strftime('%Y-%m-%dT%H:%M:%S')
    encoded_expiration_time = urlsafe_base64_encode(force_bytes(expiration_time_str))
    binary_image_url = reverse(
        "images:binary_image_view",
        kwargs={
            'pk': pk,
            'name': os.path.basename(uploaded_image.image_url.path),
            'encoded_expiration_time': encoded_expiration_time,
        },
    )
    return request.build_absolute_uri(binary_image_url)
