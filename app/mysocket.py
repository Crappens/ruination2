"""
This module manages a persistent websocket for MyYear, used
to send the keepalive signal for locks, and hopefully other
stuff in the future.

It's built with https://github.com/zeekay/flask-uwsgi-websocket
"""
import json
import shlex
import datetime
import contextlib
from collections import defaultdict
from injector import uwsgi

from flask.ext.uwsgi_websocket import GeventWebSocket as WebSocket

from app import scheduler
from app.models import db, Sheet, User, Book
from app.ripper.ripper import rip_book
from app.flowing.index import build_index
from app.submission.http import submit_book


class WebSocketCommander(object):
    """
    Parse commands from a websocket and dispatch to matching handler methods.
    """
    # a set of connections that can talk to each other (like an irc channel)
    channels = defaultdict(set)

    def __init__(self, app, ws):
        """
        Constructor.
        :param app: the Flask application object
        :param ws: the WebSocketClient object
        :return:
        """
        self.app = app
        self.ws = ws
        self.connected = True
        self.outbox = []     # you can't send from a callback in uwsgi, so we use a queue
        self.current_task = 0

    def interact(self):
        """
        This controls the actual communication between ruination and MyYear.
        """
        while True:
            cmd = self.ws.receive()
            # Flask-uWSGI-WebSocket's gevent websockets catch the exception that's
            # supposed to be thrown here, and replace it with this boolean:
            if self.ws.connected:
                if cmd:   # WebSocket seems to return None, GeventWebsocket returns ''
                    self.dispatch(cmd)
                while self.outbox:
                    self.ws.send(self.outbox.pop(0))
            else:
                self.connected = False
                uwsgi.log("websocket client disconnected!")
                break

    def dispatch(self, cmd):
        """
        This parses the command and executes a corresponding method on this class.
        example: passing `foo "b a r" 123`  will call `self.cmd_foo("b a r","123")`

        Commands may start with a message number like `#1`. This is so the client
        can send the command asynchronously, and pair the response up with a
        promise / callback later.

        :param cmd: string representing the command to execute
        :return:
        """
        if cmd is None:
            pass   # otherwise shlex.split will block, trying to read from stdin!
        else:
            toks = shlex.split(cmd)

            if toks[0].startswith("#"):
                self.current_task = int(toks.pop(0)[1:])

            meth = getattr(self, "cmd_%s" % toks[0], None)
            if meth is None:
                self.reject("unknown command: %s" % toks[0])
            else:
                uwsgi.log('cmd> ' + cmd)
                try:
                    meth(*toks[1:])
                except Exception as e:
                    self.reject('%s: %s' % (e.__class__.__name__, e.message))
            self.current_task = 0

    def send(self, data):
        """
        Sends a raw string to the server. As a convenience, non-strings will be json-encoded.
        :param data: a string, or a dictionary/list to jsonify
        :return:
        """
        msg = data if type(data) in [unicode, str] else json.dumps(data)
        uwsgi.log("sending: %s" % msg)
        self.outbox.append(msg)

    def reject(self, msg):
        """
        Call this to send a failure message to the client.
        :param msg:
        :return:
        """
        self.send([-self.current_task, msg])

    def resolve(self, result):
        """
        Call this to send a successful response to the client.
        :param result:
        :return:
        """
        self.send([self.current_task, result])

    def cmd_echo(self, *args):
        """
        Just a simple echo command for testing.
        Sends back the tokenized arguments as a json list.
        :param args:
        :return:
        """
        self.send(args if self.current_task == 0 else [self.current_task, args])

    # -- channel support ----------------------

    def join(self, chan):
        """
        Join the given chan
        :param chan: an object (string, probably) representing the chan
        :return:
        """
        self.channels[chan].add(self)

    def part(self, channel):
        """
        Join the given channel
        :param channel: an object (string, probably) representing the channel
        :return:
        """
        self.channels[channel].add(self)

    @classmethod
    def broadcast(cls, chan, data, user=None):
        """
        Send a message to all listeners on a chan.
        Broadcast messages are always sent with task #0.

        :param chan: an object (string, probably) representing the chan
        :param data: the message to send. non-strings will be json-encoded.
        :param user: optional, a specific user to aim the broadcast at.
        :return:
        """
        # remove dead sockets:
        cls.channels[chan] = {sock for sock in cls.channels[chan] if sock.connected}
        for sock in cls.channels[chan]:
            if user and sock.user_id == user:
                sock.send([0, data])
            elif not user:
                sock.send([0, data])


