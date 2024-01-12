# jobs.py

import json
import pandas as pd
import numpy as np

from django.apps import apps
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError
from django.db.models import Q

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.ipam.models import IPAddress, Role, VLAN, VRF, Prefix
from nautobot.dcim.models import Site, Region, Device, Interface
from nautobot.extras.models import Tag, Status
from nautobot.extras.jobs import (
    Job,
    IntegerVar,
    StringVar,
    ObjectVar,
    MultiObjectVar,
    ChoiceVar,
    FileVar,
    IPNetworkVar,
    IPAddressWithMaskVar,
    BooleanVar
)

###


class DCNUpdateDeviceInterfaces(Job):
    template_name = "NautobotPluginTest/interface_update.html"

    class Meta:
        name = "Update Device Physical Interfaces"
        hidden = False
        description = "Update Device Physical Interfaces"
        field_order = [
            "device",
            "interface",
            "interface_status",
            "interface_desc",
            "parent_lag",
            "mode",
            "IP",
            "untagged_vlan",
            "tagged_vlans",
        ]

    # Forms element objects
    device = ObjectVar(
        model=Device, display_field="name", label="Device:", required=True
    )
    interface = ObjectVar(
        model=Interface,
        display_field="name",
        query_params={"device_id": "$device"},
        label="Interface:",
        required=True,
    )
    parent_lag = ObjectVar(
        model=Interface,
        display_field="name",
        query_params={"device_id": "$device", "type": "lag"},
        label="Parent LAG:",
        required=False,
    )
    interface_status = ObjectVar(
        model=Status,
        display_field="name",
        label="Status:",
        query_params={"name": ["Active", "Shutdown"]},
        required=False,
    )
    interface_desc = StringVar(
        default="device:port", label="Interface Description:", required=False
    )
    mode = ChoiceVar(
        choices=(
            ("", ""),
            ("access", "Access"),
            ("pruned_trunk", "Pruned Trunk"),
            ("unpruned_trunk", "Unpruned Trunk"),
            ("routed", "Routed"),
        ),
        label="Mode:",
        required=False,
    )
    IP = ObjectVar(
        model=IPAddress, display_field="address", label="IP:", required=False
    )
    untagged_vlan = ObjectVar(
        model=VLAN, display_field="vid", label="Untagged VLAN:", required=False
    )
    tagged_vlans = MultiObjectVar(
        model=VLAN, display_field="vid", label="Tagged VLANs:", required=False
    )

    def run(self, data, commit):
        # Accept data and commit
        self.data = data
        self.commit = commit
        # Establish required variables from form
        self.device_id = self.data["device"].id
        self.interface_id = self.data["interface"].id
        # Establish remaining variables if they are set, or sets them to None
        try:
            self.status_id = self.data["interface_status"].id
        except:
            self.log_info("Status not set, retaining existing value.")
            self.status_id = None
        try:
            self.interface_desc = self.data["interface_desc"]
        except:
            self.log_info("Description not provided, retaining existing value.")
            self.interface_desc = None
        try:
            if self.data["mode"] == "":
                self.interface_mode = None
            else:
                self.interface_mode = self.data["mode"]
        except:
            self.log_info("Mode not provided, retaining existing value.")
            self.interface_mode = None
        try:
            self.parent_lag_id = self.data["parent_lag"].id
        except:
            self.log_info("LAG not provided, retaining existing value.")
            self.parent_lag_id = None
        try:
            self.parent_lag_mode = self.data["parent_lag"].mode
        except:
            self.log_info("LAG not provided, no mode to set.")
            self.parent_lag_mode = None
        #### Updates interface as if it's not in a LAG
        if self.parent_lag_id is None and self.interface_mode is not None:
            ### Updates port to Routed mode (interface to the IP in the database)
            if self.data["IP"] is not None and self.interface_mode == "routed":
                # Gets the PK of the IP from the form
                self.ip_id = self.data["IP"].id
                # Looks up the IP in the DB
                ip_obj = IPAddress.objects.get(pk=self.ip_id)
                # Assign the IP to the interface
                ip_obj.assigned_object_id = self.interface_id
                ip_obj.assigned_object_type_id = 4
                ip_obj.save()
                # Looks up the Interface in the DB
                int_obj = Interface.objects.get(pk=self.interface_id)
                # Sets the rest of the variables
                int_obj.mode = ""
                if self.status_id is not None:
                    int_obj.status_id = self.status_id
                int_obj.untagged_vlan_id = None
                int_obj.tagged_vlans.clear()
                if self.interface_desc is not None:
                    int_obj.description = self.interface_desc
                int_obj.lag_id = None
                int_obj.save()
                self.log_success(
                    obj=int_obj, message=f"{int_obj} has been updated to a routed port."
                )
            ### Updates port to Access mode
            if (
                self.data["untagged_vlan"] is not None
                and self.interface_mode == "access"
            ):
                # Gets the PK of the untagged vlan from the form
                self.untagged_vlan_id = self.data["untagged_vlan"].id
                # Checks if an IP address was assigned to the interface and removes the association if present
                try:
                    ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                    ip_obj.assigned_object_id = None
                    ip_obj.assigned_object_type_id = None
                    ip_obj.save()
                except:
                    self.log_info("Interface had no assigned IP to remove.")
                    pass
                # Looks up the Interface in the DB
                int_obj = Interface.objects.get(pk=self.interface_id)
                # Mode must be set before untagged_vlan can be added
                int_obj.mode = "access"
                int_obj.save()
                # Sets the rest of the variabes
                if self.status_id is not None:
                    int_obj.status_id = self.status_id
                int_obj.tagged_vlans.clear()
                int_obj.untagged_vlan_id = self.untagged_vlan_id
                if self.interface_desc is not None:
                    int_obj.description = self.interface_desc
                int_obj.lag_id = None
                int_obj.save()
                self.log_success(
                    obj=int_obj,
                    message=f"{int_obj} has been changed to an access port.",
                )
            ### Updates port to Pruned Trunk
            elif (
                self.data["tagged_vlans"] is not None
                and self.interface_mode == "pruned_trunk"
            ):
                # Checks if an IP address was assigned to the interface and removes the association if present
                try:
                    ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                    ip_obj.assigned_object_id = None
                    ip_obj.assigned_object_type_id = None
                    ip_obj.save()
                except:
                    self.log_info("Interface had no assigned IP to remove.")
                    pass
                # Gets the PKs of the tagged vlans from the form
                self.tagged_vlans_ids = [vlan.id for vlan in self.data["tagged_vlans"]]
                # Looks up the Interface in the DB
                int_obj = Interface.objects.get(pk=self.interface_id)
                # Mode must be set before tagged_vlans can be added
                int_obj.mode = "tagged"
                int_obj.lag_id = None
                int_obj.save()
                # Gets VLAN objects
                vlan_objs = []
                for vlan in self.tagged_vlans_ids:
                    vlan_objs.append(VLAN.objects.get(pk=vlan))
                # Sets tagged VLANs
                for vlan_obj in vlan_objs:
                    int_obj.tagged_vlans.add(vlan_obj)
                # Sets the rest of the variabes
                if self.status_id is not None:
                    int_obj.status_id = self.status_id
                int_obj.untagged_vlan_id = None
                if self.interface_desc is not None:
                    int_obj.description = self.interface_desc
                int_obj.lag_id = None
                int_obj.save()
                self.log_success(
                    obj=int_obj,
                    message=f"{int_obj} has been changed to an pruned trunk port.",
                )
            ### Updates port to Unpruned Trunk
            elif self.interface_mode == "unpruned_trunk":
                # Checks if an IP address was assigned to the interface and removes the association if present
                try:
                    ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                    ip_obj.assigned_object_id = None
                    ip_obj.assigned_object_type_id = None
                    ip_obj.save()
                except:
                    self.log_info("Interface had no assigned IP to remove.")
                    pass
                # Looks up the Interface in the DB
                int_obj = Interface.objects.get(pk=self.interface_id)
                # Sets the rest of the variabes
                int_obj.mode = "tagged-all"
                if self.status_id is not None:
                    int_obj.status_id = self.status_id
                int_obj.tagged_vlans.clear()
                int_obj.untagged_vlan_id = None
                if self.interface_desc is not None:
                    int_obj.description = self.interface_desc
                int_obj.lag_id = None
                int_obj.save()
                self.log_success(
                    obj=int_obj,
                    message=f"{int_obj} has been changed to an unpruned trunk port.",
                )
            ### Mode is set but options weren't provided
            else:
                self.log_failure(
                    message="Nothing commited. Please make sure to provide either the IP or vlans as asked when mode is set."
                )
        #### Updates interface to be in a LAG
        elif self.parent_lag_id is not None and self.interface_mode is None:
            # Looks up the Interface and LAG in the DB
            int_obj = Interface.objects.get(pk=self.interface_id)
            lag_obj = Interface.objects.get(pk=self.parent_lag_id)
            # Checks if an IP address was assigned to the interface and removes the association if present
            try:
                ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                ip_obj.assigned_object_id = None
                ip_obj.assigned_object_type_id = None
                ip_obj.save()
            except:
                self.log_info("Interface had no assigned IP to remove.")
                pass
            # Sets interface mode to match LAG mode, and sets interfaces parent LAG equal to the LAG ID retrieved
            int_obj.mode = lag_obj.mode
            int_obj.lag_id = lag_obj.id
            # Sets the rest of the variabes
            if self.status_id is not None:
                int_obj.status_id = self.status_id
            if self.interface_desc is not None:
                int_obj.description = self.interface_desc
            int_obj.tagged_vlans.clear()
            int_obj.untagged_vlan_id = None
            int_obj.save()
            self.log_success(
                obj=int_obj, message=f"{int_obj} has been changed to LAG member."
            )
        # Either mode and parent_lag set, or neither are set.
        else:
            self.log_failure(
                message="Nothing commited. Please make sure that either mode or LAG is set. Both cannot be set."
            )


