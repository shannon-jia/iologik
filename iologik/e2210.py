import aiohttp
import asyncio
import async_timeout
import logging
from collections import namedtuple, deque
from .events import Events

from html.parser import HTMLParser

log = logging.getLogger(__name__)


class Parser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        log.debug("Encountered a start tag: {}".format(tag))

    def handle_endtag(self, tag):
        log.debug("Encountered an end tag : {}".format(tag))

    def handle_data(self, data):
        log.debug("Encountered some data : {}".format(data))
        if self.callback:
            self.callback(data)

    def set_callback(self, callback):
        self.callback = callback


class E2210(object):
    ''' Moxa iologik E2210 module
        12 inputs and 8 outputs
    '''

    MAX_INPUTS = 12
    MAX_OUTPUTS = 8
    GET_PATH = 'getParam.cgi'
    SET_PATH = 'setParam.cgi'
    SYS_INFO = ['DATE', 'TIME', 'IP', 'LOC', 'DESC',
                'FWR_V', 'MOD_NAME', 'SN_NUM', 'MAC_ADDR']

    def __init__(self, loop,
                 url=None,
                 events=None,
                 line=0,
                 addr=1,
                 handle_events=None):
        self.loop = loop or None
        self.url = url
        self.line = line
        self.addr = addr
        self.events = events or Events()
        self.parser = Parser()
        self.parser.set_callback(self.received)
        self.handle_events = handle_events
        self.connection = None
        self.changed = True
        self.fail = True
        self.command = namedtuple('Command', 'name method params completed')
        self.setting = {'System': {},
                        'DIMode': ['DI' for i in range(self.MAX_INPUTS)],
                        'DIStatus': [0 for i in range(self.MAX_INPUTS)],
                        'DIFilter': [200 for i in range(self.MAX_INPUTS)],
                        'DOMode': ['DO' for i in range(self.MAX_OUTPUTS)],
                        'DOStatus': [1 for i in range(self.MAX_OUTPUTS)]
                        }
        self.CMDS = {
            'get_sys_info': ('get',
                             '&'.join(['{}=?'.format(i) for i in self.SYS_INFO])),
            'get_di_mode': ('get',
                            '&'.join(['DIMode_{:02d}=?'.format(i) for i in range(self.MAX_INPUTS)])),
            'set_di_mode': ('set',
                            '&'.join(['DIMode_{:02d}=0'.format(i) for i in range(self.MAX_INPUTS)])),
            'get_di_status': ('get',
                            '&'.join(['DIStatus_{:02d}=?'.format(i) for i in range(self.MAX_INPUTS)])),
            'set_di_filter_low': ('set',
                                  '&'.join(['DIFilter_{:02d}={}'.format(i, self.setting['DIFilter'][i]) for i in range(0, self.MAX_OUTPUTS//2)])),
            'set_di_filter_high': ('set',
                                  '&'.join(['DIFilter_{:02d}={}'.format(i, self.setting['DIFilter'][i]) for i in range(self.MAX_OUTPUTS//2, self.MAX_OUTPUTS)])),

            'get_do_mode': ('get',
                            '&'.join(['DOMode_{:02d}=?'.format(i) for i in range(self.MAX_OUTPUTS)])),
            'set_do_mode': ('set',
                            '&'.join(['DOMode_{:02d}=0'.format(i) for i in range(self.MAX_OUTPUTS)])),
            'get_do_status': ('get',
                            '&'.join(['DOStatus_{:02d}=?'.format(i) for i in range(self.MAX_OUTPUTS)])),
            'set_do_status': ('set',
                            '&'.join(['DOStatus_{:02d}=1'.format(i) for i in range(self.MAX_OUTPUTS)])),
            }

        self.cmd_deque = deque()
        for name in self.CMDS:
            self.append_cmd(name)

        # start to poll http server
        self.restart_poll()

    def poll(self):
        pass

    def do_output(self, addr, which, action, deadtime):
        if which >= self.MAX_OUTPUTS or which < 0:
            return
        status = (action == 'Activate' and 0 or 1)
        params = 'DOStatus_{:02d}={}'.format(which, status)
        self.cmd_deque.appendleft(self.command('do_outputs',
                                               'set', params, False))


    def append_cmd(self, cmd_name=None):
        cmd = self.CMDS.get(cmd_name)
        if cmd:
            self.cmd_deque.append(self.command(cmd_name,
                                               cmd[0], cmd[1], False))


    def received(self, data):
        log.debug("Encountered some data : {}".format(data))
        l = data.split('=')
        if len(l) != 2:
            return
        reg = l[0]
        val = l[1]
        if reg in self.SYS_INFO:
            self.setting['System'][reg] = val
        elif reg.startswith('DIMode'):
            n = int(reg.split('_')[1])
            if n < 0 or n >= self.MAX_INPUTS:
                return
            self.setting['DIMode'][n] = (val == '0' and 'DI' or 'COUNTER')
        elif reg.startswith('DIStatus'):
            n = int(reg.split('_')[1])
            if n < 0 or n >= self.MAX_INPUTS:
                return
            self.setting['DIStatus'][n] = (val == '0' and 'ALARM' or 'NORMAL')
            event_type = 'Auxiliary Input'
            event = 'MXI_{}_{}_{}'.format(self.line, self.addr, n)
            condition = (val == '0' and True or False)
            self.events.append(event, event_type, condition)
        elif reg.startswith('DIFilter'):
            n = int(reg.split('_')[1])
            if n < 0 or n >= self.MAX_INPUTS:
                return
            self.setting['DIFilter'][n] = int(val)
        elif reg.startswith('DOMode'):
            n = int(reg.split('_')[1])
            if n < 0 or n >= self.MAX_OUTPUTS:
                return
            self.setting['DOMode'][n] = (val == '0' and 'DO' or 'PULSE')
        elif reg.startswith('DOStatus'):
            n = int(reg.split('_')[1])
            if n < 0 or n >= self.MAX_OUTPUTS:
                return
            self.setting['DOStatus'][n] = (val == '0' and 'OFF' or 'ON')
        else:
            log.warn("Do not care it: {}".format(data))


    def processor(self):
        if not self.events:
            return
        if callable(self.handle_events):
            return self.handle_events(self.events)
        else:
            log.warn('No master to processor {}'.format(self.events))

    def restart_poll(self):
        asyncio.ensure_future(self.loop_polling())

    async def _fetch(self, params, method='get'):
        endpoint = (method == 'get' and self.GET_PATH or self.SET_PATH)
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(20):
                async with session.get('{}/{}?{}'.format(self.url,
                                                         endpoint,
                                                         params)) as response:
                    if response.status >= 200 and response.status <= 300:
                        self.parser.feed(await response.text())

    async def _request(self):
        try:
            self.cmd = self.cmd_deque.popleft()
        except IndexError:
            self.append_cmd('get_di_status')
            self.append_cmd('get_do_status')
            self.cmd = self.cmd_deque.popleft()

        log.debug('Request: {}'.format(self.cmd.name))
        x = await self._fetch(self.cmd.params,
                              method=self.cmd.method)

    async def loop_polling(self):
        try:
            while True:
                try:
                    await self._request()
                    self.connection = True
                    self.processor()
                except Exception as err:
                    log.error("Cmd {} failed, with Error: {} "
                              "Will retry in {} seconds"
                              .format(self.cmd.name, err, 10))
                    self.connection = False
                if self.connection is not True:
                    self.changed = True
                    self.cmd_deque.append(self.cmd)
                    self.fail = True
                    await asyncio.sleep(10)
                else:
                    self.changed = False
                    self.fail = False
                    log.info("{} Successfully requested. ".format(self.cmd.name))
                # poll connection state every 1s
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            self.connection = False
        except Exception as err:
            log.error("Failed to access http server with Error: {}".format(err))
            self.connection = False

