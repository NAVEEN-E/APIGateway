import copy
import json
import logging
import requests
import sys
import textwrap
from django.conf import settings
from django.core.cache import (
    cache,
)
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.views import exception_handler
from rolepermissions.roles import clear_roles

from app.api_exception import BadRequest
from core.utils import looker
from core.utils.email import itt_send_mail
from app.core.models import (
    UserProfile,
)

logger = logging.getLogger(__name__)

HTTP_CODES = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    416: "Range Not Satisfiable",
    417: "Expectation Failed",
    426: "Upgrade Required",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported"
}


def api_500_handler(exc, **context):
    # Return HttpResponse if the error is from Admin website
    # else return Json Response
    raw_uri = str(exc.get_raw_uri())

    if raw_uri.find("/v1/") > 0:
        response = JsonResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data={
                "errors": ["Server Error for {}".format(exc.get_raw_uri())],
                "message": "Internal Server Error",
            },
        )
        return response
    else:
        type_, value, traceback = sys.exc_info()
        context['exception_details'] = value
        return render(exc, 'itt/500.html', context, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_formatted_error(field, error):
    """
    Formats validation error in `field-error` format.
    Args:
        field: Field name for which validation failed.
        error: Validation error message.
    """
    return "{}-{}".format(
        field,
        error[0] if isinstance(error, list) else error,
    )


def get_formatted_errors(exception_detail):
    """
    Returns all validation errors with field name and error details.

    Args:
        exception_detail: Key value pair of field and error details.

    """
    flattened_error_details = []
    for field, error in exception_detail.items():
        if isinstance(error, dict):
            flattened_error_details.extend([
                [field, error]
                for field, error in error.items()
            ])
        else:
            flattened_error_details.append([
                field,
                error,
            ])

    all_errors = tuple(
        copy.deepcopy(get_formatted_error(
            field=error_detail[0],
            error=error_detail[1],
        )) for error_detail in flattened_error_details
    )

    return(all_errors)


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.

    # Override 'accepted_renderer' and 'accepted_media_type' in
    # request object so that error response always return a json
    # response.
    json_renderer = JSONRenderer()
    context['request'].accepted_renderer = json_renderer
    context['request'].accepted_media_type = json_renderer.media_type

    response = exception_handler(exc, context)

    errors = []
    kys = []
    if (
        hasattr(exc, 'detail') and
        isinstance(exc.detail, dict)
    ):
        errors.extend(get_formatted_errors(exc.detail))
    elif (
        hasattr(exc, 'detail') and
        isinstance(exc.detail, list)
    ):
        for elem in exc.detail:
            for k, v in elem.items():
                er = "{}-{}".format(k, v[0] if isinstance(v, list) else v)
                errors.append(copy.deepcopy(er))
                kys.append(k)
    else:
        er = exc.args[0] if isinstance(exc.args, tuple) and len(exc.args) > 0 else ""
        errors.append(er)

    if response is not None:
        format_type = context['request'].GET.get('format', None)
        valid_format_types = [renderer.format for renderer in context['view'].renderer_classes]
        if format_type and format_type not in valid_format_types:
            error_msg = "The format passed in request '{}' is not supported, the supported values are - {}.".format(
                format_type,
                ', '.join(valid_format_types),
            )
            errors = [error_msg]

            # When a format is passed onto a view that is not
            # supported by the renderers defined on that view, Django
            # throws a 404 to indicate that a renderer was 'not found'
            # that supports this format. This can be confusing, so
            # let's return a 400 instead to indicate that the request
            # is wrong.
            response.status_code = status.HTTP_400_BAD_REQUEST

        if response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
            supported_media_types = [parser.media_type for parser in context['request'].parsers]

            errors = [
                'The media type in the request {} is unsupported, the supported values are - {}.'.format(
                    context['request'].content_type,
                    ', '.join(supported_media_types),
                )
            ]

        response.data = {}
        response.data['errors'] = errors
        response.data['message'] = HTTP_CODES[response.status_code]

    return response


def remove_all_user_permission(auth_user):
    auth_user.is_superuser = False
    auth_user.is_staff = False
    auth_user.is_active = False
    clear_roles(auth_user)
    auth_user.save()


def superuser_only(function):
    """
    Limit view to superusers only.
    """
    def _inner(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to perform this action.")
        return function(request, *args, **kwargs)
    return _inner


def validate_field_ids(model, field_ids):
    found_model_objs = model.objects.filter(id__in=field_ids)
    non_existing_field_ids = set(field_ids) - set([str(model_obj.id) for model_obj in found_model_objs])
    if non_existing_field_ids:
        raise BadRequest('Following {}s do not exist {}.'.format(model().__class__.__name__, non_existing_field_ids))
    return found_model_objs
