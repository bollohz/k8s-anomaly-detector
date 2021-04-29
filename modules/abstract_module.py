import os
from abc import ABC
from prometheus_client import Gauge


class AbstractModule(ABC):
    configuration_file_name: str
    conf_base_path: str
    configuration_variables: list

    def __init__(self):
        self.configuration_file_name = ""
        self.conf_base_path = os.path.curdir + "/conf/modules"

    def get_module_configuration(self):
        pass

    @classmethod
    def execute(self):
        raise Exception("Execute method need to be implemented")
