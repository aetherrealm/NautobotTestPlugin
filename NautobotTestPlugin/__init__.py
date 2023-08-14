from nautobot.apps import NautobotAppConfig

class TestPlugin(NautobotAppConfig):
    name = "NautobotTestPlugin"
    verbose_name = "Test Plugin"
    description = "A test description."
    version = "0.1"
    author = "Michael Cote"
    base_url = "test-plugin"
    required_settings = []
    default_settings = {"loud": False}

config = TestPlugin