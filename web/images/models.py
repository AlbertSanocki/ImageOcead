from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from imageocean.settings import ALLOWED_IMAGE_EXTENSIONS

def upload_to(instance, filename):
    """Path for upload creator"""
    return 'images/{filename}'.format(filename=filename)

def validate_image(image):
    """Image validator"""
    ext = image.name.split('.')[-1]
    if not ext.lower() in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(message="Invalid file extension allowed extensions are .JPG and .PNG")

class UserTier(models.Model):
    """Model of user tier"""
    name = models.CharField(max_length=50)
    thumbnail_sizes = ArrayField(models.IntegerField(), default=list)
    original_image = models.BooleanField(default=False)
    expiring_links = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name

class AppUser(AbstractUser):
    """Model of application user"""
    tier = models.ForeignKey(UserTier, on_delete=models.CASCADE, blank=True, null=True, default=None)

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

class UploadedImage(models.Model):
    """Model of image uploaded by user"""
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    image_url = models.ImageField(upload_to=upload_to,validators=[validate_image], blank=True)
    thumbnails_urls = ArrayField(models.URLField(), default=list)

@receiver(post_save, sender=AppUser)
def set_tier(sender, instance, created, **kwargs):
    """Set tier of the newly created user"""
    if created:
        instance.tier = UserTier.objects.get(name="Basic")
        instance.save()