###


class DCNBulkUpdateInterfaces(Job):
    class Meta:
        name = "DCN Bulk Update Interfaces"
        hidden = False
        description = "Imports a Cabling Mac into Nautobot to bulk update interfaces."

    cabling_mac = FileVar(
        label="Upload Cabling MAC", description="Cabling MAC interface bulk import"
    )

    def run(self, data, commit):
        # Accept data and commit
        self.commit = commit
        # Accept in the Cabling MAC XLSX, target the Cabling sheet, and ignore the first row
        mac = pd.read_excel(data["cabling_mac"], sheet_name="Cabling", header=1)
        # Replace the nan values with None instead for logic checking
        mac = mac.replace(np.nan, None)
        # Convert the sheet into a dictionary where each dictionary item represents a row
        mac = mac.to_dict(orient="records")
        # Get status UUID
        for status in Status.objects.all():
            if status.name == "Active":
                status_obj = status
        # For each row in the cabling mac
        for row in mac:
            if row.get("Mode") not in [None, "N/A"]:         
                # Does the device exist in Nautobot
                try:
                    dev_obj = Device.objects.get(name=row.get("Device.1"))
                    site_obj = dev_obj.site_id
                except Device.DoesNotExist:
                    raise ValueError(f"{row.get('Device.1')} does not exist.")
                if dev_obj:
                    # If LAG is defined
                    if row.get("Port-Channel") is not None:
                        # Retrieves the LAG interface if it exists
                        lag_obj = None
                        try:
                            lag_obj = Interface.objects.get(
                                Q(name=row.get("Port-Channel")), Q(device_id=dev_obj.id)
                            )
                            lag_obj.description = row.get("Port-Channel Name")
                            self.log_info(
                                message=f"{lag_obj.name} already exists. Ignoring description and mode settings."
                            )
                        # If the LAG doesn't exist, create it
                        except Interface.DoesNotExist:
                            lag_obj = Interface(
                                name=row.get("Port-Channel"),
                                device_id=dev_obj.id,
                                type="lag",
                                status_id=status_obj.pk,
                                description=row.get("Port-Channel Name"),
                            )
                            self.log_info(
                                message=f"{lag_obj.name} will be created on {dev_obj.name}."
                            )
                            lag_obj.validated_save()
                        # Set the mode config
                        mode = row.get("Mode")
                        if mode == "Pruned Trunk":
                            # Must set mode before assigning vlans
                            lag_obj.mode = "tagged"
                            lag_obj.save()
                            # Gets VLAN objects
                            vlan_objs = []
                            vlans = str(row.get("VLANs")).split(",")
                            for vlan in vlans:
                                # DC local VLAN
                                try:
                                    vlan_objs.append(
                                        VLAN.objects.get(
                                            vid=int(vlan), site_id=site_obj
                                        )
                                    )
                                # Fabric global VLAN
                                except VLAN.DoesNotExist:
                                    try:
                                        vlan_objs.append(
                                            VLAN.objects.get(
                                                vid=int(vlan), site_id=None
                                            )
                                        )
                                    except VLAN.DoesNotExist:
                                        raise ValueError(f"VLAN{vlan} does not exist. (LAG Depth Pruned Trunk)")
                            # Sets tagged VLANs
                            for vlan_obj in vlan_objs:
                                lag_obj.tagged_vlans.add(vlan_obj)
                            # Checks if an IP address was assigned to the interface and removes the association if present
                            try:
                                ip_obj = IPAddress.objects.get(
                                    assigned_object_id=lag_obj.id
                                )
                                ip_obj.assigned_object_id = None
                                ip_obj.assigned_object_type_id = None
                                ip_obj.save()
                            except:
                                self.log_info(
                                    f"{lag_obj.name} had no assigned IP to remove."
                                )
                                pass
                            # Sets the rest of the variables
                            lag_obj.untagged_vlan = None
                            self.log_info(
                                message=f"{lag_obj.name} was set to a pruned trunk."
                            )
                        elif mode == "Unpruned Trunk":
                            # Checks if an IP address was assigned to the interface and removes the association if present
                            try:
                                ip_obj = IPAddress.objects.get(
                                    assigned_object_id=lag_obj.id
                                )
                                ip_obj.assigned_object_id = None
                                ip_obj.assigned_object_type_id = None
                                ip_obj.save()
                            except:
                                self.log_info(
                                    f"{lag_obj.name} had no assigned IP to remove."
                                )
                                pass
                            # Must set mode before assigning vlans
                            lag_obj.mode = "tagged-all"
                            lag_obj.save()
                            # Sets the rest of the variables
                            lag_obj.untagged_vlan = None
                            lag_obj.tagged_vlans.clear()
                            self.log_info(
                                message=f"{lag_obj.name} was set to an unpruned trunk."
                            )
                        elif mode == "Access":
                            # Checks if an IP address was assigned to the interface and removes the association if present
                            try:
                                ip_obj = IPAddress.objects.get(
                                    assigned_object_id=lag_obj.id
                                )
                                ip_obj.assigned_object_id = None
                                ip_obj.assigned_object_type_id = None
                                ip_obj.save()
                            except:
                                self.log_info(
                                    f"{lag_obj.name} had no assigned IP to remove."
                                )
                                pass
                            # Must set mode before assigning vlans
                            lag_obj.mode = "access"
                            lag_obj.save()
                            # Gets VLAN object
                            vlan = str(row.get("VLANs")).split(",")
                            # If more than one VLAN is present but the port is set to access, only the first VLAN is used
                            try:
                                vlan_obj = VLAN.objects.get(
                                    vid=int(vlan[0]), site_id=site_obj
                                )
                            except VLAN.DoesNotExist:
                                try:
                                    vlan_obj = VLAN.objects.get(
                                        vid=int(vlan[0]), site_id=None
                                    )
                                except VLAN.DoesNotExist:
                                        raise ValueError(f"VLAN{vlan} does not exist. (LAG Depth Access)")
                            # Sets the rest of the variables
                            lag_obj.tagged_vlans.clear()
                            lag_obj.untagged_vlan = vlan_obj
                            self.log_info(
                                message=f"{lag_obj.name} was set to an access port."
                            )
                        elif mode == "Routed":
                            # Looks up the IP in the DB
                            try:
                                ip_obj = IPAddress.objects.get(address=row.get("IP"))
                            except IPAddress.DoesNotExist:
                                raise ValueError(f"{row.get('IP')} does not exist.")
                            # Assign the IP to the interface
                            ip_obj.assigned_object_id = lag_obj.id
                            ip_obj.assigned_object_type_id = 4
                            ip_obj.save()
                            # Sets the rest of the variables
                            lag_obj.untagged_vlan = None
                            lag_obj.tagged_vlans.clear()
                            lag_obj.mode = ""
                            self.log_info(
                                message=f"{lag_obj.name} was set to a routed port."
                            )
                        # Saves the interface changes
                        lag_obj.validated_save()
                        self.log_success(message=f"{lag_obj.name} has been updated.")
                        
                        # If Port-Channel is defined, set child interface
                        int_obj = None
                        try:
                            int_obj = Interface.objects.get(
                                Q(name=row.get("Port.1")), Q(device_id=dev_obj.id)
                            )
                            self.log_info(
                                message=f"{int_obj.name} will be updated on {dev_obj.name}."
                            )
                            int_obj.description = row.get("int desc")
                        except Interface.DoesNotExist:
                            # Media types in cabling mac need to be updated to match Nautobot media types
                            int_obj = Interface(
                                name=row.get("Port.1"),
                                device_id=dev_obj.id,
                                type=row.get("Media.1"),
                                status_id=status_obj.pk,
                                description=row.get("int desc"),
                            )
                            int_obj.validated_save()
                            self.log_success(
                                message=f"{int_obj.name} was created on {dev_obj.name}."
                            )
                        int_obj.mode = ""
                        int_obj.lag_id = lag_obj.id
                        self.log_success(
                            message=f"{int_obj.name} was set as a member of {lag_obj.name}."
                        )
                        int_obj.validated_save()

                    # If LAG is not defined
                    elif row.get("Port-Channel") is None:
                        # Retrieves the interface if it exists
                        try:
                            int_obj = Interface.objects.get(
                                Q(name=row.get("Port.1")), Q(device_id=dev_obj.id)
                            )
                            self.log_info(
                                message=f"{int_obj.name} will be updated on {dev_obj.name}."
                            )
                            int_obj.description = row.get("int desc")
                            int_obj.status_id=status_obj.pk
                        except Interface.DoesNotExist:
                            # Media types in cabling mac need to be updated to match Nautobot media types
                            int_obj = Interface(
                                name=row.get("Port.1"),
                                device_id=dev_obj.id,
                                type=row.get("Media.1"),
                                status_id=status_obj.pk,
                                description=row.get("int desc"),
                            )
                            self.log_info(
                                message=f"{int_obj.name} will be created on {dev_obj.name}."
                            )
                            int_obj.validated_save()
                        # Set mode config
                        mode = row.get("Mode")
                        int_obj.lag_id = None
                        if mode == "Pruned Trunk":
                            # Must set mode before assigning vlans
                            int_obj.mode = "tagged"
                            int_obj.save()
                            # Gets VLAN objects
                            vlan_objs = []
                            vlans = str(row.get("VLANs")).split(",")
                            for vlan in vlans:
                                # DC local VLAN
                                try:
                                    vlan_objs.append(
                                        VLAN.objects.get(
                                            vid=int(vlan), site_id=site_obj
                                        )
                                    )
                                # Fabric global VLAN
                                except VLAN.DoesNotExist:
                                    try:
                                        vlan_objs.append(
                                            VLAN.objects.get(
                                                vid=int(vlan), site_id=None
                                            )
                                        )
                                    except VLAN.DoesNotExist:
                                        raise ValueError(f"VLAN{vlan} does not exist (Ethernet Depth Pruned Trunk).")
                            # Sets tagged VLANs
                            for vlan_obj in vlan_objs:
                                int_obj.tagged_vlans.add(vlan_obj)
                            # Checks if an IP address was assigned to the interface and removes the association if present
                            try:
                                ip_obj = IPAddress.objects.get(
                                    assigned_object_id=int_obj.id
                                )
                                ip_obj.assigned_object_id = None
                                ip_obj.assigned_object_type_id = None
                                ip_obj.save()
                            except:
                                self.log_info(
                                    f"{int_obj.name} had no assigned IP to remove."
                                )
                                pass
                            # Sets the rest of the variables
                            int_obj.untagged_vlan = None
                            self.log_info(
                                message=f"{int_obj.name} was set to a pruned trunk."
                            )
                        elif mode == "Unpruned Trunk":
                            # Checks if an IP address was assigned to the interface and removes the association if present
                            try:
                                ip_obj = IPAddress.objects.get(
                                    assigned_object_id=int_obj.id
                                )
                                ip_obj.assigned_object_id = None
                                ip_obj.assigned_object_type_id = None
                                ip_obj.save()
                            except:
                                self.log_info(
                                    f"{int_obj.name} had no assigned IP to remove."
                                )
                                pass
                            # Must set mode before assigning vlans
                            int_obj.mode = "tagged-all"
                            int_obj.save()
                            # Sets the rest of the variables
                            int_obj.untagged_vlan = None
                            int_obj.tagged_vlans.clear()
                            self.log_info(
                                message=f"{int_obj.name} was set to an unpruned trunk."
                            )
                        elif mode == "Access":
                            # Checks if an IP address was assigned to the interface and removes the association if present
                            try:
                                ip_obj = IPAddress.objects.get(
                                    assigned_object_id=int_obj.id
                                )
                                ip_obj.assigned_object_id = None
                                ip_obj.assigned_object_type_id = None
                                ip_obj.save()
                            except:
                                self.log_info(
                                    f"{int_obj.name} had no assigned IP to remove."
                                )
                                pass
                            # Must set mode before assigning vlans
                            int_obj.mode = "access"
                            int_obj.save()
                            self.log_info(
                                message=f"{int_obj.name} was set to an access port."
                            )
                            # Gets VLAN object
                            vlan = str(row.get("VLANs")).split(",")
                            # If more than one VLAN is present but the port is set to access, only the first VLAN is used
                            try:
                                vlan_obj = VLAN.objects.get(
                                    vid=int(vlan[0]), site_id=site_obj
                                )
                            except VLAN.DoesNotExist:
                                try:
                                    vlan_obj = VLAN.objects.get(
                                        vid=int(vlan[0]), site_id=None
                                    )
                                except VLAN.DoesNotExist:
                                    raise ValueError(f"VLAN{vlan} does not exist. (Ethernet Access Depth)")
                            # Sets the rest of the variables
                            int_obj.tagged_vlans.clear()
                            int_obj.untagged_vlan = vlan_obj
                        elif mode == "Routed":
                            # Looks up the IP in the DB
                            try:
                                ip_obj = IPAddress.objects.get(address=row.get("IP"))
                            except IPAddress.DoesNotExist:
                                raise ValueError(f"{row.get('IP')} does not exist.")
                            # Assign the IP to the interface
                            ip_obj.assigned_object_id = int_obj.id
                            ip_obj.assigned_object_type_id = 4
                            ip_obj.save()
                            # Sets the rest of the variables
                            int_obj.untagged_vlan = None
                            int_obj.tagged_vlans.clear()
                            int_obj.mode = ""
                            self.log_info(
                                message=f"{int_obj.name} was set to a routed port."
                            )
                        # Saves the interface changes
                        int_obj.validated_save()
                        self.log_success(message=f"{int_obj.name} has been saved.")

