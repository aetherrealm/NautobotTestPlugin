# views.py
from django.shortcuts import render
from nautobot.apps.views import NautobotUIViewSet
from django.views.generic import View

class Wizards(View):
    def get(self, request):
        return render(request, 'NautobotPluginTest/plugin_home.html')