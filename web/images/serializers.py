from rest_framework import serializers
from .models import UploadedImage, validate_image

class WithoutImageSerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(write_only=True,validators=[validate_image])
    class Meta:
        model = UploadedImage
        fields = ['id', 'thumbnails_urls','image_url']
        read_only_fields = ['id', 'thumbnails_urls']

class WithImageSerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(validators=[validate_image])
    class Meta:
        model = UploadedImage
        fields = ['id', 'thumbnails_urls','image_url']
        read_only_fields = ['id', 'thumbnails_urls']
