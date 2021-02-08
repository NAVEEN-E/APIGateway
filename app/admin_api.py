import base64
import copy
import datetime
import json
import logging
import requests
from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django.db import (
    OperationalError,
    transaction,
)
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponse,
    JsonResponse,
)
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rolepermissions.roles import (
    assign_role,
    get_user_roles,
)
from urllib.parse import urlparse
from uuid import UUID

from admin.roles import (
    Data,
    ReadOnly,
    SystemAdmin,
    WriteOnly,
)
from app.mixins import (
    SingleObjectOnPostMixin,
)
from app.api_exception import (
    BadRequest,
    Conflict,
    ServiceUnavailable,
)

from app.utils import superuser_only
from core.utils.email import itt_send_mail
from app.core.models import (
    AppModule,
    UserAppModuleMapping,
    UserProfile,
)

logger = logging.getLogger(__name__)


# TODO: Rename the class to justify it as base class for AdminAPIView
class BaseAdminAPIView(APIView):
    def dispatch_and_handle_exception(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)

        # Handle root level exceptions here.
        except OperationalError as e:
            logger.exception("OperationalError occurred: {}".format(e))
            exception = ServiceUnavailable("This service is temporarily unavailable!")
        except Exception as e:
            logger.exception("Some error occurred{}".format(e))
            exception = APIException(e.args[0])

        return self.response_with_exception(request, exception, *args, **kwargs)

    def response_with_exception(self, request, exception, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.headers = self.default_response_headers
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request

        response = self.handle_exception(exception)
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    def dispatch(self, request, *args, **kwargs):
        # All ops apart from PATCH.
        if not request.method == 'PATCH':
            return self.dispatch_and_handle_exception(request, *args, **kwargs)

        # For PATCH, is JSON bad?
        try:
            request_data = json.loads(request.body.decode(
                settings.DEFAULT_CHARSET
            ))
        except json.JSONDecodeError:
            return self.dispatch_and_handle_exception(request, *args, **kwargs)

        # For PATCH, is payload list?
        if isinstance(request_data, list):
            exception = BadRequest("Request body should be an object for PATCH operation")
            return self.response_with_exception(request, exception, *args, **kwargs)

        # Fire PATCH.
        return self.dispatch_and_handle_exception(request, *args, **kwargs)


class AdminAPIView(BaseAdminAPIView):
    """
    Base from which the various api views of the admin tool are
    defined.
    """
    db_reader = settings.DB_WRITER
    filter_backends = ()

    def _get_object(self, model, **kwargs):
        try:
            return model.objects.using(self.db_reader).get(**kwargs)
        except ValidationError as exc:
            if hasattr(exc, 'messages') and len(exc.messages) > 0:
                raise BadRequest(str(exc.messages[0]))
            else:
                raise BadRequest("Validation failed for some input values")
        except model.DoesNotExist:
            raise Http404("Could not find entity looking for in {}.".format(model.__name__))

    def _get_filtered_object(self, model, request, filter_object, except_filter=[]):
        # db_reader option when specified reads from the connection mentioned in settings.DATABASE
        # This option should be used only for 'GET' requests.
        filter_parameters = request.query_params
        if not set(filter_parameters.keys()).issubset(set(self.filterset_fields)):
            raise BadRequest("Invalid query params.")
        try:
            for filter_param in filter_parameters:
                if filter_param not in except_filter:
                    list_filter_val = filter_parameters[filter_param].split(',')
                    filter_key = filter_param + '__in'
                    filter_object &= Q(**{filter_key: list_filter_val})

            return model.objects.using(self.db_reader).filter(filter_object)
        except Exception as e:
            raise BadRequest("invalid filters")

    def filter_queryset(self, queryset):
        """
        Given a queryset, filter it with whichever filter backend is in use.
        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def check_permissions(self, request):
        if request.version == 'v3':
            if settings.BLOCK_POST_PATCH_DELETE_REQUESTS and not request.method == "GET":
                raise ServiceUnavailable("This service is temporarily unavailable!")
            if request.method == "GET":
                self.db_reader = settings.DB_READER
            else:
                self.db_reader = settings.DB_WRITER

            # 1. If superuser then fall back to default permission checking.
            if request.user.is_superuser:
                return super().check_permissions(request)

            # If "ALL" then appmodule checking to be handled in view.
            appmodule_check_required = getattr(self, "appmodule_id", "") != "ALL"
            # If True then role permission checking to be handled in view.
            permission_check_required = not getattr(self, "permission_exception", False)
            # Check bulk create flag is set or not
            # flag setting logic handled at SingleObjectOnPostMixin
            restrict_bulk_creation = getattr(self, "restrict_bulk_creation", False)
            # 2. If appmodule and permission checks are to be performed, we
            # expect to know who the user is. Complain if we don't
            # know.
            if (
                appmodule_check_required or
                permission_check_required
            ):
                super().check_permissions(request)

            # 3. Check user has access to requested appmodule.
            if appmodule_check_required:
                if 'appmodule_id' in self.kwargs:
                    user_list = UserProfile.objects.filter(user=request.user)
                    if len(user_list) > 0:
                        up = user_list[0]
                    else:
                        raise PermissionDenied("User profile does not match the authentication token.")
                    appmodule_list = [str(appmodule.id) for appmodule in up.appmodules.all()]
                    if not self.kwargs['appmodule_id'] in appmodule_list:
                        raise PermissionDenied("Requested object does not belong to your appmodule")
                else:
                    raise PermissionDenied("Have to mention appmodule_id in View class, if no filter to be applied then set to ALL")

            # 4. Check user is authorized to perform corresponding CRUD operation.
            if permission_check_required:
                user_roles = get_user_roles(self.request.user)
                if self.request.method == "GET":
                    if not (SystemAdmin in user_roles or ReadOnly in user_roles or WriteOnly in user_roles):
                        raise PermissionDenied('You do not have permission to perform this action.')
                elif self.request.method == "POST":
                    if not (SystemAdmin in user_roles or WriteOnly in user_roles):
                        raise PermissionDenied('You do not have permission to perform this action.')
                    if restrict_bulk_creation and not request.user.is_superuser:
                        raise PermissionDenied('You do not have permission to perform the bulk post action.')
                elif self.request.method == "DELETE":
                    if not (SystemAdmin in user_roles or WriteOnly in user_roles):
                        raise PermissionDenied('You do not have permission to perform this action.')
                elif self.request.method == "PATCH":
                    if not (SystemAdmin in user_roles or WriteOnly in user_roles):
                        raise PermissionDenied('You do not have permission to perform this action.')

        return super().check_permissions(request)

    def strip_standard_fields(self, request_data):
        request_data = copy.deepcopy(request_data)
        request_data.pop('created_by', None)
        request_data.pop('id', None)
        request_data.pop('owned_by', None)
        request_data.pop('ts', None)
        return request_data

    def convert_to_array(self, value):
        if value == '':
            return []
        return [value]

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        super().initial(request, *args, **kwargs)


class AmISuperuser(AdminAPIView):
    appmodule_id = 'ALL'
    permission_exception = True

    def get(self, request, *args, **kwargs):
        status_code = (
            status.HTTP_204_NO_CONTENT
            if request.user.is_superuser
            else status.HTTP_404_NOT_FOUND
        )

        return Response(None, status=status_code)


class SendEmail(SingleObjectOnPostMixin, AdminAPIView):
    appmodule_id = 'ALL'
    permission_exception = True

    @method_decorator(superuser_only)
    def post(self, request, appmodule_id, *args, **kwargs):

        mail_object = {}
        mail_object["subject"] = "test"
        mail_object["message"] = "Hello, this is test message."
        mail_object["from_email"] = "help@ittdigital.com"
        # Receiver will be all users from appmodule.
        mail_object["recipient_list"] = ["nishant@ittdigital.com"]

        for em in request.data:
            if itt_send_mail(mail_object, request):
                response = {'message': '1 Email successfully deliverd.'}
            else:
                response = {'message': '0 Email successfully deliverd.'}

        return Response(response)
