from datetime import datetime
from django.core.exceptions import ValidationError
import json
import re

from core.constants import MODULE_MISMATCH_MESSAGE_TEMPLATE


def validate_json_object_not_empty(value):
    validate_json_object(value)

    if not len(json.loads(value)):
        raise ValidationError(
            ('%(value)s should contain at least one key-value pair.'),
            params={'value': value},
        )


def validate_json_object(value):
    validate_json(value)

    if not isinstance(json.loads(value), dict):
        raise ValidationError(
            ('%(value)s is not a valid JSON object.'),
            params={'value': value},
        )


def validate_json(value):
    try:
        json_value = json.loads(value)
    except json.JSONDecodeError:
        raise ValidationError(
            ('%(value)s is not a valid JSON.'),
            params={'value': value},
        )


def validate_instances_belong_to_same_module(
    child_instance=None,
    parent_model=None,
    parent_module_id=None,
):
    if (
        not child_instance or
        not parent_model or
        not parent_module_id
    ):
        return

    if parent_module_id != child_instance.module_id:
        raise ValidationError(MODULE_MISMATCH_MESSAGE_TEMPLATE.format(
            child_instance._meta.model.__name__.lower(),
            parent_model._meta.model.__name__.lower(),
        ))
