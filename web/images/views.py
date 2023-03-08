import os
from io import BytesIO
import datetime

from PIL import Image
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from rest_framework import generics, permissions, authentication, status
from rest_framework.response import Response

from .models import UploadedImage
from .serializers import WithImageSerializer, WithoutImageSerializer
from .services.tools import (
    create_thumbnail_data,
    create_binary_image_data,
    create_thumbnail_urls,
    crete_expiring_link
)
from .services.validators import match_content_type_and_save_format, validate_height, validate_expiration_seconds
from .services.custom_exceptions import InvalidExpirationRange, InvalidExpirationSeconds
from api.authentication import TokenAuthentication
from api.permissions import CanAccessBinaryImage

@login_required
@validate_height
def thumbnail_view(request, pk, height, name):
    """
    A view that returns a thumbnail of an image.

    Args:
        request (HttpRequest): The request object.
        pk (int): The primary key of the UploadedImage instance.
        height (int): The height of the thumbnail.
        name (str): The name of the original image file.

    Returns:
        HttpResponse: The response containing the thumbnail image.
    """

    image = get_object_or_404(UploadedImage, pk=pk, user=request.user)
    if not os.path.exists(image.image_url.path):
        raise Http404
    cache_key = f"thumbnail_{pk}_{height}"
    thumbnail_data = cache.get(cache_key)
    if thumbnail_data is None:
        thumbnail_data = create_thumbnail_data(image.image_url.path, height)
        cache.set(cache_key, thumbnail_data)
    thumbnail = Image.open(BytesIO(thumbnail_data))
    try:
        content_type, save_format = match_content_type_and_save_format(image.image_url.name.split('.')[-1].upper())
    except ValueError as err:
        return HttpResponse(err, status=400)
    response = HttpResponse(content_type=content_type)
    thumbnail.save(response, save_format)
    return response

@login_required
@cache_control(max_age=30000)
def binary_image_view(request, pk, encoded_expiration_time, name):
    """
    A view that returns a binary version of an image.

    Args:
        request (HttpRequest): The request object.
        pk (int): The primary key of the UploadedImage instance.
        expiration_time_str (str): The expiration time of the signed URL in string format.
        name (str): The name of the original image file.

    Returns:
        HttpResponse: The response containing the binary image.
    """

    try:
        expiration_time_str = force_str(urlsafe_base64_decode(encoded_expiration_time))
        expiration_time = datetime.datetime.strptime(expiration_time_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return HttpResponse(f'Invalid date!', status=400)
    if datetime.datetime.now() > expiration_time:
        return HttpResponseForbidden("The signed URL has expired.")
    image = get_object_or_404(UploadedImage, pk=pk, user=request.user)
    if not os.path.exists(image.image_url.path):
        raise Http404
    binary_image_data = create_binary_image_data(image.image_url.path)
    binary_image = Image.open(BytesIO(binary_image_data))
    content_type, save_format = match_content_type_and_save_format(image.image_url.name.split('.')[-1].upper())
    response = HttpResponse(content_type=content_type)
    binary_image.save(response, save_format)
    return response

class ImageListCreteAPIView(generics.ListCreateAPIView):
    """
    API View that allows authenticated users to upload images and list
    images uploaded before
    """

    authentication_classes = [
        authentication.SessionAuthentication,
        TokenAuthentication
    ]
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_queryset(self):
        return UploadedImage.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if not self.request.user.tier.original_image:
            return WithoutImageSerializer
        return WithImageSerializer

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        thumbnail_sizes = self.request.user.tier.thumbnail_sizes
        thumbnails_urls = create_thumbnail_urls(self.request, instance, thumbnail_sizes)
        instance.thumbnails_urls = thumbnails_urls
        instance.save()

class ImageDetailAPIView(generics.RetrieveAPIView):
    """
    API View that allows authenticated users to access details
    of a single uploaded image
    """

    authentication_classes = [
        authentication.SessionAuthentication,
        TokenAuthentication
    ]
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_queryset(self):
        return UploadedImage.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if not self.request.user.tier.original_image:
            return WithoutImageSerializer
        return WithImageSerializer

class FetchLinkToBinaryImageAPIView(generics.RetrieveAPIView):
    """
    API View that allows users with CanAccessBinaryImage permission
    to fetch link to binary image that expires after a number
    of seconds (user can specify any number between 300 and 30000)
    """

    authentication_classes = [
        authentication.SessionAuthentication,
        TokenAuthentication
    ]
    permission_classes = [
        permissions.IsAuthenticated,
        CanAccessBinaryImage
    ]

    def get_queryset(self):
        return UploadedImage.objects.filter(user=self.request.user)

    def get(self, request, pk, *args, **kwargs):
        """
        Retrieve the signed URL to access the binary image.

        Parameters:
            request (HttpRequest): The request object.
            pk (int): The primary key of the uploaded image.
            expiration_seconds (int): The number of seconds until the signed URL expires.

        Returns:
            HttpResponse: The signed URL to access the binary image.
        """

        uploaded_image = get_object_or_404(UploadedImage, pk=pk, user=request.user)
        if not os.path.exists(uploaded_image.image_url.path):
            raise Http404
        try:
            expiration_seconds = validate_expiration_seconds(request.GET.get('expiration_seconds', 3600))
            binary_image_url = crete_expiring_link(self.request, pk, uploaded_image, expiration_seconds)
        except InvalidExpirationSeconds as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except InvalidExpirationRange as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'url': binary_image_url, 'expiration_seconds': expiration_seconds}, status=status.HTTP_200_OK)
