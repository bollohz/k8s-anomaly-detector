from flask import Flask
from configuration import Configuration
from model_manager import ModelManager
from request_handler import RequestHandler
from prometheus_api_client import PrometheusConnect
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client import Gauge, REGISTRY, CollectorRegistry
import logging
import redis
import atexit

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Set up logging
logging.basicConfig(level=logging.DEBUG)
# Set up configuration class
conf = Configuration()

sentry_sdk.init(
    dsn=conf.get('sentry_dns'),
    integrations=[FlaskIntegration()]
)

app = Flask(__name__)

# Set up Redis
store = redis.StrictRedis(
    host=conf.get("redis_host"),
    port=conf.get("redis_port")
)

logging.info(store.info())
logging.info("check status of redis passed..")
logging.info(conf.get('no_train_mode'))
if conf.get('no_train_mode'):
    pc = None
else:
    pc = PrometheusConnect(
        url=conf.get("prometheus_url"),
        headers=conf.get_prometheus_header(),
        disable_ssl=True,
    )

# Set up Model Manager
model_manager = ModelManager(conf=conf, storage=store, pc=pc, no_train_mode=conf.get('no_train_mode'))

# Set up Scheduler
scheduler = BackgroundScheduler()

# Set up Request Handler
request_handler = RequestHandler(conf=conf, pc=pc, model_manager=model_manager, scheduler=scheduler)


@app.route('/metrics')
def get_metrics():
    return request_handler.metrics_route()


@app.route('/job_dashboard')
def job_dashboard_metrics_route():
    return request_handler.job_dashboard_metrics_route()


# used as health check for liveness and readiness
@app.route('/')
def main():
    return request_handler.root_route()


@app.route('/locks')
def get_locks():
    return request_handler.locks_route()


@app.route('/activities')
def get_activities():
    return request_handler.scheduled_activities()


@app.route('/reports')
def get_reports():
    return request_handler.reports_route()


@app.route('/sendreports')
def send_reports_call():
    return request_handler.send_reports(call=True)


def retrain_models():
    logging.info("retraining models....")
    model_manager.retrain_models()


def retrain_model_end_window():
    logging.info("retraining models end window.. time is gone....")
    model_manager.init = True
    model_manager.retrain_models()


def send_reports():
    logging.info("Sending reports....")
    request_handler.send_reports()


def start_scheduling():
    scheduler.add_job(
        func=send_reports,
        trigger="interval",
        seconds=int(conf.get_report_window_second())
    )
    scheduler.start()


if __name__ == '__main__':
    try:
        app.logger.info("Setting scheduling...")
        start_scheduling()
        app.logger.info("Starting server...")
        atexit.register(lambda: scheduler.shutdown())
        app.run(host="0.0.0.0", debug=False)
    except:
        raise Exception("Error during start of k8s-anomaly-detector")
