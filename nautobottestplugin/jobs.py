# jobs.py

import json
import pandas as pd
import numpy as np

from django.apps import apps
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError
from django.db.models import Q

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.ipam.models import IPAddress, Role, VLAN
from nautobot.dcim.models import Site, Region, Device, Interface
from nautobot.extras.models import Tag, Status
from nautobot.extras.jobs import (
    Job,
    IntegerVar,
    StringVar,
    ObjectVar,
    MultiObjectVar,
    ChoiceVar,
    FileVar
)


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
        model=Status, display_field="name", label="Status:", query_params={"name":["Active","Shutdown"]}, required=False
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

class BulkUpdateInterfaces(Job):

    class Meta:
        name = "Bulk Update Interfaces"
        hidden = False
        description = "Imports a Cabling Mac into Nautobot to bulk update interfaces."

    cabling_mac = FileVar(label = "Upload Cabling MAC", description="Cabling MAC interface bulk import")

    def run(self, data, commit):
    # Accept data and commit
        self.commit = commit
        # Accept in the Cabling MAC XLSX, target the Cabling sheet, and ignore the first row
        mac = pd.read_excel(data["cabling_mac"], sheet_name="Cabling", header=1)
        # Replace the nan values with None instead for logic checking
        mac = mac.replace(np.nan, None)
        # Convert the sheet into a dictionary where each dictionary item represents a row
        mac = mac.to_dict(orient='records')
        # Get status UUID
        for status in Status.objects.all():
            if status.name == "Active":
                status_obj = status

        # For each row in the cabling mac
        for row in mac:
            # Does the device exist in Nautobot
            try:
                dev_obj = Device.objects.get(name=row.get('Device.1'))
                #### If LAG is defined
                if row.get('Port-Channel') is not None:
                    # Retrieves the interface if it exists
                    try:
                        lag_obj = Interface.objects.get(Q(name=row.get('Port-Channel')), Q(device_id=dev_obj.id))
                        self.log_info(message=f"{lag_obj.name} already exists. Ignoring description and mode settings.")
                    # LAG doesn't exist, creating
                    except:
                        self.log_info(message=f"{int_obj.name} will be created on {dev_obj.name}.")
                        lag_obj = Interface(name=row.get('Port-Channel'), device_id=dev_obj.id, type='lag', mode=row.get('Mode'),
                                        status_id = status_obj.pk, description=row.get('Port-Channel Name'))
                        lag_obj.validated_save()
                # Retrieves the interface if it exists
                try:
                    int_obj = Interface.objects.get(Q(name=row.get('Port.1')),Q(device_id=dev_obj.id))
                    self.log_info(message=f"{int_obj.name} will be updated on {dev_obj.name}.")
                    int_obj.description = row.get('int desc')

                    ###int_obj.lag_id = lag_obj.id

                # Interface doesn't exist, creating
                except:
                    self.log_info(message=f"{int_obj.name} will be created on {dev_obj.name}.")
                # Retrieves the interface description if it's filled out
                try:
                    int_desc = row.get('int desc')
                # Creates a concatenated interface description if the above doesn't exist
                except:
                    int_desc = row.get('Device')+":"+row.get('Port')



            # Device doesn't exist, goes to the next line            
            except:
                self.log_warning(message=f"{row.get('Device.1')} does not exist in Nautobot.")

# class DeployNewNetwork(Job):
#     class Meta:
#         name = "Deploy New Non-Fabric Network"
#         hidden = False
#         description = "Deploy a Non-Fabric Network"


class CreateVLANs(Job):
    # template_name = "NautobotPluginTest/test_template.html"

    class Meta:
        name = "Deploy New VLAN"
        hidden = False
        description = "Test VLAN add Job"
        field_order = ["vid", "vlan_desc", "vlan_role", "gateway_ip"]

    vid = IntegerVar(description="VLAN ID")

    vlan_desc = StringVar()

    ## region = ObjectVar(model=Region, display_field="name")

    # site = ObjectVar(model=Site, display_field="name")

    # tenant_group = ObjectVar(model=TenantGroup, display_field="name")

    # tenant = ObjectVar(model=Tenant, display_field="name")

    # tags = MultiObjectVar(model=Tag, display_field="name", label="Where should this VLAN apply?")

    gateway_ip = ObjectVar(
        model=IPAddress,
        display_field="address",
        required=False,
        label="What is the gateway IP?",
    )

    vlan_role = ObjectVar(model=Role, display_field="name")

    def run(self, data, commit):
        self.log_success(message=self.gateway_ip)


jobs = [DCNUpdateDeviceInterfaces, CreateVLANs, BulkUpdateInterfaces]
