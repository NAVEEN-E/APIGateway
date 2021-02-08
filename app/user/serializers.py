from django.contrib.auth import (
    get_user_model,
    authenticate
)
from django.contrib.auth.hashers import check_password
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from core.models import User
from core.utils.email import itt_send_mail


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'email',
            'password',
            'name',
            'address',
            'contact',
            'picture',
            )
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5}}

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class AuthTokenSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )
        if not user:
            msg = _('Unable to authenticate with provided credentials')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return attrs


class AuthOTPTokenSerializer(serializers.Serializer):
    email = serializers.CharField()
    otp = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        # print(f"\n\n===email==== {email}=========\n\n")
        # print(f"\n\n====password===={password}========\n\n")
        user = User.objects.filter(
                email=email,
        )
        # password = [p.password for p in user]
        # print(f"\n\n=======\n\n")
        # print([p.password for p in user])
        # print(f"\n\n====user===={user}========\n\n")
        # print(f"\n\n====user===={user.password}========\n\n")
        # otp = "4321"
        # itt_send_mail(None, email, otp)

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )
        if not user:
            msg = _('Unable to authenticate with provided credentials')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return attrs
