#!/usr/bin/env python3

import sys
import redis

import logging

from configuration import Configuration
from model_manager import ModelManager
from prometheus_api_client import PrometheusConnect

conf = Configuration()

# Set up Redis
store = redis.StrictRedis(
    host=conf.get("redis_host"),
    port=conf.get("redis_port")
)
logging.info(store.info())
logging.info("check status of redis passed..")

pc = PrometheusConnect(
    url=conf.get("prometheus_url"),
    headers=conf.get_prometheus_header(),
    disable_ssl=True,
)

if __name__ == '__main__':
    init = False
    if sys.argv[0] == "init":
        init = True

    ModelManager(conf=conf, storage=store, pc=pc, init=init)

    print("retrain is done! :)")
    exit(0)
