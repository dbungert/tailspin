#!/usr/bin/env python3

import argparse
import asyncio
from datetime import (timedelta, datetime)
import logging
import os
import sys
from timeit import default_timer as timer
import traceback
import urwid

from tailspin import util
from tailspin.urwid_ext.vterm import TSTerminal

args = None

# tailspin has three different categories where info is written
# 1) to screen in the status header
#    status header information is largely ephemeral, with a summary posted at
#    the end of tail window / subprocess log
# 2) to screen in the terminal window / subprocess log
#    the subprocess log is largely pristine subprocess output,
#    with a little bit of metadata before and after
# 3) logged to the tailspin log
#    tailspin log is a standard program diagnostic with minimal information
#    overlap with the subprocess log


class LabeledData(urwid.Text):
    def __init__(self, label='', _value=None):
        super().__init__('')
        self.label_text = label
        self.value = _value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, _value):
        self._value = _value
        self.set_text(f'{self.label_text}: {_value}')


class PassRate(LabeledData):
    def __init__(self, label=''):
        super().__init__(label)
        self.success = 0
        self.total = 0
        self.value = 'N/A'

    def complete(self, _success):
        if _success:
            self.success += 1
        self.total += 1
        rate = self.success / self.total * 100
        self.value = f'{rate:.0f}%'


class LabeledAverage(LabeledData):
    def __init__(self, label=''):
        super().__init__(label)
        self.values = []

    def append(self, _value):
        self.values.append(_value)

        value_sum = timedelta()
        for v in self.values:
            value_sum += v

        self.value = value_sum / len(self.values)


class RunCounter(LabeledData):
    def __init__(self, label, runs_desired):
        self.runs_desired = runs_desired
        super().__init__(label, 0)

    @LabeledData.value.setter
    def value(self, _value):
        self._value = _value
        self.set_text(f'{self.label_text}: {_value} of {self.runs_desired}')

    @property
    def needs_more(self):
        return self.value < self.runs_desired


class SubprocessLog:
    def __init__(self, runid=None):
        self.logfile = None
        self.logdir = util.create_logdir()
        if runid is not None:
            self.open(runid)

    def open(self, runid):
        self.close()
        name = util.generate_logfile_name(args.command[0], self.logdir, runid)
        self.logfile = open(name, 'wb')

    def close(self):
        if self.logfile:
            self.logfile.close()
            self.logfile = None

    def write(self, data):
        self.logfile.write(data)


class TopFrame(urwid.WidgetWrap):
    def __init__(self):
        self.cmd_arr = args.command
        self.log = SubprocessLog()
        self.command = urwid.Text(f'Command: {" ".join(self.cmd_arr)}')
        self.runs = RunCounter('Completed Runs', args.runs)
        self.runtime = LabeledData('Runtime')
        self.pass_rate = PassRate('Success Rate')
        self.avg_runtime = LabeledAverage('Average Runtime')
        self.header = urwid.Pile([
            self.command,
            self.runs,
            self.runtime,
            self.avg_runtime,
            self.pass_rate,
            urwid.Divider('─')
        ])
        self.term = TSTerminal(self.cmd_arr)
        urwid.connect_signal(self.term, 'exitcode', self.set_exitcode)
        urwid.connect_signal(self.term, 'feed', self.on_feed)
        urwid.connect_signal(self.term, 'done', self.on_done)
        urwid.connect_signal(self.term, 'spawn', self.on_spawn)
        self.frame = urwid.Frame(header=self.header, body=self.term)
        urwid.WidgetWrap.__init__(self, self.frame)

    def set_exitcode(self, _, rc):
        self.pass_rate.complete(rc == 0)

    def set_duration(self, delta):
        td = timedelta(seconds=delta)
        self.runtime.value = td
        self.avg_runtime.append(td)

    def on_spawn(self, _):
        self.log.open(self.runs.value + 1)
        self.start_time = timer()

    def end_run(self):
        self.end_time = timer()
        delta = self.end_time - self.start_time
        self.set_duration(delta)
        self.log.close()

    def on_done(self, _):
        self.end_run()
        self.runs.value += 1
        if self.runs.needs_more:
            self.term.run()

    def on_feed(self, _, data):
        self.log.write(data)

    def start(self, loop):
        self.term.main_loop = loop


def unhandled(key):
    if key in ('ctrl-c', 'enter'):
        logging.debug(key)
        raise urwid.ExitMainLoop


def on_loop_start(urwid_loop, top_frame):
    logging.debug('event loop running')
    top_frame.start(urwid_loop)


def excepthook(exctype, value, tb):
    logging.debug('Exception')
    logging.debug('Type: %s', exctype)
    logging.debug('Value: %s', value)
    for line in traceback.format_tb(tb):
        logging.debug('%s', line.strip())


def setup_diagnostic():
    log_format = ('%(asctime)-15s %(levelname)s %(module)s.%(funcName)s: '
                  + '%(message)s')

    os.makedirs('logs', exist_ok=True)

    logging.basicConfig(filename='logs/tailspin.log',
                        format=log_format, level=logging.DEBUG)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--runs', type=int, default=1,
                        help='Number of times to loop the command. ' +
                             'Default=1.  0=forever')
    parser.add_argument('command', nargs=argparse.REMAINDER,
                        help='Command and arguments to run.')
    global args
    args = parser.parse_args()


def main():
    try:
        urwid.set_encoding('utf8')
        sys.excepthook = excepthook

        setup_diagnostic()
        logging.debug('start')

        parse_args()
        top_frame = TopFrame()
        event_loop = urwid.AsyncioEventLoop(loop=asyncio.get_event_loop())
        urwid_loop = urwid.MainLoop(top_frame, unhandled_input=unhandled,
                                    event_loop=event_loop)

        urwid_loop.set_alarm_in(0, on_loop_start, user_data=top_frame)
        urwid_loop.run()
        logging.debug('exit')
    except BaseException:
        logging.exception('base exception')
        print(traceback.format_exc())
        sys.exit(1)
