from rest_framework.exceptions import APIException


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = 'Service temporarily unavailable, try again later.'
    default_code = 'service_unavailable'


class Conflict(APIException):
    status_code = 409
    default_detail = 'Conflicts with already existing object.'
    default_code = 'object_exist'


class BadRequest(APIException):
    status_code = 400
    default_detail = 'Missin parameter'
    default_code = 'bad_request'
