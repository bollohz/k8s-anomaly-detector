import yaml
import boto3
from boto3 import dynamodb
from modules.abstract_module import AbstractModule
from prometheus_client import Gauge, REGISTRY, CollectorRegistry


class JobDashboardModule(AbstractModule):
    configuration_file_name: str
    configuration_variables: list
    configuration_labels: list

    def __init__(self):
        super().__init__()
        self.configuration_file_name = "/job_dashboard_module.yaml"
        self.configuration_variables = {}
        self.gauge_dict = {}
        self.configuration_labels = [
            "Id",
            "Result"
        ]
        self.get_module_configuration()

    def get_module_configuration(self):
        configuration_path = self.conf_base_path + self.configuration_file_name
        with open(configuration_path, "r") as f:
            env = yaml.safe_load(f)
        env = env['configuration_variables']
        for var in env:
            self.configuration_variables[var['name']] = var['value']

    def get_client_instance(self) -> boto3.dynamodb:
        return boto3.resource(
            service_name='dynamodb',
            region_name=self.configuration_variables['region']
        )

    def get_items(self) -> list:
        ddb_client = self.get_client_instance()
        ddb_table = ddb_client.Table(self.configuration_variables["dynamo_db_table"])
        return ddb_table.scan()['Items']

    def execute(self) -> {Gauge}:
        items = self.get_items()
        gauge_dict = {}
        gauge_string = "job_dashboard_result"
        registry_names = REGISTRY._names_to_collectors.keys()
        if gauge_string in registry_names:
            REGISTRY.unregister(REGISTRY._names_to_collectors[gauge_string])
        metric = Gauge(
            gauge_string,
            'Job Dashboard metrics',
            registry=REGISTRY,
            labelnames=['id']
        )
        for item in items:
            item_value = 0  # it means SUCCESS
            if item['Result'] != "SUCCESS":
                item_value = 1.0
            gauge_dict[item['Id']] = metric.labels(item['Id']).set(item_value)
        return gauge_dict
