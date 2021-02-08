import json
from django.conf import settings
from django.http import JsonResponse
from django.urls import resolve
from django.utils import timezone
from django.utils.cache import patch_cache_control
from rest_framework import (
    serializers,
    status,
)
from rest_framework.relations import (
    MANY_RELATION_KWARGS,
    ManyRelatedField,
)
from rest_framework_serializer_field_permissions.fields import PermissionMixin


class PatchCacheControlHeaderOnGetMixin:
    def dispatch(self, request, *args, **kwargs):
        # If cache-control is disable then default.
        if not settings.PATCH_CACHE_CONTROL_HEADER:
            return super().dispatch(request, *args, **kwargs)

        # If not GET, then default.
        if not request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)

        response = super().dispatch(request, *args, **kwargs)

        if response.status_code not in settings.CACHE_RESPONSE_CODES:
            return response

        # Use cache_till from views if specified, else use settings.
        cache_till = getattr(self, "cache_till", settings.CACHE_TILL)
        patch_cache_control(response, max_age=cache_till)

        return response


class RelatedFieldPermissionMixin(PermissionMixin):
    """
    Adds the ability to permission on fields of type RelatedField.

    This is based off of an outstanding feature request here
    https://github.com/InterSIS/django-rest-serializer-field-permissions/issues/24.
    If/when this makes its way into django-rest-serializer-field-permissions,
    this custom mixin can then be dropped.
    """

    class PermissionManyRelatedField(ManyRelatedField):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.permission_classes = self.child_relation.permission_classes
            self.check_permission = self.child_relation.check_permission

    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return RelatedFieldPermissionMixin.PermissionManyRelatedField(**list_kwargs)


class SingleObjectOnPostMixin:
    restrict_bulk_creation = False

    def dispatch(self, request, *args, **kwargs):
        # 1. If not POST, then default.
        if not request.method == 'POST':
            return super().dispatch(request, *args, **kwargs)

        try:
            request_data = json.loads(request.body.decode(
                settings.DEFAULT_CHARSET
            ))
        except json.JSONDecodeError:
            return super().dispatch(request, *args, **kwargs)

        is_dict = isinstance(request_data, dict)

        # 2. If not POST on single object (aka list), then default.
        if not is_dict:
            # Set flag here depending on request payload size
            # as bulk creation restricted to superusers only
            self.restrict_bulk_creation = True
            return super().dispatch(request, *args, **kwargs)

        # Tweak 'request.body' as a single object list. Note that
        # 'request._body' is updated directly to bypass Django's check
        # to not modify 'request.body' once read. This check was
        # originally introduced to prevent the potentially unnecessary
        # expensive parsing of the 'body' in case the view happens to
        # not use that data - https://code.djangoproject.com/ticket/613.
        # In this case, by this point, it is pretty much guaranteed that
        # the 'data' will need to be POSTed and parsed, so override.
        request_data = [request_data]
        request_data = json.dumps(request_data).encode(
            settings.DEFAULT_CHARSET
        )
        request._body = request_data

        response = super().dispatch(request, *args, **kwargs)

        # 3. If no success on single object POST, then pass-through
        # error response.
        if not response.status_code == status.HTTP_200_OK:
            return response

        url_resolver = resolve(request.path.rstrip('/'))

        # 4. Handle the rest.
        response_data = json.loads(response.content.decode(
            settings.DEFAULT_CHARSET
        ))[0]
        url_namespace = url_resolver.namespaces[1]

        # For AppModule and Users, use id as identifier, else name.
        if (
            url_namespace == 'itt-appmodule' or
            url_namespace == 'itt-user'
        ):
            resource_identifier = response_data['id']
        else:
            resource_identifier = response_data['name']

        response = JsonResponse(
            response_data,
            status=status.HTTP_201_CREATED,
        )
        response['Location'] = "/{}".format(resource_identifier)

        return response