class MyYearCommander(WebSocketCommander):
    """
    A WebSocketCommander with MyYear-specific logic.

    events sent by this class:

      ['evt-locked', sheet_id:str, user_id:str]
      ['evt-unlocked', sheet_id:str, was_forced:bool]

    """

    def __init__(self, app, ws):
        """
        Constructor
        :param app: flask app
        :param ws: websocket
        :return:
        """
        super(MyYearCommander, self).__init__(app, ws)
        self.renew_seconds = 2 * 60
        self.expire_seconds = 15 * 60
        self.current_locks = set()
        self.user_id = None
        self.book_id = None
        self.project_num = None
        self.token = None

    # -- user login

    # !! this seems rather insecure, but it mirrors the current level of security
    #    in the HTTP api, where the locking user_id is just sent in the URL.
    #    Maybe we should rethink this? :)
    def cmd_user(self, user_id, book_id, token, project_number):
        self.user_id = user_id
        self.book_id = book_id
        self.token = token
        self.project_num = project_number
        self.resolve("hello, %s" % user_id)
        self.join(self.book_id)

    # -- test hooks ---------------

    def cmd_whoami(self):
        self.resolve(self.user_id)

    def cmd_speed(self, renew, expire):
        """
        Change the lock renewal/expiration speed.
        <<called by test runner>>
        :param renew: number of seconds before locks renew
        :param expire: number of seconds before locks expire
        :return:
        """
        self.renew_seconds = int(renew)
        self.expire_seconds = int(expire)
        self.resolve("renew locks every %s seconds, expire after %s seconds"
                     % (renew, expire))

    def cmd_halt(self):
        """Force websocket to close immediately. <used by test runner>"""
        self.ws.close()

    def cmd_reap(self):
        """Force lock reaper to run immediately. <used by test runner>"""
        self.reap_locks(self.app)

    # -- sheet locking methods ---------------

    def cmd_unlock(self, sheet_id):
        """
        Unlock a sheet, by id.

        :param sheet_id:
        :return:
        """
        if sheet_id in self.current_locks:
            with self._sheet_context(sheet_id) as sheet:
                if sheet.locked and sheet.user_id == self.user_id:
                    sheet.locked_until = None
                    sheet.locked = False
                    sheet.user_id = ''
                    self.current_locks.remove(sheet_id)
                    self.resolve('ok')
                    self.broadcast(self.book_id, ['evt-unlocked', sheet_id, False])
                    if sheet.thumbnail_url:
                        current_thumbnail = sheet.thumbnail_url.rsplit("/", 1)[1]
                    else:
                        current_thumbnail = None
                    if sheet_id + "_" + str(sheet.version) + ".png" != current_thumbnail:
                        g = rip_book(sheet_id=sheet_id, split_spread=False, user_id=self.user_id,
                                     project_name=self.project_num, project_id=self.book_id, token=self.token,
                                     thumbnail=True, image_type="LowRes")
                        self.broadcast(self.book_id, ['evt-thumbnail', sheet_id, g[0]])
                else:
                    self.reject("cannot unlock %s" % sheet_id)
        else:
            self.reject("cannot unlock %s" % sheet_id)

    def cmd_force_unlock(self, sheet_id):
        """
        Force an unlock of the sheet. (This is performed by admin users).
        :param sheet_id:
        :return:
        """
        if sheet_id in self.current_locks:
            # This shouldn't actually happen, since the admin screen doesn't
            # list the page the admin has open themselves, but just in case,
            # something changes in the future, treat it as a normal unlock:
            self.cmd_unlock(sheet_id)
        else:
            with self._sheet_context(sheet_id) as sheet:
                sheet.locked_until = None
                sheet.locked = False
                sheet.user_id = ''
                sheet_thumb = sheet.thumbnail_url
                sheet_version = sheet.version
            self.resolve('ok')
            self.broadcast(self.book_id, ['evt-unlocked', sheet_id, True])
            if sheet_thumb:
                current_thumbnail = sheet_thumb.rsplit("/", 1)[1]
            else:
                current_thumbnail = None
            if sheet_id + "_" + str(sheet_version) + ".png" != current_thumbnail:
                g = rip_book(sheet_id=sheet_id, split_spread=False, user_id=self.user_id,
                             project_name=self.project_num, project_id=self.book_id, token=self.token,
                             thumbnail=True, image_type="LowRes")
                self.broadcast(self.book_id, ['evt-thumbnail', sheet_id, g[0]])

    def cmd_lock(self, sheet_id):
        """
        Lock a sheet, by id.

        Multiple sheets can be locked at a time. Just run this
        command multiple times. (ex: SVGEditService.unTagGallery.)

        :param sheet_id:
        :return:
        """
        if sheet_id in self.current_locks:
            pass   # already locked
        else:
            with self._sheet_context(sheet_id) as sheet:
                if sheet.locked and sheet.user_id != self.user_id:
                    self.reject("sheet %s is already locked." % sheet_id)
                else:
                    # Even though we just checked, it's possible that someone else could
                    # be acquiring the lock right this nanosecond. Therefore, we'll use
                    # an optimistic locking strategy, where we both re-check the lock
                    # and attempt to acquire it in a single query.
                    rowcount = (db.session.query(Sheet)
                                .filter((Sheet.id_ == sheet_id) &
                                        ((~Sheet.locked) | (Sheet.user_id == self.user_id)))
                                .update({Sheet.locked: True,
                                         Sheet.user_id: self.user_id,
                                         Sheet.locked_until: self._lock_time()},
                                        synchronize_session='evaluate'))
                    if rowcount == 1:
                        self.current_locks.add(sheet_id)
                        self._schedule_relock(sheet_id)
                        self.resolve('ok')
                        self.broadcast(self.book_id, ['evt-locked', sheet.id, self.user_id])
                    else:
                        self.reject("Unable to acquire lock.")

    def cmd_reacquire(self, sheet_id, version):
        """
        Attempt to reacquire a lock for the given sheet (after a disconnect).
        :param sheet_id:
        :param version:
        :return:
        """
        with self._sheet_context(sheet_id) as sheet:
            if int(sheet.version) > int(version):
                return self.reject('The sheet has been changed by another user.')
            elif sheet.locked and sheet.user_id != self.user_id:
                return self.reject('The sheet has been locked by another user.')
        # can't nest sheet contexts or you get a wacky 'DetachedInstanceError'
        self.cmd_lock(sheet_id)

    def cmd_request_thumbnail(self, sheet_id):
        sheets_to_rip = sheet_id.replace("[", "").replace("]", "").split(",")
        if sheets_to_rip[0] == "":
            sheets_to_rip.pop(0)
        with self.app.app_context():
            if len(sheets_to_rip) > 0:
                if type(sheets_to_rip) is not list:
                    sheets_to_rip = [sheets_to_rip]
                for sheet in sheets_to_rip:
                    resp = rip_book(sheet_id=sheet, project_id=self.book_id, project_name=self.project_num,
                                    user_id=self.user_id, token=self.token, thumbnail=True, split_spread=False,
                                    image_type='LowRes')
                    self.broadcast(self.book_id, ['evt-thumbnail', sheet, resp[0]])

    def cmd_build_index(self, req_data):
        with self.app.app_context():
            data = json.loads(req_data)
            if isinstance(data['n_reversed'], basestring):
                tmp = False if data["n_reversed"].lower() == "false" else True
            else:
                tmp = data["n_reversed"]
            resp = build_index(project_number=self.book_id, user_id=self.user_id, token=self.token, field=data["field"],
                               category=data["category"], c_reversed=data["c_reversed"], n_reversed=tmp)
            self.broadcast(self.book_id, ['evt-dir-proof', resp], self.user_id)

    def cmd_submit_book(self):
        with self.app.app_context():
            user = db.session.query(User).filter_by(user_uuid=self.user_id).first()
            user_name = user.user_first_name + " " + user.user_last_name
            book = db.session.query(Book).filter_by(id_=self.book_id).first()
            resp = submit_book(req_data={"project_id": self.book_id, "user_id": self.user_id, "token": self.token,
                                         "project_name": self.project_num}, user=user, user_name=user_name, book=book)
            self.broadcast(self.book_id, ['evt-message', 'submission', resp["msg"]])

    @contextlib.contextmanager
    def _sheet_context(self, sheet_id):
        """
        Fetches a sheet by id, if it exists, and saves it after
        your `with` block executes.
        :param self:
        :param sheet_id:
        :return:
        """
        # we need the app_context so that Flask-SQLAlchemy knows which app/db to use.
        with self.app.app_context():
            sheet = db.session.query(Sheet).filter_by(id_=sheet_id).first()
            if sheet is None:
                raise LookupError("unknown sheet %s" % sheet_id)
            else:
                yield sheet
                db.session.commit()

    def _schedule_relock(self, sheet_id):
        """
        Helper to schedule update of the lock after .renew_seconds
        """
        uwsgi.log('scheduling relock for %s' % sheet_id)
        scheduler.add(self._relock, self.renew_seconds, sheet_id)

    def _lock_time(self):
        """
        :return: a new datetime, self.expire_seconds in the future.
        """
        return datetime.datetime.utcnow() + datetime.timedelta(seconds=self.expire_seconds)

    def _relock(self, sheet_id):
        """
        Updates the user's lock on the page, and then calls
        `_schedule_relock` so the lock gets renewed indefinitely.

        Note: the lock is cleared automatically by the scheduled
        call to `reap_locks` if this function isn't called to renew it.

        :param sheet_id:
        :return:
        """
        if self.connected and sheet_id in self.current_locks:
            with self._sheet_context(sheet_id) as sheet:
                # ! shouldn't be any need to test the lock again if we got to this point, but...
                assert sheet.user_id == self.user_id, "not your lock to renew!?! %s" % sheet_id
                sheet.locked_until = self._lock_time()
                uwsgi.log("renewed lock for %s until %s" % (sheet_id, sheet.locked_until))
                self._schedule_relock(sheet_id)
        else:
            uwsgi.log("allowing lock for %s to expire" % sheet_id)
            pass  # we either unlocked the page or got disconnected

    @classmethod
    def reap_locks(cls, app):
        """
        This runs once a minute (after `mysocket.register` schedules it).
        It clears out expired locks from the database.

        :param app: the flask application context
        :return:
        """
        with app.app_context():
            db.session.flush()
            for sheet in db.session.query(Sheet).filter(Sheet.locked,
                                                        Sheet.locked_until < datetime.datetime.utcnow()).all():
                sheet.user_id = ''
                sheet.locked = False
                sheet.locked_until = None
                # broadcast as a regular unlock, even though we are technically
                # forcing it. The only difference is that with forced unlocks,
                # the user who has the page open is forcibly kicked off the page,
                # but in this case, that person has lost their connection.
                # (they may have reconnected, but that's handled elsewhere.)
                cls.broadcast(sheet.book_id, ['evt-unlocked', sheet.id, False])

            db.session.commit()
        print "-------REAPER"
        scheduler.add(MyYearCommander.reap_locks, 30, app)


def register(app, uri):
    """
    This mounts our websocket handler onto a live Flask app.
    It also sets up the scheduler to run every second.

    (We're doing it this way rather than using @ws.route(uri)
    because app_factories.py is set up to use blueprints,
    but flask-uwsgi-websocket expects a live Flask object.)

    :param app: the flask app object
    :param uri: the URI at which we'll serve the websocket
    :return: None
    """
    wsk = WebSocket(app)
    wsk.add_url_rule(uri, view_func=lambda ws: MyYearCommander(app, ws).interact())
    scheduler.add(MyYearCommander.reap_locks, 15, app)

if __name__ == "__main__":
    pass
