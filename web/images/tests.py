import os
import datetime
from io import BytesIO
from django.http import Http404
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from PIL import Image
import tempfile
from .services.tools import (
    create_thumbnail_data,
    create_binary_image_data,
    create_thumbnail_urls,
    crete_expiring_link
)
from .services.validators import (match_content_type_and_save_format, validate_expiration_seconds)
from .models import AppUser, UserTier, UploadedImage
from .serializers import WithoutImageSerializer, WithImageSerializer
from .services.custom_exceptions import InvalidExpirationRange, InvalidExpirationSeconds

os.environ.setdefault("DB_NAME", "test_db_name")
os.environ.setdefault("DB_USER", "test_db_user")
os.environ.setdefault("DB_PASSWORD", "test_db_password")
os.environ.setdefault("DB_HOST", "test_db_host")
os.environ.setdefault("SECRET_KEY", "test_secret_key")
os.environ.setdefault("ALLOWED_HOSTS", "test_allowed_hosts")
os.environ.setdefault("DEBUG", "1")

class BaseTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        test_image = Image.new('RGB', (100, 100), color='red')
        tier = UserTier.objects.create(name='Basic', thumbnail_sizes=[50, 100, 200])
        self.user = AppUser.objects.create(username='testuser', password = 'testpass', tier=tier)
        self.file_name = 'test_image.jpg'
        file_content = BytesIO()
        test_image.save(file_content, 'JPEG')
        file_content.seek(0)
        self.media_file = default_storage.save(
            'test_images/' + self.file_name,
            SimpleUploadedFile(name=self.file_name, content=file_content.read())
        )
        self.image = UploadedImage.objects.create(user=self.user, image_url=self.media_file)

    def tearDown(self):
        UploadedImage.objects.all().delete()
        UserTier.objects.all().delete()
        AppUser.objects.all().delete()
        default_storage.delete(self.media_file)

class CreateThumbnailTestCase(APITestCase):

    def setUp(self):
        self.image = Image.new('RGB', (100, 100), color='red')
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        self.image.save(self.temp_file.name, format='JPEG')

    def test_positive_create_thumbnail(self):
        thumb_data = create_thumbnail_data(self.temp_file.name, 50)
        thumb_image = Image.open(BytesIO(thumb_data))
        self.assertEqual(thumb_image.height, 50)

    def test_create_thumbnail_with_nonexistent_file(self):
        with self.assertRaises(Http404):
            create_thumbnail_data('nonexistent.jpg', 50)
        print()

    def tearDown(self):
        try:
            os.unlink(self.temp_file.name)
        except OSError:
            pass

class CreateBinaryImageTestCase(APITestCase):

    def setUp(self):
        self.image = Image.new('RGB', (100, 100), color='red')
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        self.image.save(self.temp_file.name, format='JPEG')

    def test_positive_create_binary_image_data(self):
        binary_image_data = create_binary_image_data(self.temp_file.name)
        binary_image = Image.open(BytesIO(binary_image_data))
        self.assertEqual(binary_image.mode,'L')

        expected_image = Image.open(self.temp_file.name)
        expected_binary_image = expected_image.convert('L')
        expected_binary_io = BytesIO()
        expected_binary_image.save(expected_binary_io, expected_image.format.upper())
        expected_binary_image_data = expected_binary_io.getvalue()
        expected_binary_io.close()
        self.assertEqual(binary_image_data, expected_binary_image_data)

    def test_create_binary_image_data_with_nonexistent_file(self):
        with self.assertRaises(Http404):
            create_binary_image_data('nonexistent.jpg')

    def tearDown(self):
        try:
            os.unlink(self.temp_file.name)
        except OSError:
            pass

class CreateThumbnailUrlsTestCase(BaseTestCase):

    def test_positive_create_thumbnail_urls(self):
        self.client.force_login(self.user)
        request = self.client.get('/').wsgi_request
        instance = self.image
        thumbnail_sizes = self.user.tier.thumbnail_sizes
        thumbnails_urls = create_thumbnail_urls(request, instance, thumbnail_sizes)
        self.assertEqual(len(thumbnails_urls), 3)
        self.assertEqual(thumbnails_urls[0], {'50px': f'http://testserver/api/images/{self.image.pk}/thumbnail_view/50/test_image.jpg'})
        self.assertEqual(thumbnails_urls[1], {'100px': f'http://testserver/api/images/{self.image.pk}/thumbnail_view/100/test_image.jpg'})
        self.assertEqual(thumbnails_urls[2], {'200px': f'http://testserver/api/images/{self.image.pk}/thumbnail_view/200/test_image.jpg'})

class CreateExpiringLinkTestCase(BaseTestCase):

    def test_positive_create_expiring_link(self):
        self.client.force_login(self.user)
        request = self.client.get('/').wsgi_request
        pk = self.image.pk
        self.user.tier.expiring_links = True
        self.user.tier.save()
        expiration_seconds = 300
        expiring_link = crete_expiring_link(request, pk, self.image, expiration_seconds)
        expiration_time_str = force_str(urlsafe_base64_decode(expiring_link.split('/')[-1]))
        expected_expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=expiration_seconds)
        expected_expiration_time_str = expected_expiration_time.strftime('%Y-%m-%dT%H:%M:%S')
        self.assertEqual(expiration_time_str,expected_expiration_time_str)