###

class DCNDeployNetworks(Job):
    # Template includes javascript to hide and reveal fabric switch groups which is only used for EVPN.
    template_name = "NautobotPluginTest/network_creation.html"

    # Job metadata
    class Meta:
        name = "Deploy a New Network"
        hidden = False
        description = "Deploy a new network in nautobot."
        field_order = ["tenant", "sites", "vid", "vlan_name", "vlan_role", "prefix", "prefix_vrf", "dhcp", "fabric_switch_groups"]

    # Form fields
    tenant = ObjectVar(model=Tenant, display_field="name", label="Tenant:", 
                       required=True)
    sites = MultiObjectVar(model=Site, query_params={"tenant_id": "$tenant"}, display_field="name", label="Sites:", 
                     required=True)
    vid = IntegerVar(min_value=2, max_value=4093, label="Vlan ID:", 
                     required=True)
    vlan_name = StringVar(min_length=1, max_length=32, 
                          required=True)
    vlan_role = ObjectVar(model=Role, display_field="name", label="VLAN Role:", 
                          required=True)
    prefix = IPNetworkVar(label="Prefix:", required=True)
    prefix_vrf = ObjectVar(model=VRF, query_params={"tenant_id": "$tenant"}, display_field="name", label="Prefix VRF:", 
                           required=True)
    dhcp = BooleanVar(default=True, label="DHCP", required=True)
    fabric_switch_groups = MultiObjectVar(model=Tag, query_params={"name__ic": "VLAN"}, display_field="name", label="Switch Groups:",
                                          required=False)

    
    # Class for working with existing ORM objects
    class orm_object:
        def __init__(self, model_name, app_name, pks):
            self.objs = []
            model = apps.get_model(app_name, model_name)
            # For each item in the provided list if the list item is not None
            gen_exp = (id for id in pks if id is not None)
            for id in gen_exp:
                self.objs.append(model.objects.get(pk=id))
            # Add a none object with a pk of None to the list
            if pks[0] is None:
                obj = self.none_object()
                self.objs.append(obj)

        def __str__(self):
            # A single object was passed
            if len(self.objs) == 1:
                return self.objs[0].name
            # More than one object was passed
            else:
                obj_names = [f"{obj.name}" for obj in self.objs]
                return ', '.join(obj_names)
            
        # Nested class for making up None objects
        class none_object:
            def __init__(self):
                self.pk = None
                self.name = None
            def __str__(self):
                return self.pk

    def run(self, data, commit):
        # Accept data and commit from form
        self.data = data
        self.commit = commit

        # Other required objects
        status = Status.objects.get(name="Active")

        # Capture required variables
        tenant = self.orm_object("Tenant", "tenancy", [self.data["tenant"].id])
        self.log_info(f"{tenant} tenant")

        # Sites must be filled out, if for all sites all 3 must be defined.
        sites = self.orm_object("Site", "dcim", [site.id for site in self.data["sites"]] if self.data["sites"] is not None else [None])
        self.log_info(f"{sites} sites")

        vid = self.data["vid"]
        self.log_info(f"{vid} VID")

        vlan_name = self.data['vlan_name']
        self.log_info(f"{vlan_name} Vlan Name")

        vlan_role = self.orm_object("Role", "ipam", [self.data['vlan_role'].id])
        self.log_info(f"{vlan_role} Vlan Role")

        prefix = self.data["prefix"]
        self.log_info(f"{prefix} Prefix")

        prefix_vrf = self.orm_object("VRF", "ipam", [self.data["prefix_vrf"].id])
        self.log_info(f"{prefix_vrf} Prefix VRF")

        dhcp = self.data["dhcp"]
        self.log_info(f"Is DHCP enabled? {dhcp}")

        # Capture Optional Variables
        if len(self.data["fabric_switch_groups"]) >= 1:
            # Creates switch_groups class member with all of the tag PKs
            switch_groups = self.orm_object("Tag", "extras", [group.id for group in self.data["fabric_switch_groups"]])
            self.log_info(f"{switch_groups} Switch Groups")
        else:
            # Creates switch_groups class member with a none 0 index element
            switch_groups = self.orm_object("Tag", "extras", [None])    

        # If more than one site is assigned, assign the vlan globally (no site)
        if len(sites.objs) >= 2:
            vlan_site = None
        # If exactly 1 site is assigned, assign to that site only
        elif len(sites.objs) == 1:
            vlan_site = sites.objs[0]
        # If switch group tags had no selections
        if switch_groups.objs[0].pk == None:
            tag_list = []
        # If switch group tags had at least 1 selection
        else:
            tag_list = [obj.pk for obj in switch_groups.objs]

        # Check if VLAN already exist
        vlan_vid = VLAN.objects.filter(vid=vid).values_list('pk', flat=True)
        if len(vlan_vid) >= 1:
            self.log_failure(f"{vid} already exists.")
        # Otherwise create the VLAN
        else:
            self.log_info("VLAN creation...")
            # build vlan object    
            vlan_obj = VLAN(
                name=vlan_name,
                vid=vid,
                site=vlan_site,
                tenant=tenant.objs[0],
                status=status,
                role=vlan_role.objs[0],
                description=vlan_name,
                tags=tag_list
            )
            # save vlan object to DB
            vlan_obj.validated_save()
            self.log_success(message=f"{vlan_obj.name} has been saved.")

        # Checks if prefix already exists   
        prefix_id = Prefix.objects.filter(prefix=prefix).values_list('pk', flat=True)
        if len(prefix_id) >= 1:
            self.log_failure(f"{prefix} already exists.")

        # Otherwise, create the Prefix
        else:
            # build prefix object
            prefix_obj = Prefix(
                prefix=prefix,
                vrf=prefix_vrf.objs[0],
                site=vlan_site,
                tenant=tenant.objs[0],
                vlan=vlan_obj,
                is_pool=dhcp,
                description=vlan_name,
                role=vlan_role.objs[0],
                status=status,
            )

            # save prefix object to DB
            prefix_obj.validated_save()
            self.log_success(message=f"{prefix_obj.prefix} has been saved.")

jobs = [DCNUpdateDeviceInterfaces, DCNDeployNetworks, DCNBulkUpdateInterfaces]
