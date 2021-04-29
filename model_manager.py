from prometheus_client import Gauge
import logging
import prophet as model
import pickle
from datetime import datetime
from model_factory import ModelFactory
import numpy as np

logging.basicConfig(level=logging.DEBUG)


class ModelManager:

    def __init__(self, conf, storage, pc, init=True, no_train_mode=False):
        self.init = init
        self.configuration = conf
        self.storage = storage
        self.model_list = []
        self.gauge_dict = dict()
        self.pc = pc
        self.executed_activities = {}
        self.reports = {}
        self.factory = ModelFactory()
        if not no_train_mode:
            self.load_predictor_models()
            self.retrain_models()

    def load_predictor_models(self):

        for metric in self.configuration.get("prometheus_metric_list"):
            metric_init = self.pc.get_current_metric_value(metric_name=metric["metric_query"])
            for unique_metric in metric_init:
                if 'models' in metric:
                    model_to_apply = metric['models']
                else:
                    model_to_apply = [{'kind': 'prophet'}]
                logging.info(model_to_apply)
                for md in model_to_apply:
                    args = None
                    if 'args' in md.keys():
                        args = md['args']
                    self.model_list.append(
                        self.factory.create(
                            kind=md['kind'],
                            metric=unique_metric,
                            metric_predicted_name=metric["predicted_metric_name"] + "_" + md['kind'],
                            rolling_data_window_size=self.configuration.get_retrain_window(),
                            prophet_conf=self.configuration.get("prophet_configuration"),
                            args=args
                        )
                    )
                    report_name = metric["predicted_metric_name"] + "_" + md['kind']
                    if report_name not in self.reports.keys():
                        self.reports[report_name] = self.init_report()

        logging.info("Predictor model list loaded..")
        logging.info("Count of predictors models.. {0}".format(len(self.model_list)))
        for predictor in self.model_list:
            unique_metric = predictor.metric
            label_list = list(unique_metric.label_config.keys())
            label_list.append("value_type")
            if predictor.metric_predicted_name not in self.gauge_dict:
                self.gauge_dict[predictor.metric_predicted_name] = Gauge(
                    predictor.metric_predicted_name,
                    predictor.model_description,
                    label_list,
                )
        logging.info("Predictor Gauge Dict created..")

    def get_initial_time(self):
        start_time = datetime.now() - self.configuration.get_metric_chunk()
        if self.init:
            start_time = datetime.now() - self.configuration.get_retrain_window()
            self.init = False
        return start_time

    def clean_lock(self):
        self.executed_activities = {}

    def create_predictor_lock(self, name):
        self.executed_activities[name] = True

    def get_predictor_lock(self, name):
        if name in self.executed_activities.keys():
            return self.executed_activities[name]
        return False

    def get_all_predictor_locks(self):
        return self.executed_activities

    def retrain_models(self):
        self.clean_lock()
        for predictor in self.model_list:
            metric_to_predict = predictor.metric
            metric_start_time = self.get_initial_time()
            new_metric = self.pc.get_metric_range_data(
                metric_name=metric_to_predict.metric_name,
                label_config=metric_to_predict.label_config,
                start_time=metric_start_time,
                end_time=datetime.now()
            )
            if len(new_metric) == 0:
                continue
            new_metric = new_metric[0]
            start_time = datetime.now()
            predictor.train(
                metric_data=new_metric,
                prediction_duration=int(self.configuration.get("retrain_scheduling_seconds"))
            )

            logging.info(
                "Total Training time taken = %s, for metric: %s %s",
                str(datetime.now() - start_time),
                metric_to_predict.metric_name,
                metric_to_predict.label_config
            )

        self.storage.set(self.configuration.model_list_field, pickle.dumps(self.model_list))
        self.storage.set(self.configuration.report_list_field, pickle.dumps(self.reports))

    def get_gauge_dict(self):
        return self.gauge_dict

    def set_gauge_dict(self, gauge_dict):
        self.gauge_dict = gauge_dict
        return self

    def clean_reports(self):
        for report_name in self.reports.keys():
            self.reports[report_name] = self.init_report()
        self.storage.set(self.configuration.report_list_field, pickle.dumps(self.reports))

    def init_report(self):
        return {
            'report': {
                'count': 0,
                'anomaly_count': 0,
                'point_error_media': 0,
                'total_yhat': 0,
                'total_cur_value': 0
            },
        }

    def get_reports(self):
        return pickle.loads(self.storage.get(self.configuration.report_list_field))

    def report(self, name, cur_value, predicted_value, anomaly):
        reports = self.get_reports()
        reports[name]['report']['count'] += 1
        reports[name]['report']['anomaly_count'] += anomaly
        reports[name]['report']['point_error_media'] += (cur_value - predicted_value["yhat"][0]) / 2
        reports[name]['report']['total_yhat'] += predicted_value["yhat"][0]
        reports[name]['report']['total_cur_value'] += cur_value
        self.storage.set(self.configuration.report_list_field, pickle.dumps(reports))
