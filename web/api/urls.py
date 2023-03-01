from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from . import views

app_name = 'api'

urlpatterns = [
    path('auth/', obtain_auth_token, name='authorization'),
]