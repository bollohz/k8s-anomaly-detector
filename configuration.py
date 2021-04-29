import os
import yaml
import logging
from prometheus_api_client.utils import parse_datetime, parse_timedelta
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)


def respect_schema(env, version="v1alpha"):
    return True


class Configuration:

    def __init__(self):
        self.activity_conf_file = os.path.curdir + "/conf/activities.yaml"
        self.commands_root_folder = "/conf/commands/"
        self.model_list_field = "model_list"
        self.report_list_field = "report_list"
        self.model_manager_field = "model_manager_instance"

        with open(os.path.join(os.path.curdir, "conf/environment.yaml"), "r") as f:
            env = yaml.safe_load(f)

        if not respect_schema(env):
            logging.info("Schema not respected.. please provide correct information")
            exit(1)

        self.environment = env

    def get(self, elem):
        return self.environment[elem]

    def get_retrain_window(self):
        return parse_timedelta(
            "now",
            self.get("retrain_window")
        )

    def get_prometheus_header(self):
        if self.get("prometheus_token") != "":
            return {
                "Authorization": "bearer " + self.get("prometheus_token")
            }
        return {}

    def get_metric_chunk(self):
        return parse_timedelta("now", self.get("retrain_chunk_size"))

    def get_retrain_window_seconds(self):
        retrain_window = self.get("retrain_window")
        seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return int(retrain_window[:-1]) * seconds_per_unit[retrain_window[-1]]

    def get_report_window_second(self):
        retrain_window = self.get("report_window")
        seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return int(retrain_window[:-1]) * seconds_per_unit[retrain_window[-1]]