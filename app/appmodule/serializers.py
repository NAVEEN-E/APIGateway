from rest_framework import serializers

from core.models import AppModule


class AppModuleSerializer(serializers.ModelSerializer):
    """Serializer for appmodule object"""

    class Meta:
        model = AppModule
        fields = ('id', 'name', 'dashboard_url', 'login_url', 'user')
        read_only_Fields = ('id',)
