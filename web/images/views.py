import os
from io import BytesIO
import datetime

from PIL import Image
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import generics, permissions, authentication, status
from rest_framework.response import Response

from .models import UploadedImage
from .serializers import WithImageSerializer, WithoutImageSerializer
from api.authentication import TokenAuthentication
from api.permissions import CanAccessBinaryImage

def create_thumbnail(image_path, height):
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

def create_binary_image(image_path):
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
    binary_image = img.convert('1')
    binary_io = BytesIO()
    binary_image.save(binary_io, img.format.upper())
    binary_image_data = binary_io.getvalue()
    binary_io.close()
    return binary_image_data

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
    
    try:
        height = int(height)
        if height < 10 or height > 1000:
            raise ValueError('Height should be between 1 and 1000.')
        if height not in request.user.tier.thumbnail_sizes:
            raise ValueError('Your account tier does not allow You to create thumbail of this height')
    except ValueError as err_msg:
        return HttpResponse(f'Invalid height! {err_msg}', status=400)

    image = get_object_or_404(UploadedImage, pk=pk, user=request.user)
    if not os.path.exists(image.image_url.path):
        raise Http404
    image_path = image.image_url.path
    thumbnail_data = create_thumbnail(image_path, height)
    thumbnail = Image.open(BytesIO(thumbnail_data))
    original_format = image.image_url.name.split('.')[-1].upper()

    match original_format:
        case 'PNG':
            content_type = "image/png"
            save_format = "PNG"
        case 'JPG' | 'JPEG':
            content_type = "image/jpeg"
            save_format = "JPEG"
        case _:
            return HttpResponse("Unsupported image format", status=400)

    response = HttpResponse(content_type=content_type)
    thumbnail.save(response, save_format)
    return response

def binary_image_view(request, pk, expiration_time_str, name):
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
        expiration_time = datetime.datetime.strptime(expiration_time_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError as err_msg:
        return HttpResponse(f'Invalid date! {err_msg}', status=400)
    if datetime.datetime.now() > expiration_time:
        return HttpResponseForbidden("The signed URL has expired.")
    image = get_object_or_404(UploadedImage, pk=pk, user=request.user)
    if not os.path.exists(image.image_url.path):
        raise Http404
    image_path = image.image_url.path
    binary_image_data = create_binary_image(image_path)
    binary_image = Image.open(BytesIO(binary_image_data))
    original_format = image.image_url.name.split('.')[-1]

    if original_format == 'png':
        content_type = "image/png"
        save_format = "PNG"
    elif original_format == 'jpg' or original_format == 'jpeg':
        content_type = "image/jpeg"
        save_format = "JPEG"
    else:
        return HttpResponse("Unsupported image format")

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
        thumbnails_urls = []
        for size in thumbnail_sizes:
            thumbnail_url = reverse(
                "images:thumbnail_view",
                kwargs={
                    "pk": instance.pk,
                    "height": size,
                    "name": os.path.basename(instance.image_url.path),
                },
            )
            thumbnail_url = self.request.build_absolute_uri(thumbnail_url)
            thumbnails_urls.append({f"{size}px": thumbnail_url})
        serializer.save(thumbnails_urls=thumbnails_urls)

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
        expiration_seconds = int(request.GET.get('expiration_seconds', 0))
        if expiration_seconds < 300 or expiration_seconds > 30000:
            return Response({'error': 'Expiration time must be between 300 and 30000 seconds'}, status=status.HTTP_400_BAD_REQUEST)
        expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=expiration_seconds)
        expiration_time_str = expiration_time.strftime('%Y-%m-%dT%H:%M:%S')
        binary_image_url = reverse(
            "images:binary_image_view",
            kwargs={
                'pk': pk,
                'expiration_time_str': expiration_time_str,
                'name': os.path.basename(uploaded_image.image_url.path),
            },
        )
        binary_image_url = self.request.build_absolute_uri(binary_image_url)
        return Response({'url': binary_image_url, 'expiration_seconds': expiration_seconds}, status=status.HTTP_200_OK)
