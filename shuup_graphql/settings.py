# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.test.signals import setting_changed
from django.utils import six

try:
    import importlib  # Available in Python 3.1+
except ImportError:
    from django.utils import importlib  # Will be removed in Django 1.9


# Copied shamelessly from Django Graphene and Django REST Framework

DEFAULTS = {
    # Schema used for Front endpoint
    "FRONT_SCHEMA": "shuup_graphql.front.schema",
    # Schema used for Admin endpoint
    "ADMIN_SCHEMA": "shuup_graphql.admin.schema",
}

# List of settings that may be in string import notation.
IMPORT_STRINGS = (
    "FRONT_SCHEMA",
    "ADMIN_SCHEMA",
)


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, six.string_types):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        parts = val.split(".")
        module_path, class_name = ".".join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        msg = "Could not import '%s' for Shuup GraphQL setting '%s'. %s: %s." % (
            val,
            setting_name,
            e.__class__.__name__,
            e,
        )
        raise ImportError(msg)


class ShuupGraphQLSettings(object):
    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        if user_settings:
            self._user_settings = user_settings
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, "SHUUP_GRAPHQL", {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid Shuup GraphQL setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        setattr(self, attr, val)
        return val


shuup_graphql_settings = ShuupGraphQLSettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_settings(*args, **kwargs):
    global shuup_graphql_settings
    setting, value = kwargs["setting"], kwargs["value"]
    if setting == "SHUUP_GRAPHQL":
        shuup_graphql_settings = ShuupGraphQLSettings(value, DEFAULTS, IMPORT_STRINGS)


setting_changed.connect(reload_settings)
