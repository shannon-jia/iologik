#!/usr/bin/env python

"""
  Events

  Copyright (c) Mingvale Technology Co.,Ltd
  See LICENSE for details.

"""

import logging
import time

log = logging.getLogger(__name__)


class Events(object):
    ''' Events for handle 
    '''

    def __init__(self):
        self.history = {}
        self.queue = []
        self.status = {}

    # Events
    def clear(self):
        self.history.clear()
        self.status.clear()

    def add_to_history(self, event):
        self.history.setdefault(event, self._time_stamp())
        return self.history.get(event)

    def remove_from_history(self, event):
        return self.history.pop(event, None)

    def append(self, event, event_type, condition):
        action = None
        if condition:
            time_stamp = self.add_to_history(event)
            action = 'Activated'
        else:
            stamp = self.remove_from_history(event)
            if stamp:
                time_stamp = self._time_stamp()
                action = 'Reseted'
        if action:
            self.queue.append((event, time_stamp, action, event_type))

    def pop(self):
        if self.queue:
            return self.queue.pop(0)
        else:
            return (None, None, None, None)

    def is_empty(self):
        if self.queue:
            return False
        else:
            return True

    # modules status
    def append_status(self, event, event_type, changed):
        action = 'Activated'
        if changed:
            time_stamp = self.add_to_history(event)
        else:
            stamp = self.remove_from_history(event)
            if stamp:
                action = 'Reseted'
            time_stamp = self._time_stamp()
        # if changed:
        #     time_stamp = self._time_stamp()
        # else:
        #     (_, time_stamp, _, _) = self.status.get(event,
        #                                             (None,
        #                                              None,
        #                                              None,
        #                                              None))
        #     if not time_stamp:
        #         time_stamp = self._time_stamp()
        #         action = 'Reseted'
        x = (event, time_stamp, action, event_type)
        self.status[event] = x

    def get_status(self):
        return self.status

    def status_is_empty(self):
        if self.status:
            return False
        else:
            return True

    def _time_stamp(self):
        t = time.localtime()
        time_stamp = '%d-%02d-%02d %02d:%02d:%02d' % (t.tm_year,
                                                      t.tm_mon,
                                                      t.tm_mday,
                                                      t.tm_hour,
                                                      t.tm_min,
                                                      t.tm_sec)
        return time_stamp
