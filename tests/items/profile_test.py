"""
TODO
"""

from typing import Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile

from tests.conftest import does_not_raise


def test_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    profile = Profile(cobbler_api)

    # Arrange
    assert isinstance(profile, Profile)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    result = profile.make_clone()

    # Assert
    assert result != profile


def test_to_dict(
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
):
    # Arrange
    distro: Distro = create_distro()
    profile: Profile = create_profile(distro_name=distro.name)

    # Act
    result = profile.to_dict()

    # Assert
    assert len(result) == 45
    assert result["distro"] == distro.name
    assert result.get("boot_loaders") == enums.VALUE_INHERITED


def test_to_dict_resolved(
    cobbler_api: CobblerAPI, create_distro: Callable[[str], Distro]
):
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    cobbler_api.add_distro(test_distro)
    titem = Profile(cobbler_api)
    titem.name = "to_dict_resolved_profile"
    titem.distro = test_distro.name
    titem.kernel_options = {"my_value": 5}
    cobbler_api.add_profile(titem)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": True, "my_value": 5}
    assert result.get("boot_loaders") == ["grub", "pxe", "ipxe"]
    assert enums.VALUE_INHERITED not in str(result)


# Properties Tests


def test_parent_empty(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.parent = ""

    # Assert
    assert profile.parent is None


def test_parent_profile(cobbler_api: CobblerAPI, create_distro, create_profile):
    # Arrange
    test_dist = create_distro()
    test_profile = create_profile(test_dist.name)
    profile = Profile(cobbler_api)

    # Act
    profile.parent = test_profile.name

    # Assert
    assert profile.parent is test_profile


def test_parent_other_object_type(cobbler_api: CobblerAPI, create_image):
    # Arrange
    test_image = create_image()
    profile = Profile(cobbler_api)

    # Act
    with pytest.raises(CX):
        profile.parent = test_image.name


def test_parent_invalid_type(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act & Assert
    with pytest.raises(TypeError):
        profile.parent = 0


def test_parent_self(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)
    profile.name = "testname"

    # Act & Assert
    with pytest.raises(CX):
        profile.parent = profile.name


def test_distro(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.distro = ""

    # Assert
    assert profile.distro is None


def test_name_servers(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers = []

    # Assert
    assert profile.name_servers == []


def test_name_servers_search(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers_search = ""

    # Assert
    assert profile.name_servers_search == ""


def test_proxy(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.proxy = ""

    # Assert
    assert profile.proxy == ""


@pytest.mark.parametrize("value,expected_exception", [(False, does_not_raise())])
def test_enable_ipxe(cobbler_api: CobblerAPI, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_ipxe = value

        # Assert
        assert profile.enable_ipxe is value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (True, does_not_raise()),
        (False, does_not_raise()),
        ("", does_not_raise()),
        (0, does_not_raise()),
    ],
)
def test_enable_menu(cobbler_api: CobblerAPI, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_menu = value

        # Assert
        assert isinstance(profile.enable_menu, bool)
        assert profile.enable_menu or not profile.enable_menu


def test_dhcp_tag(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.dhcp_tag = ""

    # Assert
    assert profile.dhcp_tag == ""


@pytest.mark.parametrize(
    "input_server,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), "192.168.1.1"),
        (False, pytest.raises(TypeError), ""),
    ],
)
def test_server(
    cobbler_api: CobblerAPI, input_server, expected_exception, expected_result
):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.server = input_server

        # Assert
        assert profile.server == expected_result


def test_next_server_v4(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v4 = ""

    # Assert
    assert profile.next_server_v4 == ""


def test_next_server_v6(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v6 = ""

    # Assert
    assert profile.next_server_v6 == ""


@pytest.mark.parametrize(
    "input_filename,expected_result,is_subitem,expected_exception",
    [
        ("", "", False, does_not_raise()),
        ("", "", True, does_not_raise()),
        ("<<inherit>>", "", False, does_not_raise()),
        ("<<inherit>>", "", True, does_not_raise()),
        ("test", "test", False, does_not_raise()),
        ("test", "test", True, does_not_raise()),
        (0, "", True, pytest.raises(TypeError)),
    ],
)
def test_filename(
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    input_filename,
    expected_result,
    is_subitem,
    expected_exception,
):
    # Arrange
    test_dist = create_distro()
    profile = Profile(cobbler_api)
    profile.name = "filename_test_profile"
    if is_subitem:
        test_profile = create_profile(test_dist.name)
        profile.parent = test_profile.name
    profile.distro = test_dist.name

    # Act
    with expected_exception:
        profile.filename = input_filename

        # Assert
        assert profile.filename == expected_result


def test_autoinstall(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.autoinstall = ""

    # Assert
    assert profile.autoinstall == ""


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), False),
        ("<<inherit>>", does_not_raise(), True),
        (False, does_not_raise(), False),
        (True, does_not_raise(), True),
    ],
)
def test_virt_auto_boot(
    cobbler_api: CobblerAPI, value, expected_exception, expected_result
):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_auto_boot = value

        # Assert
        assert isinstance(profile.virt_auto_boot, bool)
        assert profile.virt_auto_boot is expected_result


@pytest.mark.parametrize(
    "value,expected_exception, expected_result",
    [
        ("", does_not_raise(), 0),
        # FIXME: (False, pytest.raises(TypeError)), --> does not raise
        (-5, pytest.raises(ValueError), -5),
        (0, does_not_raise(), 0),
        (5, does_not_raise(), 5),
    ],
)
def test_virt_cpus(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_cpus = value

        # Assert
        assert profile.virt_cpus == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("5", does_not_raise(), 5.0),
        ("<<inherit>>", does_not_raise(), 5.0),
        # FIXME: (False, pytest.raises(TypeError)), --> does not raise
        (-5, pytest.raises(ValueError), 0),
        (0, does_not_raise(), 0.0),
        (5, does_not_raise(), 5.0),
    ],
)
def test_virt_file_size(
    cobbler_api: CobblerAPI, value, expected_exception, expected_result
):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_file_size = value

        # Assert
        assert profile.virt_file_size == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("qcow2", does_not_raise(), enums.VirtDiskDrivers.QCOW2),
        ("<<inherit>>", does_not_raise(), enums.VirtDiskDrivers.RAW),
        (enums.VirtDiskDrivers.QCOW2, does_not_raise(), enums.VirtDiskDrivers.QCOW2),
        (False, pytest.raises(TypeError), None),
        ("", pytest.raises(ValueError), None),
    ],
)
def test_virt_disk_driver(
    cobbler_api: CobblerAPI, value, expected_exception, expected_result
):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_disk_driver = value

        # Assert
        assert profile.virt_disk_driver == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), 0),
        ("<<inherit>>", does_not_raise(), 512),
        (0, does_not_raise(), 0),
        (0.0, pytest.raises(TypeError), 0),
    ],
)
def test_virt_ram(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_ram = value

        # Assert
        assert profile.virt_ram == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("<<inherit>>", does_not_raise(), enums.VirtType.XENPV),
        ("qemu", does_not_raise(), enums.VirtType.QEMU),
        (enums.VirtType.QEMU, does_not_raise(), enums.VirtType.QEMU),
        ("", pytest.raises(ValueError), None),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_virt_type(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_type = value

        # Assert
        assert profile.virt_type == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("<<inherit>>", does_not_raise(), "xenbr0"),
        ("random-bridge", does_not_raise(), "random-bridge"),
        ("", does_not_raise(), "xenbr0"),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_virt_bridge(
    cobbler_api: CobblerAPI, value, expected_exception, expected_result
):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_bridge = value

        # Assert
        # This is the default from the settings
        assert profile.virt_bridge == expected_result


def test_virt_path(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.virt_path = ""

    # Assert
    assert profile.virt_path == ""


def test_repos(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.repos = ""

    # Assert
    assert profile.repos == []


def test_redhat_management_key(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.redhat_management_key = ""

    # Assert
    assert profile.redhat_management_key == ""


def test_boot_loaders(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.boot_loaders = ""

    # Assert
    assert profile.boot_loaders == []


def test_menu(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.menu = ""

    # Assert
    assert profile.menu == ""


def test_display_name(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.display_name = ""

    # Assert
    assert profile.display_name == ""
