# calendar.py
# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import threading
import logging
import time

from gi.repository import GLib, Gio

from remembrance import info

logger = logging.getLogger(info.app_executable)

class Calendar(threading.Thread):
    '''Updates date labels when day changes'''
    def __init__(self, win):
        self.app = win
        self.time = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.countdown_id = 0
        super().__init__(target=self.run_countdown)
        self.start()

        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.NONE,
            None,
            'org.freedesktop.login1',
            '/org/freedesktop/login1',
            'org.freedesktop.login1.Manager',
            None,
            self.bus_callback
        );

    def bus_callback(self, obj, result):
        proxy = obj.new_for_bus_finish(result)
        proxy.connect("g-signal", self.on_signal_received)

    def on_signal_received(self, proxy, sender, signal, parameters):
        if signal == "PrepareForSleep" and parameters[0]:
            logger.info('Resuming from sleep')
            self.run_countdown(False)

    def on_countdown_done(self):
        for reminder in self.win.reminder_lookup_dict.values():
            reminder.set_time_label()
        if self.win.reminder_edit_win is not None:
            self.win.reminder_edit_win.update_date_button_label()
        self.countdown_id = 0
        self.run_countdown()
        return False

    def remove_countdown(self):
        GLib.Source.remove(self.countdown_id)

    def run_countdown(self, new_day = True):
        try:
            if new_day:
                self.time = self.time + datetime.timedelta(days=1)
                self.timestamp = self.time.timestamp()

            if self.countdown_id != 0:
                GLib.Source.remove(self.countdown_id)
                self.countdown_id = 0

            now = time.time()
            self.wait = int(1000 * (self.timestamp - now))
            if self.timestamp > 0:
                self.countdown_id = GLib.timeout_add(self.wait, self.on_countdown_done)
            else:
                self.on_countdown_done()
        except Exception as error:
            logger.error(f'{error}: Failed to set timeout to refresh date labels')