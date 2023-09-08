# jobs.py

import json

from django.apps import apps
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.ipam.models import IPAddress, Role, VLAN
from nautobot.dcim.models import Site, Region, Device, Interface
from nautobot.extras.models import Tag
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
            "interface_desc",
            "mode",
            "IP",
            "untagged_vlan",
            "tagged_vlans"
        ]
    device = ObjectVar(model=Device, display_field="name", label="Device:")
    interface = ObjectVar(model=Interface, display_field="name", query_params={'device_id':'$device'}, label="Interface:")
    interface_desc = StringVar(default="device:port")
    mode = ChoiceVar(choices=(("",""),("access","access"), ("trunked", "trunked"), ("routed", "routed")))
    IP = ObjectVar(model=IPAddress, display_field="address", label="IP:")
    untagged_vlan = ObjectVar(model=VLAN, display_field="vid", label="Untagged VLAN:")
    tagged_vlans = MultiObjectVar(model=VLAN, display_field="vid", label="Tagged VLANs:")
    
    def run(self, data, commit):
        self.log_success(message=self.device)

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
            "tenant_group",
            "tenant",
            "region",
            "site",
            "vlan_role",
            "gateway_ip",
            "tags"
        ]

    vid = IntegerVar(description="VLAN ID")

    vlan_desc = StringVar()

    region = ObjectVar(model=Region, display_field="name")

    site = ObjectVar(model=Site, display_field="name")

    tenant_group = ObjectVar(model=TenantGroup, display_field="name")

    tenant = ObjectVar(model=Tenant, display_field="name")

    tags = MultiObjectVar(model=Tag, display_field="name", label="Where should this VLAN apply?")

    gateway_ip = ObjectVar(model=IPAddress, display_field="address", required=False, label="What is the gateway IP?")

    vlan_role = ObjectVar(model=Role, display_field="name")

    def run(self, data, commit):
        self.log_success(message=self.gateway_ip)

jobs = [DCNUpdateDeviceInterfaces, CreateVLANs]
