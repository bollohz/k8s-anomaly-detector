from flask import jsonify, Response
from prometheus_api_client import Metric
from prometheus_client import Gauge, generate_latest, REGISTRY
from datetime import datetime
import logging
import pickle
import threading
import yaml
import subprocess
import os
import numpy as np
import boto3
import modules
import inspect

logging = logging.getLogger(__name__)


class RequestHandler:

    def __init__(self, conf, pc, model_manager, scheduler):
        self.configuration = conf
        self.model_manager = model_manager
        self.storage = model_manager.storage
        self.scheduler = scheduler
        self.pc = pc

    def root_route(self):
        returned_data = {
            'status': 'green',
            'version': 'v1alpha'
        }
        return jsonify(returned_data)

    def locks_route(self):
        locks = self.model_manager.get_all_predictor_locks()
        returned_data = {
            'locks': locks,
            'init_start': self.model_manager.init
        }
        return jsonify(returned_data)

    def calculate_rate(self, reports):
        for model in reports:
            report = reports[model]['report']
            if report['count'] > 0:
                report["rmse"] = np.sqrt(((report['total_yhat'] - report['total_cur_value']) / report['count']) ** 2)
                report["err_percentage"] = np.sqrt((report['anomaly_count'] * (1 - report['anomaly_count'])) / report['count'])
                report["anomaly_count"] = report['anomaly_count']
        return reports

    def reports_route(self):
        reports = self.model_manager.get_reports()
        reports = self.calculate_rate(reports)
        returned_data = {
            'data': reports
        }
        return jsonify(returned_data)

    def send_reports(self, call=False):
        reports = self.model_manager.get_reports()
        reports = self.calculate_rate(reports)
        mail_text = ""
        for model in reports:
            mail_text += " Model {0} as an RMSE of {1}, with an error rate of {2} on {3} anomaly counted \n".format(
                    model,
                    reports[model]["report"]["rmse"],
                    reports[model]["report"]["err_percentage"],
                    reports[model]["report"]["anomaly_count"]
                )
        self.model_manager.clean_reports()
        sns = boto3.client('sns')
        response = sns.publish(
            TopicArn=self.configuration.get("topic_arn"),
            Message=mail_text,
            Subject='k8s-anomaly-detector Model Report'
        )
        if call:
            return jsonify(response)


    def scheduled_activities(self):
        jobs = []
        for j in self.scheduler.get_jobs():
            job = {
                'name': j.name,
                'func_ref': j.func_ref,
                'id': j.id,
                'next_run': j.next_run_time
            }
            jobs.append(job)
        return jsonify(jobs)

    def anomaly_detection(self, val_current, prediction):
        # Calculate for an anomaly (can be different for different models)
        anomaly = True
        if (val_current < prediction["yhat_upper"][0]) \
                and (val_current > prediction["yhat_lower"][0]):
            anomaly = False
        return anomaly

    def manage_activity(self, manage_activity_name):
        logging.info("Starting functions for {0} ".format(manage_activity_name))
        if not self.model_manager.get_predictor_lock(manage_activity_name):
            # Do activities
            with open(self.configuration.activity_conf_file, 'r') as af:
                activities = yaml.safe_load(af)
            activity = [d for d in activities['activities'] if d['name'] == manage_activity_name]
            logging.info("ACTIVITY {0}".format(activity))
            if len(activity) == 1:
                self.model_manager.create_predictor_lock(manage_activity_name)
                logging.info("Create lock for {0} ".format(manage_activity_name))
                activity = activity[0]
                if "shell_file" in activity['command']:
                    sh = os.path.abspath(os.getcwd()) + self.configuration.commands_root_folder + activity["command"][
                        "shell_file"]
                    args = ""
                    if "args" in activity["command"]:
                        args = activity["command"]["args"]
                    try:
                        p = subprocess.run(
                            [sh, args],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        logging.info("command return {0}".format(p.returncode))
                    except:
                        pass
                elif "python_script" in activity["command"]:
                    logging.info("Need to implement management for custom python scripts...")
                    pass

    def metrics_route(self):
        model_list = self.storage.get(self.configuration.model_list_field)
        model_list = pickle.loads(model_list)
        for predictor in model_list:
            logging.info("Predictor is {0},{1}".format(predictor.metric.metric_name, predictor.metric.label_config))
            current_metric = self.pc.get_current_metric_value(
                metric_name=predictor.metric.metric_name,
                label_config=predictor.metric.label_config
            )
            if len(current_metric) == 0:
                continue
            current_metric_data = Metric(
                current_metric[0]
            )
            predict = predictor.predict_value(datetime.now())
            gauges = self.model_manager.get_gauge_dict()
            for col in list(predict.columns):
                gauges[predictor.metric_predicted_name].labels(
                    **predictor.metric.label_config, value_type=col
                ).set(predict[col][0])
            anomaly = 0
            if self.anomaly_detection(
                    current_metric_data.metric_values["y"][0],
                    predict
            ):
                th = threading.Thread(target=self.manage_activity(predictor.metric_predicted_name))
                anomaly = 1
                th.start()
            gauges[predictor.metric_predicted_name].labels(
                **predictor.metric.label_config, value_type="anomaly"
            ).set(anomaly)
            self.model_manager.report(
                name=predictor.metric_predicted_name,
                cur_value=current_metric_data.metric_values["y"][0],
                predicted_value=predict,
                anomaly=anomaly
            )
        return Response(generate_latest(REGISTRY).decode("utf-8"), content_type='text; charset=utf-8')

    def job_dashboard_metrics_route(self):
        classes = [name for name, obj in inspect.getmembers(modules) if inspect.isclass(obj) and name != 'AbstractModule']
        for custom_classes in classes:
            class_ = getattr(modules, custom_classes)
            instance = class_()  # type:AbstractModule
            instance.execute()
        return Response(generate_latest(REGISTRY.register('job_dashboard_result')).decode("utf-8"), content_type='text; charset=utf-8')
