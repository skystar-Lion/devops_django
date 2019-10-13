#!/usr/bin/env python3


import time
import subprocess
import logging
import sys
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


logging.basicConfig(level=logging.INFO)


class Myhandler(FileSystemEventHandler):
    def __init__(self, fn):
        super(Myhandler, self).__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path:
            logging.info('src file:%s has changed' % event.src_path)
            self.restart()


command = ['echo', 'ok']
process = None


def kill_process():
    global process
    if process:
        logging.info('kill process ... pid:%s' % process.pid)
        process.kill()
        process.wait()
        logging.info('process return code.. %s' % process.returncode)
        process = None


def start_process():
    global process, command
    logging.info('start process %s ...' % ''.join(command))
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()


def start_watch(path, callback):
    observer = Observer()
    observer.schedule(Myhandler(restart_process), path, recursive=True)
    observer.start()
    logging.info('watchinf dir... %s' % path)
    start_process()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        logging.info('usage: ./daemon_monitor.py app.py')
        exit(0)
    if argv[0] != 'python3':
        argv.insert(0, 'python3')
    command = argv

    path = os.path.abspath('.')
    start_watch(path, None)
