from django.urls import path, include
from rest_framework.routers import DefaultRouter

from appmodule import views


router = DefaultRouter()
router.register('appmodules', views.AppModuleViewSet)

app_name = 'appmodule'

urlpatterns = [
    path('', include(router.urls))
]
