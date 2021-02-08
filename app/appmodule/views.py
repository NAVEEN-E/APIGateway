from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import AppModule

from appmodule import serializers


class BaseAppModuleAttrViewSet(viewsets.GenericViewSet,
                               mixins.ListModelMixin,
                               mixins.CreateModelMixin):
    """Base viewset for user owned appmodule attributes"""
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Return objects for the current authenticated user only"""
        return self.queryset.filter(user=self.request.user).order_by('-name')

    def perform_create(self, serializer):
        """Create a new appmodule"""
        serializer.save(user=self.request.user)


class AppModuleViewSet(BaseAppModuleAttrViewSet):
    """Manage appmodules in the database"""
    queryset = AppModule.objects.all()
    serializer_class = serializers.AppModuleSerializer
