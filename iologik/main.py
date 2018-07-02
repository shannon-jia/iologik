# -*- coding: utf-8 -*-

"""RPS One Main Progam."""
import asyncio
import logging
from urllib.parse import urlparse
from collections import namedtuple
from .events import Events
from .e2210 import E2210 as Manager

log = logging.getLogger(__name__)

class MoxaIO:
    """ Moxa IO Module
    """
    RELAY_KEEP_TIME = 20
    REPORT_STATUS_TIME = 10


    def __init__(self, loop=None,
                 url=None,
                 line=0):
        self.loop = loop or asyncio.get_event_loop()
        self.url = url
        self.line = line
        self.publish = None
        self.polling_cnt = 0
        self.num = 1
        self.events = Events()

        self.manager = None

    def __str__(self):
        return '{}'.format(self.url)

    def set_publish(self, publish):
        if callable(publish):
            self.publish = publish
        else:
            self.publish = None

    def start(self):
        self.manager = Manager(self.loop,
                               url = self.url,
                               events=self.events,
                               line = self.line,
                               handle_events=self.handle_events)
        self.loop.call_later(5, self.polling)

    def stop(self):
        pass

    def report_status(self):
        if not self.manager:
            return
        event = 'LINE_{}'.format(self.line)
        changed = self.manager.changed
        if self.manager.fail is False:
            event_type = 'OnLine'
            if self.num == 1:
                event_type = 'Comm Fail'
        else:
            event_type = 'Comm Fail'
            self.num = 0
        self.events.append_status(event,
                                  event_type,
                                  changed)
        self.handle_status(self.events)
        # report modules status
        # self.handle_status(self.mod_events)

    # Collect message to publish
    def handle_status(self, events):
        Event = namedtuple('Event', 'name time_stamp action event_type')
        status = events.get_status()
        for k,v in status.items():
            e = Event(*v)
            self._publish(e)

    # Collect message to publish
    def handle_events(self, events):
        Event = namedtuple('Event', 'name time_stamp action event_type')
        while not events.is_empty():
            e = Event(*events.pop())
            self._publish(e)

    def _publish(self, e):
        x = {'name': e.name,
             'time_stamp': e.time_stamp,
             'action': e.action,
             'type': e.event_type
        }
        log.info("publish: {}".format(x))
        if callable(self.publish):
            self.publish(x)

    def polling(self):
        self.polling_cnt += 1
        if self.polling_cnt > 10000:
            self.polling_cnt = 0
        if (self.polling_cnt % (self.REPORT_STATUS_TIME * 8)) == 7:
            self.report_status()
        if self.manager.fail is False:
            self.num += 1
            if self.num == 1:
                self.report_status()
                print('{}{}{}{}{}{}{}{}{{}{}{}}')
        self._polling()
        self.loop.call_later(1, self.polling)

    def _polling(self):
        try:
            if self.manager:
                self.manager.poll()
                log.debug('poll {}'.format('manager'))
        except Exception as err:
            log.warn('Poll fail: {}'.format(err))

    def info(self):
        return {
            'url': self.url,
            'module': 'Moxa_E2210',
            'setting': self.manager.setting
        }

    async def got_command(self, msg):
        ''' once process one json '''
        log.debug('got command: {}'.format(msg))
        try:
            m = msg
        except Exception as e:
            log.error('get error command : {}'.format(e))
            return False

        cmd = m.get('cmd')
        if cmd == 'OK':
            return True
        cmd_type = m.get('type').upper()
        names = m.get('name', '')
        status = m.get('status', 'AUTO')
        deadtime = m.get('deadtime', self.RELAY_KEEP_TIME)
        if not deadtime:
            deadtime = self.RELAY_KEEP_TIME
        if cmd_type == 'RELAY' or cmd_type == 'OUTPUT':
            if type(names) is list:
                for name in names:
                    self.control_relay(name, status, deadtime)
            elif type(names) is str:
                self.control_relay(names, status, deadtime)
            else:
                return False
        return True

    # Release for SAM2
    def control_relay(self, name, status='AUTO', deadtime=10):
        ENUM_STATUS = ('ON', 'OFF', 'AUTO')
        # ENUM_DEVICE = ('RM', 'ROM', 'ROM08', 'ROM16')
        if type(name) is not str:
            return None
        name_parts = name.split('_')
        if len(name_parts) < 4:
            return None
        dev = name_parts[0].upper()
        # jump RM relay process
        # if dev not in ENUM_DEVICE:
        #     return False
        status = status.upper()
        if status not in ENUM_STATUS:
            return False

        try:
            sys = int(name_parts[1])
            if self.line != 0 and self.line != sys:
                log.warn('Line number is not equal!: Line[{}] != {}'
                         .format(self.line, sys))
                # return False
            unit = int(name_parts[2])
            relay = int(name_parts[3])
            if status == 'ON':
                action = 'Activate'
                dt = 0
            elif status == 'AUTO':
                action = 'Activate'
                dt = int(deadtime)
            else:
                action = 'Reset'
                dt = 0
            self.update_relay(unit, relay, action, dt)
            return True
        except Exception as e:
            log.error('control_relay error: {}'.format(e))
            return False
        return False

    def update_relay(self, addr, which, action, deadtime=0):
        if not self.manager:
            return False
        return self.manager.do_output(addr, which, action, deadtime)

