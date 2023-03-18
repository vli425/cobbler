"""
TODO
"""

from typing import Any, Callable, List, Tuple

import pytest

from cobbler.cli import CobblerCLI
from cobbler.utils.process_management import service_restart


@pytest.fixture(scope="function", autouse=True)
def restart_daemon():
    """
    Restart cobblerd to re-read all collections after the automatic cleanup.
    """
    service_restart("cobblerd")


@pytest.fixture(scope="function")
def run_cmd(capsys: pytest.CaptureFixture[str]) -> Callable[[Any], Tuple[str, str]]:
    """
    Execute the cli command via the cli object.

    :param capsys: This is a pytest fixture to caputure the stdout and stderr
    :return: The output of the command
    :raises Exception: If something has gone wrong.
    """

    def _run_cmd(cmd: List[str]):
        cmd.insert(0, "cli.py")
        cli = CobblerCLI(cmd)
        cli.check_setup()
        cli.run(cmd)
        return capsys.readouterr()

    return _run_cmd


@pytest.fixture(scope="function")
def list_objects(run_cmd):
    """
    Get objects of a type

    :return: Inner function which returns a list of objects.
    """

    def _list_objects(object_type: str) -> list:
        """
        This is the actual function which is then executed by the outer one.

        :param object_type: object type
        :return: list objects
        """
        objects = []
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "list"])
        lines = outputstd.split("\n")
        for line in lines:
            if line.strip() != "":
                objects.append(line.strip())
        return objects

    return _list_objects
