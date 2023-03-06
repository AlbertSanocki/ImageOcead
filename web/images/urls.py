from django.urls import path
from . import views

app_name = 'images'

urlpatterns = [
    path('', views.ImageListCreteAPIView.as_view(), name='list_create_image'),
    path('<int:pk>/', views.ImageDetailAPIView.as_view(), name='image_details'),
    path('<int:pk>/binary/', views.FetchLinkToBinaryImageAPIView.as_view(), name='binary_link'),
    path('<int:pk>/thumbnail_view/<int:height>/<str:name>', views.thumbnail_view,\
        name='thumbnail_view'),
    path('<int:pk>/binary_image_view/<str:name>/<str:encoded_expiration_time>', \
        views.binary_image_view, name='binary_image_view')
]