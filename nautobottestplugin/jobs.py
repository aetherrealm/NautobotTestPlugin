# jobs.py

import json

from django.apps import apps
from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.ipam.models import IPAddress, Role
from nautobot.dcim.models import Site, Region
from nautobot.extras.models import Tag
from nautobot.extras.jobs import Job, IntegerVar, StringVar, ObjectVar, MultiObjectVar

class CreateVLANs(Job):
    template_name = "NautobotPluginTest/test_template.html"

    class Meta:
        name = "CreateVLANs"
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

    tags = MultiObjectVar(model=Tag, display_field="name")

    gateway_ip = ObjectVar(model=IPAddress, display_field="address", required=False)

    vlan_role = ObjectVar(model=Role, display_field="name")

    def run(self, data, commit):
        self.log_success(message=self.gateway_ip)

jobs = [CreateVLANs]