class MatchContentTypeAndSaveFormatTestCase(APITestCase):

    def test_positive_match(self):
        content_type, save_format = match_content_type_and_save_format('PNG')
        self.assertEqual(content_type, 'image/png')
        self.assertEqual(save_format, 'PNG')

        content_type, save_format = match_content_type_and_save_format('JPG')
        self.assertEqual(content_type, 'image/jpeg')
        self.assertEqual(save_format, 'JPEG')

    def test_unsupported_format(self):
        with self.assertRaises(ValueError) as ve:
            match_content_type_and_save_format('BMP')
        self.assertEqual(str(ve.exception), 'Unsupported image format')

class ThumbnailHeightValidatorTestCase(BaseTestCase):

    def test_positive_valid_height(self):
        self.client.force_login(self.user)
        valid_height = 200
        url = reverse('images:thumbnail_view', kwargs={'pk': self.image.pk, 'height': valid_height, 'name': os.path.basename(self.image.image_url.path)},)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_negative_valid_height_based_on_account_tier(self):
        self.client.force_login(self.user)
        invalid_height = 60
        url = reverse('images:thumbnail_view', kwargs={'pk': self.image.pk, 'height': invalid_height, 'name': os.path.basename(self.image.image_url.path)},)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode('utf-8'), 'Your account tier does not allow You to create thumbail of this height')

    def test_negative_valid_height_outside_the_range(self):
        self.client.force_login(self.user)
        invalid_height = 10^999
        url = reverse('images:thumbnail_view', kwargs={'pk': self.image.pk, 'height': invalid_height, 'name': os.path.basename(self.image.image_url.path)},)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode('utf-8'), 'Height should be between 1 and 1000.')

class ExpirationSecondsParamValidatorTestCase(APITestCase):
    
    def test_positive_validate_expiration_seconds(self):
        valid_expiration_seconds = 500
        expiration_seconds = validate_expiration_seconds(valid_expiration_seconds)
        self.assertEqual(expiration_seconds, valid_expiration_seconds)

    def test_negative_validate_expiration_seconds(self):
        invalid_expiration_seconds = 40000
        with self.assertRaises(InvalidExpirationRange) as ve:
            validate_expiration_seconds(invalid_expiration_seconds)
        self.assertEqual(str(ve.exception), 'expiration_seconds must be between 300 and 30000 seconds')

    def test_negative_validate_expiration_seconds(self):
        invalid_expiration_seconds = 'text'
        with self.assertRaises(InvalidExpirationSeconds) as ve:
            validate_expiration_seconds(invalid_expiration_seconds)
        self.assertEqual(str(ve.exception), 'expiration_seconds must be an integer')

class ThumbnailViewTestCase(BaseTestCase):

    def test_positive_thumbnail_view(self):
        self.client.force_login(self.user)
        height = self.user.tier.thumbnail_sizes.pop()
        url = reverse('images:thumbnail_view', kwargs={'pk': self.image.pk, 'height': height, 'name': os.path.basename(self.image.image_url.path)},)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_no_auth__thumbnail_view(self):
        height = self.user.tier.thumbnail_sizes.pop()
        url = reverse('images:thumbnail_view', kwargs={'pk': self.image.pk, 'height': height, 'name': os.path.basename(self.image.image_url.path)},)
        response = self.client.post(url)
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/api/images/{self.image.pk}/thumbnail_view/200/test_image.jpg',
            status_code=302,
            target_status_code=200
        )

class BinaryImageViewTestCase(BaseTestCase):

    def test_positive_binary_image_view(self):
        self.client.force_login(self.user)
        self.user.tier.expiring_links = True
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=24)
        encoded_expiration_time = urlsafe_base64_encode(force_bytes(expiration_time.strftime('%Y-%m-%dT%H:%M:%S')))
        kwargs = {
            'pk': self.image.pk,
            'encoded_expiration_time': encoded_expiration_time,
            'name': os.path.basename(self.image.image_url.path)
        }
        url = reverse('images:binary_image_view', kwargs=kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertIsNotNone(response.content)

    def test_no_auth_binary_image_view(self):
        self.user.tier.expiring_links = True
        expiration_time = datetime.datetime.now() + datetime.timedelta(hours=24)
        encoded_expiration_time = urlsafe_base64_encode(force_bytes(expiration_time.strftime('%Y-%m-%dT%H:%M:%S')))
        kwargs = {
            'pk': self.image.pk,
            'encoded_expiration_time': encoded_expiration_time,
            'name': os.path.basename(self.image.image_url.path)
        }
        url = reverse('images:binary_image_view', kwargs=kwargs)
        response = self.client.get(url)
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/api/images/{self.image.pk}/binary_image_view/test_image.jpg/{encoded_expiration_time}',
            status_code=302,
            target_status_code=200
        )

class ImageListCreteAPIViewTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        test_image = Image.new('RGB', (100, 100), color='red')
        tier = UserTier.objects.create(name='Basic', thumbnail_sizes=[50, 100, 200])
        self.user = AppUser.objects.create(username='testuser', password = 'testpass', tier=tier)
        file_name = 'test_image.jpg'
        file_content = BytesIO()
        test_image.save(file_content, 'JPEG')
        file_content.seek(0)
        self.media_file = SimpleUploadedFile(file_name, file_content.read())
        self.token = Token.objects.create(user=self.user)
        self.auth_header = {'Authorization': f'Bearer {self.token.key}'}

    def test_without_image_list_create_api_view(self):
        # Test without original_image tier
        without_image_serializer = WithoutImageSerializer([])
        self.user.tier.original_image = False
        self.user.tier.save()
        url = reverse('images:list_create_image')
        # test get request
        response = self.client.get(url, HTTP_AUTHORIZATION=self.auth_header['Authorization'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
        self.assertEqual(
            response.renderer_context['view'].get_serializer_class().__name__,
            without_image_serializer.__class__.__name__
        )
        # test post requests
        response = self.client.post(url, {'image_url': self.media_file}, HTTP_AUTHORIZATION=self.auth_header['Authorization'], format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UploadedImage.objects.filter(user=self.user).count(), 1)
        uploaded_image = UploadedImage.objects.get(user=self.user)
        self.assertEqual(response.data['id'], uploaded_image.id)
        self.assertEqual(len(response.data['thumbnails_urls']), 3)
        self.assertEqual(
            response.renderer_context['view'].get_serializer_class().__name__,
            without_image_serializer.__class__.__name__
        )

    def test_with_image_list_create_api_view(self):
        # Test with original_image tier
        with_image_serializer = WithImageSerializer([])
        self.user.tier.original_image = True
        self.user.tier.save()
        url = reverse('images:list_create_image')
        # test post requests
        response = self.client.post(url, {'image_url': self.media_file}, HTTP_AUTHORIZATION=self.auth_header['Authorization'], format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UploadedImage.objects.filter(user=self.user).count(), 1)
        uploaded_image = UploadedImage.objects.get(user=self.user)
        self.assertEqual(response.data['id'], uploaded_image.id)
        self.assertEqual(len(response.data['thumbnails_urls']), 3)
        self.assertIn('image_url',response.data)
        self.assertEqual(
            response.renderer_context['view'].get_serializer_class().__name__,
            with_image_serializer.__class__.__name__
        )

    def test_no_auth_list_create_api_view(self):
        url = reverse('images:list_create_image')
        # test post requests
        response = self.client.post(url, {'image_url': self.media_file})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual('Authentication credentials were not provided.',\
                        response.data.get('detail'))

    def tearDown(self):
        UploadedImage.objects.all().delete()
        UserTier.objects.all().delete()
        AppUser.objects.all().delete()

class FetchLinkToBinaryImageAPIViewTestCase(BaseTestCase):

    def test_positive_fetching_link_to_binary_image(self):
        self.client.force_login(self.user)
        self.user.tier.expiring_links = True
        self.user.tier.save()
        url = reverse('images:binary_link',args=[self.image.pk])
        valid_expiration_seconds = 300
        response = self.client.get(url,{'expiration_seconds': valid_expiration_seconds})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('url', response.data)
        self.assertIn('expiration_seconds', response.data)
        self.assertEqual(valid_expiration_seconds, response.data.get('expiration_seconds'))

    def test_negative_with_int_fetching_link_to_binary_image(self):
        self.client.force_login(self.user)
        self.user.tier.expiring_links = True
        self.user.tier.save()
        url = reverse('images:binary_link',args=[self.image.pk])
        valid_expiration_seconds = 200
        response = self.client.get(url,{'expiration_seconds': valid_expiration_seconds})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('expiration_seconds must be between 300 and 30000 seconds',\
                        response.data.get('error'))

    def test_negative_with_str_fetching_link_to_binary_image(self):
        self.client.force_login(self.user)
        self.user.tier.expiring_links = True
        self.user.tier.save()
        url = reverse('images:binary_link',args=[self.image.pk])
        valid_expiration_seconds = 'test'
        response = self.client.get(url,{'expiration_seconds': valid_expiration_seconds})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('expiration_seconds must be an integer',\
                        response.data.get('error'))

    def test_permission_denied_fetching_link_to_binary_image(self):
        self.client.force_login(self.user)
        self.user.tier.expiring_links = False
        self.user.tier.save()
        url = reverse('images:binary_link',args=[self.image.pk])
        valid_expiration_seconds = 300
        response = self.client.get(url,{'expiration_seconds': valid_expiration_seconds})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual('Your account tier does not allow you to fetch link to binary image. Upgrade Your account tier to Enterprice!',\
                        response.data.get('detail'))

    def test_no_auth_fetching_link_to_binary_image(self):
        url = reverse('images:binary_link',args=[self.image.pk])
        response = self.client.get(url, {'image_url': self.media_file})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual('Authentication credentials were not provided.',\
                        response.data.get('detail'))
