from django.urls import path
from . import views

app_name = 'images'

urlpatterns = [
    path('', views.ImageListCreteAPIView.as_view()),
    path('<int:pk>/', views.ImageDetailAPIView.as_view()),
    path('<int:pk>/binary/', views.FetchLinkToBinaryImageAPIView.as_view()),
    path('<int:pk>/thumbnail_view/<int:height>/<str:name>', views.thumbnail_view,\
        name='thumbnail_view'),
    path('<int:pk>/binary_image_view/<str:expiration_time_str>/<str:name>', \
        views.binary_image_view, name='binary_image_view')
]