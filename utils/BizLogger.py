import os
import logging
import time
from flask import request
import socket
from logging import handlers

local_host = socket.gethostname()
import json


class RequestFormatter(logging.Formatter):

    def __init__(self, app, *args, **kvargs):
        self._app = app
        logging.Formatter.__init__(self, *args, **kvargs)

    def format(self, record):
        try:
            record.traceId = request.values.get('request_id', '0')
            record.version = request.values.get('client_version', 0)
        except Exception as e:
            record.traceId = '0'
            record.version = 0
        tm = time.time()
        msc = int(tm * 1000) % 1000
        nowtime = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(tm)))
        nowtime += ".{}Z".format(msc)
        record.utc = nowtime
        record.local_host = local_host
        record.msg = json.dumps(record.msg, ensure_ascii=False)
        result = super().format(record)
        return result.replace("WARNING", "WARN")


class MyLogger(object):
    def __init__(self, name="graph-data-evals"):
        self.biz_hdl = None
        self._name = name
        self._init_log_format()
        print("Init MyLogger")

    def _init_log_format(self):
        biz_log = os.getenv('LOG_BIZ_FILE', "vivo_biz_graph-data-evals.log")
        if biz_log is not None:
            if biz_log.find('/') != -1:
                log_dir = '/'.join(biz_log.split("/")[0:-1])
                if not os.path.exists(log_dir):
                    try:
                        os.makedirs(log_dir)
                    except Exception as e:
                        print(e)
            self.log_time = time.strftime("%Y%m%d%H")
            formatter = RequestFormatter(self,
                                         '{"process_name":"%(processName)s","thread_name":"%(threadName)s","message":%(message)s,"@timestamp":"%(utc)s","level":"%(levelname)s","mdc":{"traceId":"%(traceId)s"},"file":"%(filename)s","class":"","line_number":"%(lineno)s","logger_name":"%(name)s","method":"%(funcName)s","@version":"%(version)s","source_host":"%(local_host)s"}'
                                         )
            new_hdl = handlers.TimedRotatingFileHandler(
                filename='/data/tomcat/logs/biz/' + biz_log + "." + self.log_time, when="MIDNIGHT", interval=3,
                backupCount=3)
            fhdl = logging.FileHandler('/data/tomcat/logs/biz/' + biz_log + "." + self.log_time, 'a+')
            new_hdl.setFormatter(formatter)
            fhdl.setFormatter(formatter)
            self.biz_logger = logging.getLogger(self._name)
            self.biz_logger.setLevel(logging.INFO)
            if self.biz_hdl is not None:
                self.biz_logger.removeHandler(self.biz_hdl)
            self.biz_logger.addHandler(fhdl)
            self.biz_hdl = fhdl
            self._is_biz = True
        else:
            self._is_biz = False
            self.biz_logger = None

    def get_biz_logger(self):
        if self._is_biz:
            now = time.strftime("%Y%m%d%H")
            if now != self.log_time:
                self._init_log_format()
        return self.biz_logger


class StreamFormatter(logging.Formatter):

    def __init__(self, app, *args, **kvargs):
        self._app = app
        logging.Formatter.__init__(self, *args, **kvargs)

    def format(self, record):
        try:
            record.traceId = request.values.get('request_id', '0')
            record.version = request.values.get('client_version', 0)
        except Exception as e:
            record.traceId = '0'
            record.version = 0

        record.local_host = local_host
        result = super().format(record)
        return result.replace("WARNING", "WARN")


class StreamLogger(object):
    def __init__(self, name="graph-data-evals"):
        self.biz_logger = logging.getLogger(name)
        self.biz_logger.setLevel(logging.INFO)
        fhdl = logging.StreamHandler()
        formatter = StreamFormatter(self,
                                    '%(local_host)s %(processName)s %(threadName)s %(asctime)s %(traceId)s %(message)s'
                                    )
        fhdl.setFormatter(formatter)
        self.biz_logger.addHandler(fhdl)
        print("Init streamLogger")

    def get_biz_logger(self):
        return self.biz_logger


env = os.getenv('APP_ENV', None)
if env == 'pre':
    mylogger = MyLogger()
elif env == 'prd':
    mylogger = MyLogger()
else:
    mylogger = StreamLogger()


def log_warn(*argv, **argkv):
    try:
        mylogger.get_biz_logger().warn(*argv, **argkv)
    except Exception as e:
        print("logger error", e)


def log_error(*argv, **argkv):
    try:
        mylogger.get_biz_logger().error(*argv, **argkv)
    except Exception as e:
        print("logger error", e)


def log_info(*argv, **argkv):
    try:
        mylogger.get_biz_logger().info(*argv, **argkv)
    except Exception as e:
        print("logger error", e)