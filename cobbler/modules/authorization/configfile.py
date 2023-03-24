"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources.
For instance, when using authz_ldap, you want to use authn_configfile,
not authz_allowall, which will most likely NOT do what you want.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


import os
from configparser import SafeConfigParser
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


CONFIG_FILE = "/etc/cobbler/users.conf"


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authz".
    """
    return "authz"


def __parse_config() -> Dict[str, Dict[Any, Any]]:
    """
    Parse the the users.conf file.

    :return: The data of the config file.
    """
    if not os.path.exists(CONFIG_FILE):
        return {}
    config = SafeConfigParser()
    config.read(CONFIG_FILE)
    alldata: Dict[str, Dict[str, Any]] = {}
    groups = config.sections()
    for group in groups:
        alldata[str(group)] = {}
        options = config.options(group)
        for option in options:
            alldata[group][option] = 1
    return alldata


def authorize(
    api_handle: "CobblerAPI",
    user: str,
    resource: str,
    arg1: Any = None,
    arg2: Any = None,
) -> int:
    """
    Validate a user against a resource. All users in the file are permitted by this module.

    :param api_handle: This parameter is not used currently.
    :param user: The user to authorize.
    :param resource: This parameter is not used currently.
    :param arg1: This parameter is not used currently.
    :param arg2: This parameter is not used currently.
    :return: "0" if no authorized, "1" if authorized.
    """
    # FIXME: this must be modified to use the new ACL engine

    data = __parse_config()
    for _, group_data in data.items():
        if user.lower() in group_data:
            return 1
    return 0
