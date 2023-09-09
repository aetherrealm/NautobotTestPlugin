# jobs.py

import json

from django.apps import apps
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.ipam.models import IPAddress, Role, VLAN
from nautobot.dcim.models import Site, Region, Device, Interface
from nautobot.extras.models import Tag, Status
from nautobot.extras.jobs import Job, IntegerVar, StringVar, ObjectVar, MultiObjectVar, ChoiceVar

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
            "mode",
            "IP",
            "untagged_vlan",
            "tagged_vlans"
        ]
    
    device = ObjectVar(model=Device, display_field="name", label="Device:")
    interface = ObjectVar(model=Interface, display_field="name", query_params={'device_id':'$device'}, label="Interface:")
    interface_status = ObjectVar(model=Status, display_field="name", label="Status:")
    interface_desc = StringVar(default="device:port")
    mode = ChoiceVar(choices=(("",""),("access","Access"), ("pruned_trunk", "Pruned Trunk"), 
                              ("unpruned_trunk", "Unpruned Trunk"), ("routed", "Routed")))
    IP = ObjectVar(model=IPAddress, display_field="address", label="IP:", required=False)
    untagged_vlan = ObjectVar(model=VLAN, display_field="vid", label="Untagged VLAN:", required=False)
    tagged_vlans = MultiObjectVar(model=VLAN, display_field="vid", label="Tagged VLANs:", required=False)

    def run(self, data, commit):
        # Accept data and commit
        self.data = data
        self.commit = commit
        # Establish required variables from form
        self.status_id = self.data['interface_status'].id
        self.device_id = self.data['device'].id
        self.interface_id = self.data['interface'].id
        self.interface_desc = self.data['interface_desc']
        self.interface_mode = self.data['mode']
        # Updates port to Routed mode (interface to the IP in the database)
        if self.data['IP'] is not None and self.data['mode'] == "routed":
            # Gets the PK of the IP from the form
            self.ip_id = self.data['IP'].id
            # Looks up the IP in the DB
            ip_obj = IPAddress.objects.get(pk=self.ip_id)
            # Assign the IP to the interface
            ip_obj.assigned_object_id = self.interface_id
            ip_obj.assigned_object_type_id = 4
            ip_obj.save()
            # Looks up the Interface in the DB
            int_obj = Interface.objects.get(pk=self.interface_id)
            # Sets the rest of the variables
            int_obj.mode = ''
            int_obj.status_id = self.status_id
            int_obj.untagged_vlan_id = None
            int_obj.tagged_vlans.clear()
            int_obj.description = self.interface_desc
            int_obj.save()
            self.log_info(f"IP:{self.ip_id}")
        # Updates port to Access mode
        if self.data['untagged_vlan'] is not None and self.data['mode'] == "access":
            # Gets the PK of the untagged vlan from the form
            self.untagged_vlan_id = self.data['untagged_vlan'].id
            # Checks if an IP address was assigned to the interface and removes the association if present
            try:
                ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                ip_obj.assigned_object_id = None
                ip_obj.assigned_object_type_id = None
                ip_obj.save()
            except:
                pass
            # Looks up the Interface in the DB
            int_obj = Interface.objects.get(pk=self.interface_id)
            # Mode must be set before untagged_vlan can be added
            int_obj.mode = 'access'
            int_obj.save()
            # Sets the rest of the variabes
            int_obj.status_id = self.status_id
            int_obj.tagged_vlans.clear()
            int_obj.untagged_vlan_id = self.untagged_vlan_id
            int_obj.description = self.interface_desc
            int_obj.save()
            self.log_info(f"Untagged_VLAN:{self.untagged_vlan_id}")
        # Updates port to Pruned Trunk
        if self.data['tagged_vlans'] is not None and self.data['mode'] == "pruned_trunk":
            # Checks if an IP address was assigned to the interface and removes the association if present
            try:
                ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                ip_obj.assigned_object_id = None
                ip_obj.assigned_object_type_id = None
                ip_obj.save()
            except:
                pass
            # Gets the PKs of the tagged vlans from the form
            self.tagged_vlans_ids = [vlan.id for vlan in self.data['tagged_vlans']]
            # Looks up the Interface in the DB
            int_obj = Interface.objects.get(pk=self.interface_id)
            # Mode must be set before tagged_vlans can be added
            int_obj.mode = 'tagged'
            int_obj.save()
            # Gets VLAN objects
            vlan_objs = []
            for vlan in self.tagged_vlans_ids:
                vlan_objs.append(VLAN.objects.get(pk=vlan))
            # Sets tagged VLANs
            for vlan_obj in vlan_objs:
                int_obj.tagged_vlans.add(vlan_obj)
            # Sets the rest of the variabes
            
            int_obj.status_id = self.status_id
            int_obj.untagged_vlan_id = None
            int_obj.description = self.interface_desc
            int_obj.save()
            self.log_info(f"Tagged_VLANs:{self.tagged_vlans_ids}")
        # Updates port to Unpruned Trunk
        if self.data['mode'] == "unpruned_trunk":
            # Checks if an IP address was assigned to the interface and removes the association if present
            try:
                ip_obj = IPAddress.objects.get(assigned_object_id=self.interface_id)
                ip_obj.assigned_object_id = None
                ip_obj.assigned_object_type_id = None
                ip_obj.save()
            except:
                pass
            # Looks up the Interface in the DB
            int_obj = Interface.objects.get(pk=self.interface_id)
            # Sets the rest of the variabes
            int_obj.mode = 'tagged-all'
            int_obj.status_id = self.status_id
            int_obj.tagged_vlans.clear()
            int_obj.untagged_vlan_id = None
            int_obj.description = self.interface_desc
            int_obj.save()
            self.log_info(f"{self.data['interface']} has been set to an unpruned trunk.")
        # if commit:

        #     self.debug = data["debug"]
        # else:
        #     self.log_failure(message="Nothing commited.")


# class DeployNewNetwork(Job):
#     class Meta:
#         name = "Deploy New Non-Fabric Network"
#         hidden = False
#         description = "Deploy a Non-Fabric Network"

class CreateVLANs(Job):
    #template_name = "NautobotPluginTest/test_template.html"

    class Meta:
        name = "Deploy New VLAN"
        hidden = False
        description = "Test VLAN add Job"
        field_order = [
            "vid",
            "vlan_desc",
            "vlan_role",
            "gateway_ip"
        ]

    vid = IntegerVar(description="VLAN ID")

    vlan_desc = StringVar()

    # region = ObjectVar(model=Region, display_field="name")

    # site = ObjectVar(model=Site, display_field="name")

    # tenant_group = ObjectVar(model=TenantGroup, display_field="name")

    # tenant = ObjectVar(model=Tenant, display_field="name")

    # tags = MultiObjectVar(model=Tag, display_field="name", label="Where should this VLAN apply?")

    gateway_ip = ObjectVar(model=IPAddress, display_field="address", required=False, label="What is the gateway IP?")

    vlan_role = ObjectVar(model=Role, display_field="name")

    def run(self, data, commit):
        self.log_success(message=self.gateway_ip)

jobs = [DCNUpdateDeviceInterfaces, CreateVLANs]
