# -*- coding: utf-8 -*-

from contextlib import closing
import sys
import threading

import requests

from gnippy import config


class PowerTrackClient():
    """
        PowerTrackClient allows you to connect to the GNIP
        power track stream and fetch data.
    """
    callback = None
    url = None
    auth = None

    def __init__(self, callback, exception_callback=None, **kwargs):
        self.callback = callback
        self.exception_callback = exception_callback
        c = config.resolve(kwargs)
        self.url = c['url']
        self.auth = c['auth']

    def connect(self):
        self.worker = Worker(self.url, self.auth, self.callback,
                             self.exception_callback)
        self.worker.setDaemon(True)
        self.worker.start()

    def disconnect(self):
        self.worker.stop()
        self.worker.join()

    def load_config_from_file(self, url, auth, config_file_path):
        """ Attempt to load the config from a file. """
        conf = config.get_config(config_file_path=config_file_path)

        if url is None:
            conf_url = conf['PowerTrack']['url']
            if conf_url:
                self.url = conf['PowerTrack']['url']
        else:
            self.url = url

        if auth is None:
            conf_uname = conf['Credentials']['username']
            conf_pwd = conf['Credentials']['password']
            self.auth = (conf_uname, conf_pwd)
        else:
            self.auth = auth


class Worker(threading.Thread):
    """ Background worker to fetch data without blocking """
    def __init__(self, url, auth, callback, exception_callback=None):
        super(Worker, self).__init__()
        self.url = url
        self.auth = auth
        self.on_data = callback
        self.on_error = exception_callback
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.isSet()

    def run(self):
        try:
            with closing(requests.get(self.url, auth=self.auth, stream=True)) as r:
                if r.status_code != 200:
                    self.stop()
                    raise Exception("GNIP returned HTTP {}".format(r.status_code))

                for line in r.iter_lines():
                    if line:
                        self.on_data(line)

                    if self.stopped():
                        break
        except Exception:
            if self.on_error:
                exinfo = sys.exc_info()
                self.on_error(exinfo)
            else:
                # re-raise the last exception as-is
                raise
