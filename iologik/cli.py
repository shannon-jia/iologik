# -*- coding: utf-8 -*-

"""Console script for iologik."""

import click
# import logging
from .log import get_log
from .routermq import RouterMQ
from .main import MoxaIO
from .api import Api
import asyncio

def validate_url(ctx, param, value):
    try:
        return value
    except ValueError:
        raise click.BadParameter('url need to be format: tcp://ipv4:port')

@click.command()
@click.option('--url', default='http://192.168.1.254',
              callback=validate_url,
              envvar='RPS_URL',
              help='SerialPort Server HostName, ENV: RPS_URL')
@click.option('--amqp', default='amqp://admin:adminpass@localhost:5672//',
              callback=validate_url,
              envvar='RPS_AMQP',
              help='Amqp url, also ENV: RPS_AMQP')
@click.option('--port', default=8099,
              envvar='RPS_PORT',
              help='Api port, default=8099, ENV: RPS_PORT')
@click.option('--qid', default=0,
              envvar='RPS_QID',
              help='RPS ID for queue name, default=0, ENV: RPS_QID')
@click.option('--line', default=0,
              envvar='RPS_LINE',
              help='RPS Line for system name, default=0, ENV: RPS_LINE')
@click.option('--debug', is_flag=True)
def main(url, amqp, port, qid, line, debug):
    """Keeper for SAM2"""

    click.echo("See more documentation at http://www.mingvale.com")

    info = {
        'url': url,
        'api_port': port,
        'amqp': amqp,
    }
    log = get_log(debug)
    log.info('Basic Information: {}'.format(info))

    loop = asyncio.get_event_loop()
    loop.set_debug(0)

    # main process
    try:
        site = MoxaIO(loop, url, int(line))
        router = RouterMQ(outgoing_key='Alarms.keeper',
                          routing_keys=['Actions.keeper'],
                          queue_name='keeper_'+str(qid),
                          url=amqp)
        router.set_callback(site.got_command)
        site.set_publish(router.publish)
        api = Api(loop=loop, port=port, site=site, amqp=router)
        site.start()
        amqp_task = loop.create_task(router.reconnector())
        api.start()
        loop.run_forever()
    except KeyboardInterrupt:
        if amqp_task:
            amqp_task.cancel()
            loop.run_until_complete(amqp_task)
        site.stop()
    finally:
        loop.stop()
        loop.close()

