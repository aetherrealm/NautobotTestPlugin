# urls.

from django.urls import path

from nautobottestplugin.forms import AddVlanForm1, AddVlanForm2
from nautobottestplugin.views import VLANWizard

urlpatterns = [
    path('test-plugin/add-vlan/', VLANWizard.as_view([AddVlanForm1, AddVlanForm2])),
]