from injector import uwsgi
import gevent
import datetime
from app.config import config_map


class Schedule(object):
    """
    singleton (or rather just a class with class methods)
    that runs callbacks periodically.

    This is basically here as an abstraction layer, so we can swap
    out the actual scheduling system without having to rewrite any code.

    (uWSGI provides several options and it's not at all clear which
     configuration is going to work for us in the long run.)
    """
    queue = []        # a list of (datetime, callback, *args, **kwargs) tuples

    @classmethod
    def add(cls, callback, seconds, *args, **kwargs):
        """
        Call this to schedule your callback to run after n seconds.
        :param callback:
        :param seconds:
        :param args:
        :param kwargs:
        :return:
        """
        when = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        cls.queue.append((when, callback, args, kwargs))
        cls.queue.sort(lambda a, b: cmp(a[0], b[0]))  # sort by datetime

    @classmethod
    def tick(cls, num=None):
        """
        This gets called every second or so. It runs any callbacks that
        are ready to be called, and removes them from the queue.
        :param num: int signal number from uwsgi. (should be TICK_SIGNAL)
        :return:
        """
        now = datetime.datetime.now()
        while cls.queue and now > cls.queue[0][0]:
            _, callback, args, kwargs = cls.queue.pop(0)
            callback(*args, **kwargs)


# -- choices for running the Schedule under uWSGI

# ! As far as I can tell, uwsgi signals are just bytes,
#   and we're meant to manage them ourselves. Hopefully,
#   this one won't collide with anything.
TICK_SIGNAL = 42


def spawn_schedule_uwsgi():
    """
    Spawn the schedule using uwsgi's internal timer framework.
    The problem with this approach is that it seems to spawn in
    a new worker.
    :return:
    """
    uwsgi.register_signal(TICK_SIGNAL, '', Schedule.tick)
    uwsgi.add_timer(TICK_SIGNAL, 1)  # every 1 second


def spawn_schedule_gevent():
    """
    Spawn the scheduler as a gevent process.
    :return:
    """
    def ticker():
        while True:
            Schedule.tick()
            gevent.sleep(1)
    gevent.spawn(ticker)


# -- public API ------------------------------


def add(callback, seconds, *args, **kwargs):
    """
    Run the callback every <seconds> seconds.
    :param callback:
    :param seconds:
    :param args:
    :param kwargs:
    :return:
    """
    Schedule.add(callback, seconds, *args, **kwargs)


def start(config_name):
    """
    Start the scheduler thread/greenlet/whatever,
    based on the configuration
    :param config_name:
    :return:
    """
    which = config_map[config_name].SCHEDULER
    if which == 'gevent':
        spawn_schedule_gevent()
    else:
        spawn_schedule_uwsgi()
