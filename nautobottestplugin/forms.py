# forms.py
from django import forms
from nautobot.ipam.models import IPAddress, VLAN, VRF, Role, Prefix
from nautobot.dcim.models import Site
from nautobot.extras.models import Tag
from nautobot.utilities.forms import BootstrapMixin

class AddVlanForm1(BootstrapMixin, forms.Form):
    VlanSite = forms.ModelChoiceField(queryset=Site.objects.all(), label="Deploy VLAN to which site?")

class AddVlanForm2(BootstrapMixin, forms.Form):
    VlanID = forms.IntegerField(min_value=1, max_value=4096)
    VlanType = forms.ModelChoiceField(queryset=Role.objects.all(), required=True)
    VlanTagGroup = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=True)
    VlanGateway = forms.BooleanField(initial=True, required=True, label="Gateway Provided?")
    VlanGatewayIP = forms.ModelChoiceField(queryset=IPAddress.objects.filter(role="anycast"))


