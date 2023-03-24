"""
Migration from V3.0.0 to V3.0.1
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

from typing import Any, Dict, List

from schema import SchemaError  # type: ignore

from cobbler.settings.migrations import V3_0_0

# schema identical to V3_0_0
schema = V3_0_0.schema


def validate(settings: Dict[str, Any]) -> bool:
    """
    Checks that a given settings dict is valid according to the reference schema ``schema``.

    :param settings: The settings dict to validate.
    :return: True if valid settings dict otherwise False.
    """
    try:
        schema.validate(settings)  # type: ignore
    except SchemaError:
        return False
    return True


def normalize(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """
    # We are aware of our schema and thus can safely ignore this.
    return schema.validate(settings)  # type: ignore


def __migrate_modules_conf() -> None:
    modules_conf_path = "/etc/cobbler/modules.conf"
    with open(modules_conf_path, "r", encoding="UTF-8") as modules_conf_file:
        result: List[str] = []
        replacements = {
            "authn_": "authentication.",
            "authz_": "authorization.",
            "manage_": "managers.",
        }
        for line in modules_conf_file:
            for to_replace, replacement in replacements.items():
                idx = line.find(to_replace)
                if idx == -1:
                    continue

                result.append(
                    "%(head)s%(replacement)s%(tail)s"
                    % {
                        "head": line[:idx],
                        "replacement": replacement,
                        "tail": line[idx + len(to_replace) :],
                    }
                )
                break
            else:  # no break occured -> nothing to replace
                result.append(line)
    with open(modules_conf_path, "w", encoding="UTF-8") as modules_conf_file:
        for line in result:
            modules_conf_file.write(line)


def migrate(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migration of the settings ``settings`` to the V3.0.1 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """
    __migrate_modules_conf()

    if not V3_0_0.validate(settings):
        raise SchemaError("V3.0.0: Schema error while validating")
    return normalize(settings)
