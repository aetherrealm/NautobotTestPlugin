# urls.

from django.urls import path
from nautobottestplugin import views

urlpatterns = [
    path('dcn-home/', views.Wizards.as_view(), name="dcn_home"),
]