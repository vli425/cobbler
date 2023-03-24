"""
This module contains the specific code to generate a network bootable ISO.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler import utils
from cobbler.actions import buildiso
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.items.distro import Distro
    from cobbler.items.profile import Profile
    from cobbler.items.system import System


class AppendLineBuilder:
    """
    This class is meant to be initiated for a single append line. Afterwards the object should be disposed.
    """

    def __init__(self, distro_name: str, data: Dict[str, Any]):
        self.append_line = ""
        self.data = data
        self.distro_name = distro_name
        self.dist: Optional["Distro"] = None
        self.system_interface: Optional[str] = None
        self.system_ip = None
        self.system_netmask = None
        self.system_gw = None
        self.system_dns: Optional[Union[str, List[str]]] = None

    def _system_int_append_line(self) -> None:
        """
        This generates the interface configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_interface is not None:
            intmac = "mac_address_" + self.system_interface
            if self.dist.breed == "suse":
                if self.data.get(intmac, "") != "":
                    self.append_line += f" netdevice={self.data['mac_address_' + self.system_interface].lower()}"
                else:
                    self.append_line += f" netdevice={self.system_interface}"
            elif self.dist.breed == "redhat":
                if self.data.get(intmac, "") != "":
                    self.append_line += (
                        f" ksdevice={self.data['mac_address_' + self.system_interface]}"
                    )
                else:
                    self.append_line += f" ksdevice={self.system_interface}"
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += f" netcfg/choose_interface={self.system_interface}"

    def _system_ip_append_line(self) -> None:
        """
        This generates the IP configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_ip is not None:
            if self.dist.breed == "suse":
                self.append_line += f" hostip={self.system_ip}"
            elif self.dist.breed == "redhat":
                self.append_line += f" ip={self.system_ip}"
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += f" netcfg/get_ipaddress={self.system_ip}"

    def _system_mask_append_line(self) -> None:
        """
        This generates the netmask configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_netmask is not None:
            if self.dist.breed in ["suse", "redhat"]:
                self.append_line += f" netmask={self.system_netmask}"
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += f" netcfg/get_netmask={self.system_netmask}"

    def _system_gw_append_line(self) -> None:
        """
        This generates the gateway configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_gw is not None:
            if self.dist.breed in ["suse", "redhat"]:
                self.append_line += f" gateway={self.system_gw}"
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += f" netcfg/get_gateway={self.system_gw}"

    def _system_dns_append_line(self, exclude_dns: bool) -> None:
        """
        This generates the DNS configuration for the system to boot for the append line.
        :param exclude_dns: If this flag is set to True, the DNS configuration is skipped.
        """
        if self.dist is None:
            return
        if not exclude_dns and self.system_dns is not None:
            if self.dist.breed == "suse":
                nameserver_key = "nameserver"
            elif self.dist.breed == "redhat":
                nameserver_key = "dns"
            elif self.dist.breed in ["ubuntu", "debian"]:
                nameserver_key = "netcfg/get_nameservers"
            else:
                return

            if isinstance(self.system_dns, list):
                joined_nameservers = ",".join(self.system_dns)
                if joined_nameservers != "":
                    self.append_line += f" {nameserver_key}={joined_nameservers}"
            else:
                self.append_line += f" {nameserver_key}={self.system_dns}"

    def _generate_static_ip_boot_interface(self) -> None:
        """
        The interface to use when the system boots.
        """
        if self.dist is None:
            return
        if self.dist.breed == "redhat":
            if self.data["kernel_options"].get("ksdevice", "") != "":
                self.system_interface = self.data["kernel_options"]["ksdevice"]
                if self.system_interface == "bootif":
                    self.system_interface = None
                del self.data["kernel_options"]["ksdevice"]
        elif self.dist.breed == "suse":
            if self.data["kernel_options"].get("netdevice", "") != "":
                self.system_interface = self.data["kernel_options"]["netdevice"]
                del self.data["kernel_options"]["netdevice"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/choose_interface", "") != "":
                self.system_interface = self.data["kernel_options"][
                    "netcfg/choose_interface"
                ]
                del self.data["kernel_options"]["netcfg/choose_interface"]

    def _generate_static_ip_boot_ip(self) -> None:
        """
        Generate the IP which is used during the installation process. This respects overrides.
        """
        if self.dist is None:
            return
        if self.dist.breed == "redhat":
            if self.data["kernel_options"].get("ip", "") != "":
                self.system_ip = self.data["kernel_options"]["ip"]
                del self.data["kernel_options"]["ip"]
        elif self.dist.breed == "suse":
            if self.data["kernel_options"].get("hostip", "") != "":
                self.system_ip = self.data["kernel_options"]["hostip"]
                del self.data["kernel_options"]["hostip"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_ipaddress", "") != "":
                self.system_ip = self.data["kernel_options"]["netcfg/get_ipaddress"]
                del self.data["kernel_options"]["netcfg/get_ipaddress"]

    def _generate_static_ip_boot_mask(self) -> None:
        """
        Generate the Netmask which is used during the installation process. This respects overrides.
        """
        if self.dist is None:
            return
        if self.dist.breed in ["suse", "redhat"]:
            if self.data["kernel_options"].get("netmask", "") != "":
                self.system_netmask = self.data["kernel_options"]["netmask"]
                del self.data["kernel_options"]["netmask"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_netmask", "") != "":
                self.system_netmask = self.data["kernel_options"]["netcfg/get_netmask"]
                del self.data["kernel_options"]["netcfg/get_netmask"]

    def _generate_static_ip_boot_gateway(self) -> None:
        """
        Generate the Gateway which is used during the installation process. This respects overrides.
        """
        if self.dist is None:
            return
        if self.dist.breed in ["suse", "redhat"]:
            if self.data["kernel_options"].get("gateway", "") != "":
                self.system_gw = self.data["kernel_options"]["gateway"]
                del self.data["kernel_options"]["gateway"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_gateway", "") != "":
                self.system_gw = self.data["kernel_options"]["netcfg/get_gateway"]
                del self.data["kernel_options"]["netcfg/get_gateway"]

    def _generate_static_ip_boot_dns(self) -> None:
        """
        Generates the static Boot DNS Server which is used for resolving Domains.
        """
        if self.dist is None:
            return
        if self.dist.breed == "redhat":
            if self.data["kernel_options"].get("dns", "") != "":
                self.system_dns = self.data["kernel_options"]["dns"]
                del self.data["kernel_options"]["dns"]
        elif self.dist.breed == "suse":
            if self.data["kernel_options"].get("nameserver", "") != "":
                self.system_dns = self.data["kernel_options"]["nameserver"]
                del self.data["kernel_options"]["nameserver"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_nameservers", "") != "":
                self.system_dns = self.data["kernel_options"]["netcfg/get_nameservers"]
                del self.data["kernel_options"]["netcfg/get_nameservers"]

    def _generate_static_ip_boot_options(self) -> None:
        """
        Try to add static ip boot options to avoid DHCP (interface/ip/netmask/gw/dns)
        Check for overrides first and clear them from kernel_options
        """
        self._generate_static_ip_boot_interface()
        self._generate_static_ip_boot_ip()
        self._generate_static_ip_boot_mask()
        self._generate_static_ip_boot_gateway()
        self._generate_static_ip_boot_dns()

    def _generate_append_redhat(self) -> None:
        """
        Generate additional content for the append line in case that dist is a RedHat based one.
        """
        if self.data.get("proxy", "") != "":
            self.append_line += (
                f" proxy={self.data['proxy']} http_proxy={self.data['proxy']}"
            )
        if self.dist and self.dist.os_version in [
            "rhel4",
            "rhel5",
            "rhel6",
            "fedora16",
        ]:
            self.append_line += " ks=%s" % self.data["autoinstall"]
        else:
            self.append_line += " inst.ks=%s" % self.data["autoinstall"]

    def _generate_append_debian(self, system: "System") -> None:
        """
        Generate additional content for the append line in case that dist is Ubuntu or Debian.
        :param system: The system which the append line should be generated for.
        """
        if self.dist is None:
            return
        self.append_line += f" auto-install/enable=true url={self.data['autoinstall']} netcfg/disable_autoconfig=true"
        if self.data.get("proxy", "") != "":
            self.append_line += f" mirror/http/proxy={self.data['proxy']}"
        # hostname is required as a parameter, the one in the preseed is not respected
        my_domain = "local.lan"
        if system.hostname != "":
            # if this is a FQDN, grab the first bit
            my_hostname = system.hostname.split(".")[0]
            _domain = system.hostname.split(".")[1:]
            if _domain:
                my_domain = ".".join(_domain)
        else:
            my_hostname = system.name.split(".")[0]
            _domain = system.name.split(".")[1:]
            if _domain:
                my_domain = ".".join(_domain)
        # At least for debian deployments configured for DHCP networking this values are not used, but
        # specifying here avoids questions
        self.append_line += f" hostname={my_hostname} domain={my_domain}"
        # A similar issue exists with suite name, as installer requires the existence of "stable" in the dists
        # directory
        self.append_line += f" suite={self.dist.os_version}"

    def _generate_append_suse(self, scheme: str = "http") -> None:
        """
        Special adjustments for generating the append line for suse.

        :param scheme: This can be either ``http`` or ``https``.
        :return: The updated append line. If the distribution is not SUSE, then nothing is changed.
        """
        if self.dist is None:
            return
        if self.data.get("proxy", "") != "":
            self.append_line += f" proxy={self.data['proxy']}"
        if self.data["kernel_options"].get("install", "") != "":
            self.append_line += f" install={self.data['kernel_options']['install']}"
            del self.data["kernel_options"]["install"]
        else:
            self.append_line += (
                f" install={scheme}://{self.data['server']}:{self.data['http_port']}/cblr/"
                f"links/{self.dist.name}"
            )
        if self.data["kernel_options"].get("autoyast", "") != "":
            self.append_line += f" autoyast={self.data['kernel_options']['autoyast']}"
            del self.data["kernel_options"]["autoyast"]
        else:
            self.append_line += f" autoyast={self.data['autoinstall']}"

    def _adjust_interface_config(self) -> None:
        """
        If no kernel_options overrides are present find the management interface do nothing when zero or multiple
        management interfaces are found.
        """
        if self.system_interface is None:
            mgmt_ints: List[str] = []
            mgmt_ints_multi: List[str] = []
            slave_ints: List[str] = []
            for iname, idata in self.data["interfaces"].items():
                if idata["management"] and idata["interface_type"] in [
                    "bond",
                    "bridge",
                ]:
                    # bonded/bridged management interface
                    mgmt_ints_multi.append(iname)
                if idata["management"] and idata["interface_type"] not in [
                    "bond",
                    "bridge",
                    "bond_slave",
                    "bridge_slave",
                    "bonded_bridge_slave",
                ]:
                    # single management interface
                    mgmt_ints.append(iname)

            if len(mgmt_ints_multi) == 1 and len(mgmt_ints) == 0:
                # Bonded/bridged management interface, find a slave interface if eth0 is a slave use that (it's what
                # people expect)
                for iname, idata in self.data["interfaces"].items():
                    if (
                        idata["interface_type"]
                        in ["bond_slave", "bridge_slave", "bonded_bridge_slave"]
                        and idata["interface_master"] == mgmt_ints_multi[0]
                    ):
                        slave_ints.append(iname)

                if "eth0" in slave_ints:
                    self.system_interface = "eth0"
                else:
                    self.system_interface = slave_ints[0]
                # Set self.system_ip from the bonded/bridged interface here
                self.system_ip = self.data[
                    "ip_address_"
                    + self.data["interface_master_" + self.system_interface]
                ]
                self.system_netmask = self.data[
                    "netmask_" + self.data["interface_master_" + self.system_interface]
                ]

            if len(mgmt_ints) == 1 and len(mgmt_ints_multi) == 0:
                # Single management interface
                self.system_interface = mgmt_ints[0]

    def _get_tcp_ip_config(self) -> None:
        """
        Lookup tcp/ip configuration data. If not present already present this adds it from the previously blenderd data.
        """
        if self.system_ip is None and self.system_interface is not None:
            intip = "ip_address_" + self.system_interface
            if self.data.get(intip, "") != "":
                self.system_ip = self.data["ip_address_" + self.system_interface]
        if self.system_netmask is None and self.system_interface is not None:
            intmask = "netmask_" + self.system_interface
            if self.data.get(intmask, "") != "":
                self.system_netmask = self.data["netmask_" + self.system_interface]
        if self.system_gw is None:
            if self.data.get("gateway", "") != "":
                self.system_gw = self.data["gateway"]
        if self.system_dns is None:
            if self.data.get("name_servers") != "":
                self.system_dns = self.data["name_servers"]

    def generate_system(
        self, dist: "Distro", system: "System", exclude_dns: bool, scheme: str = "http"
    ) -> str:
        """
        Generate the append-line for a net-booting system.

        :param dist: The distribution associated with the system.
        :param system: The system itself
        :param exclude_dns: Whether to include the DNS config or not.
        :param scheme: The scheme that is used to read the autoyast file from the server
        """
        self.dist = dist

        self.append_line = f"  APPEND initrd={self.distro_name}.img"
        if self.dist.breed == "suse":
            self._generate_append_suse(scheme=scheme)
        elif self.dist.breed == "redhat":
            self._generate_append_redhat()
        elif dist.breed in ["ubuntu", "debian"]:
            self._generate_append_debian(system)

        self._generate_static_ip_boot_options()
        self._adjust_interface_config()
        self._get_tcp_ip_config()

        # Add information to the append_line
        self._system_int_append_line()
        self._system_ip_append_line()
        self._system_mask_append_line()
        self._system_gw_append_line()
        self._system_dns_append_line(exclude_dns)

        # Add remaining kernel_options to append_line
        self.append_line += buildiso.add_remaining_kopts(self.data["kernel_options"])
        return self.append_line

    def generate_profile(
        self, distro_breed: str, os_version: str, protocol: str = "http"
    ) -> str:
        """
        Generate the append line for the kernel for a network installation.
        :param distro_breed: The name of the distribution breed.
        :param os_version: The OS version of the distribution.
        :param protocol: The scheme that is used to read the autoyast file from the server
        :return: The generated append line.
        """
        self.append_line = f" append initrd={self.distro_name}.img"
        if distro_breed == "suse":
            if self.data.get("proxy", "") != "":
                self.append_line += f" proxy={self.data['proxy']}"
            if self.data["kernel_options"].get("install", "") != "":
                install_options: Union[str, List[str]] = self.data["kernel_options"][
                    "install"
                ]
                if isinstance(install_options, list):
                    install_options = install_options[0]
                    self.append_line += f" install={install_options}"
                del self.data["kernel_options"]["install"]
            else:
                self.append_line += (
                    f" install={protocol}://{self.data['server']}:{self.data['http_port']}/cblr/"
                    f"links/{self.distro_name}"
                )
            if self.data["kernel_options"].get("autoyast", "") != "":
                self.append_line += (
                    f" autoyast={self.data['kernel_options']['autoyast']}"
                )
                del self.data["kernel_options"]["autoyast"]
            else:
                self.append_line += f" autoyast={self.data['autoinstall']}"
        elif distro_breed == "redhat":
            if self.data.get("proxy", "") != "":
                self.append_line += (
                    f" proxy={self.data['proxy']} http_proxy={self.data['proxy']}"
                )
            if os_version in ["rhel4", "rhel5", "rhel6", "fedora16"]:
                self.append_line += " ks=%s" % self.data["autoinstall"]
            else:
                self.append_line += " inst.ks=%s" % self.data["autoinstall"]
        elif distro_breed in ["ubuntu", "debian"]:
            self.append_line += (
                f" auto-install/enable=true url={self.data['autoinstall']}"
            )
            if self.data.get("proxy", "") != "":
                self.append_line += f" mirror/http/proxy={self.data['proxy']}"
        self.append_line += buildiso.add_remaining_kopts(self.data["kernel_options"])
        return self.append_line


class NetbootBuildiso(buildiso.BuildIso):
    """
    This class contains all functionality related to building network installation images.
    """

    def filter_systems(self, selected_items: Optional[List[str]] = None) -> List[Any]:
        """
        Return a list of valid system objects selected from all systems by name, or everything if ``selected_items`` is
        empty.
        :param selected_items: A list of names to include in the returned list.
        :return: A list of valid systems. If an error occurred this is logged and an empty list is returned.
        """
        if selected_items is None:
            selected_items = []
        found_systems = self.filter_items(self.api.systems(), selected_items)
        # Now filter all systems out that are image based as we don't know about their kernel and initrds
        return_systems: List["System"] = []
        for system in found_systems:
            # All systems not underneath a profile should be skipped
            parent_obj = system.get_conceptual_parent()
            if parent_obj is not None and parent_obj.TYPE_NAME == "profile":
                return_systems.append(system)
        # Now finally return
        return return_systems

    def make_shorter(self, distname: str) -> str:
        """
        Return a short distro identifier which is basically an internal counter which is mapped via the real distro
        name.
        :param distname: The distro name to return an identifier for.
        :return: A short distro identifier
        """
        if distname in self.distmap:
            return self.distmap[distname]

        self.distctr += 1
        self.distmap[distname] = str(self.distctr)
        return str(self.distctr)

    def _generate_netboot_system(
        self, system: "System", cfglines: List[str], exclude_dns: bool
    ):
        """
        Generates the ISOLINUX cfg configuration for any systems included in the image.
        :param system: The system which the configuration should be generated for.
        :param cfglines: The already existing lines of the configuration.
        :param exclude_dns: If DNS configuration should be excluded or not.
        """
        self.logger.info("processing system: %s", system.name)
        profile: Optional["Profile"] = system.get_conceptual_parent()  # type: ignore
        if profile is None:
            raise ValueError("Profile not found!")
        dist: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
        if dist is None:
            raise ValueError("Profile not found!")
        distname = self.make_shorter(dist.name)
        self.copy_boot_files(dist, self.isolinuxdir, distname)

        cfglines.append("")
        cfglines.append(f"LABEL {system.name}")
        cfglines.append(f"  MENU LABEL {system.name}")
        cfglines.append(f"  KERNEL {distname}.krn")

        data = utils.blender(self.api, False, system)
        autoinstall_scheme = self.api.settings().autoinstall_scheme
        if not re.match(r"[a-z]+://.*", data["autoinstall"]):
            data["autoinstall"] = (
                f"{autoinstall_scheme}://{data['server']}:{data['http_port']}/cblr/svc/op/autoinstall/"
                f"system/{system.name}"
            )

        append_builder = AppendLineBuilder(distro_name=distname, data=data)
        append_line = append_builder.generate_system(
            dist, system, exclude_dns, autoinstall_scheme
        )
        cfglines.append(append_line)

    def _generate_netboot_profile(self, profile: "Profile", cfglines: List[str]):
        """
        Generates the ISOLINUX cfg configuration for any profiles included in the image.
        :param profile: The profile which the configuration should be generated for.
        :param cfglines: The already existing lines of the configuration.
        """
        self.logger.info('Processing profile: "%s"', profile.name)
        dist: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
        if dist is None:
            raise ValueError("distro for profile not found!")
        distname = self.make_shorter(dist.name)
        self.copy_boot_files(dist, self.isolinuxdir, distname)

        cfglines.append("")
        cfglines.append(f"LABEL {profile.name}")
        cfglines.append(f"  MENU LABEL {profile.name}")
        cfglines.append(f"  kernel {distname}.krn")

        data = utils.blender(self.api, False, profile)

        # SUSE is not using 'text'. Instead 'textmode' is used as kernel option.
        utils.kopts_overwrite(
            data["kernel_options"], self.api.settings().server, dist.breed
        )

        if not re.match(r"[a-z]+://.*", data["autoinstall"]):
            autoinstall_scheme = self.api.settings().autoinstall_scheme
            data["autoinstall"] = (
                f"{autoinstall_scheme}://{data['server']}:{data['http_port']}/cblr/svc/op/autoinstall/"
                f"profile/{profile.name}"
            )

        append_builder = AppendLineBuilder(distro_name=distname, data=data)
        append_line = append_builder.generate_profile(dist.breed, dist.os_version)
        cfglines.append(append_line)

    def generate_netboot_iso(
        self, systems: Optional[List[str]] = None, exclude_dns: bool = False
    ):
        """
        Creates the ``isolinux.cfg`` for a network bootable ISO image.

        :param systems: The filter to generate a netboot iso for. You may specify multiple systems on the CLI space
                        separated.
        :param exclude_dns: If this is True then the dns server is skipped. False will set it.
        """
        # setup isolinux.cfg
        isolinuxcfg = os.path.join(self.isolinuxdir, "isolinux.cfg")
        cfglines = [self.iso_template]

        # iterate through selected profiles
        for profile in self.filter_profiles(self.profiles):
            self._generate_netboot_profile(profile, cfglines)
        cfglines.append("MENU SEPARATOR")
        # iterate through all selected systems
        for system in self.filter_systems(systems):
            self._generate_netboot_system(system, cfglines, exclude_dns)
        cfglines.append("")
        cfglines.append("MENU END")

        with open(isolinuxcfg, "w+", encoding="UTF-8") as cfg:
            cfg.writelines(f"{line}\n" for line in cfglines)

    def run(
        self,
        iso: str = "autoinst.iso",
        buildisodir: str = "",
        profiles: Optional[List[str]] = None,
        xorrisofs_opts: str = "",
        distro_name: str = "",
        systems: Optional[List[str]] = None,
        exclude_dns: bool = False,
    ):
        """
        Run the whole iso generation from bottom to top. Per default this builds an ISO for all available systems
        and profiles.

        This is the only method which should be called from non-class members. The ``profiles`` and ``system``
        parameters can be combined.

        :param iso: The name of the iso. Defaults to "autoinst.iso".
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param profiles: The filter to generate the ISO only for selected profiles.
        :param xorrisofs_opts: ``xorrisofs`` options to include additionally.
        :param distro_name: For detecting the architecture of the ISO.
        :param systems: Don't use that when building standalone ISOs. The filter to generate the ISO only for selected
                        systems.
        :param exclude_dns: Whether the repositories have to be locally available or the internet is reachable.
        """
        buildisodir = self._prepare_iso(buildisodir, distro_name, profiles)
        systems = input_converters.input_string_or_list_no_inherit(systems)
        self.generate_netboot_iso(systems, exclude_dns)
        self._generate_iso(xorrisofs_opts, iso, buildisodir)
