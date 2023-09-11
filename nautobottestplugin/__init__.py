from nautobot.apps import NautobotAppConfig

class NautobotTestPlugin(NautobotAppConfig):
    name = "nautobottestplugin"
    verbose_name = "Test Plugin"
    description = "A test description."
    version = "1.0.0"
    author = "Michael Cote"
    base_url = "nautobottestplugin"
    required_settings = []
    default_settings = {"loud": False}

config = NautobotTestPlugin