#!/usr/bin/python
#
# Extensions to urwid terminal emulation widget
#    Copyright (C) 2010  aszlig
#    Copyright (C) 2011  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

import os
import errno
import fcntl
import signal
import struct
import termios

from urwid import (Terminal, TermCanvas)
from urwid.compat import B
try:
    from urwid.vterm import EOF
except ImportError:
    EOF = B('')


def waitstatus_to_exitcode(waitstatus):
    '''If the process exited normally (if WIFEXITED(status) is true), return
    the process exit status (return WEXITSTATUS(status)): result greater
    than or equal to 0.

    If the process was terminated by a signal (if WIFSIGNALED(status) is
    true), return -signum where signum is the number of the signal that
    caused the process to terminate (return -WTERMSIG(status)): result less
    than 0.

    Otherwise, raise a ValueError.'''

    # This function is for python 3.9 compat

    if getattr(os, 'waitstatus_to_exitcode', None):
        return os.waitstatus_to_exitcode(waitstatus)
    if os.WIFEXITED(waitstatus):
        return os.WEXITSTATUS(waitstatus)
    if os.WIFSIGNALED(waitstatus):
        return -os.WTERMSIG(waitstatus)

    raise ValueError

class TSTerminal(Terminal):
    signals = Terminal.signals + ['exitcode', 'feed', 'done', 'spawn']

    def run(self):
        self.terminated = False
        self.pid = None
        self.spawn()
        self.add_watch()

    def spawn(self):
        self._emit('spawn')
        super().spawn()

    def terminate(self):
        if self.terminated:
            return

        self.terminated = True
        self.remove_watch()
        self.change_focus(False)

        try:
            if self.pid > 0:
                self.set_termsize(0, 0)
                # upstream: improve process cleanup, much testing, add signal
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                self._emit('exitcode', waitstatus_to_exitcode(status))

                if pid == self.pid:
                    return

                for sig in (signal.SIGHUP, signal.SIGCONT, signal.SIGINT,
                            signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.kill(self.pid, sig)
                        pid, status = os.waitpid(self.pid, os.WNOHANG)
                    except OSError:
                        break

                    if pid == 0:
                        break
                    time.sleep(0.1)
                try:
                    os.waitpid(self.pid, 0)
                except OSError:
                    pass
        finally:
            # upstream: add signal. redundant with exit code one
            self._emit('done')

    def feed(self):
        data = EOF

        try:
            data = os.read(self.master, 4096)
        except OSError as e:
            if e.errno == 5: # EIO, child terminated
                data = EOF
            elif e.errno == errno.EWOULDBLOCK: # empty buffer
                return
            else:
                raise

        # upstream: add signal
        # upstream: add docs for signals?
        self._emit('feed', data)

        if data == EOF:
            self.terminate()
            self._emit('closed')
            return

        self.term.addstr(data)

        self.flush_responses()
