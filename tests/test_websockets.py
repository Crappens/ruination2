import json
from mock import MagicMock, patch
import unittest

from tests import TestCase
from tests.sample_data import LOCKED_SHEET_UUID, SHEET_UUID, USER_ID, EXPIRED_LOCKED_SHEET_UUID


class TestWebsockets(TestCase):

    USER_ID = 'tester007'
    BOOK_ID = 'myTestBook'
    TOKEN = 'abcd'
    PROJECT_NUMBER = '337799'

    def test_01_cmd_user(self):
        self.ws_view.dispatch(
            '#3 user %s %s %s %s' % (
                self.USER_ID,
                self.BOOK_ID,
                self.TOKEN,
                self.PROJECT_NUMBER
            )
        )

        self.assertEqual(self.ws_view.user_id, self.USER_ID)
        self.assertEqual(self.ws_view.book_id, self.BOOK_ID)
        self.assertEqual(self.ws_view.project_num, self.PROJECT_NUMBER)
        self.assertEqual(self.ws_view.token, self.TOKEN)

        # get socket response:
        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('3', soc_resp)
        self.assertIn('hello, %s' % self.USER_ID, soc_resp)

        # check that user joined channel
        self.assertIn(self.BOOK_ID, self.ws_view.channels)
        self.assertIn(self.ws_view, self.ws_view.channels[self.BOOK_ID])

    def test_02_cmd_lock(self):
        self.ws_view.user_id = self.USER_ID

        # test that sheet is unlocked
        resp = self.client.get('/sheet/view/%s' % SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 0)
        self.assertEqual(resp_json['sheet']['user_id'], None)

        # lock sheet
        self.ws_view.dispatch(
            '#3 lock %s' % SHEET_UUID
        )

        soc_resp = self.ws_view.outbox.pop()
        self.assertIn('3', soc_resp)
        self.assertIn('ok', soc_resp)
        self.assertIn(SHEET_UUID, self.ws_view.current_locks)

        # test that sheet is locked
        resp = self.client.get('/sheet/view/%s' % SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 1)
        self.assertEqual(resp_json['sheet']['user_id'], self.USER_ID)

        # lock the sheet again -> no response
        self.ws_view.dispatch(
            '#3 lock %s' % SHEET_UUID
        )
        self.assertFalse(self.ws_view.outbox)

    def test_03_cmd_lock_locked_sheet(self):
        self.ws_view.user_id = self.USER_ID

        # lock sheet
        self.ws_view.dispatch(
            '#3 lock %s' % LOCKED_SHEET_UUID
        )

        soc_resp = self.ws_view.outbox.pop()
        self.assertIn('-3', soc_resp)
        self.assertIn('sheet %s is already locked.' % LOCKED_SHEET_UUID, soc_resp)

    def test_04_cmd_lock_missing_sheet(self):
        self.ws_view.user_id = self.USER_ID

        # lock sheet
        self.ws_view.dispatch(
            '#3 lock unknownSheetId'
        )

        soc_resp = self.ws_view.outbox.pop()
        self.assertIn('-3', soc_resp)
        self.assertIn('LookupError: unknown sheet unknownSheetId', soc_resp)

    @patch('app.mysocket.rip_book', MagicMock())
    def test_05_cmd_unlock(self):
        resp = self.client.get('/sheet/view/%s' % LOCKED_SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 1)
        self.assertEqual(resp_json['sheet']['user_id'], USER_ID)

        self.ws_view.user_id = USER_ID
        # our locked sheets are in current_locks
        self.ws_view.current_locks.add(LOCKED_SHEET_UUID)

        self.ws_view.dispatch(
            '#3 unlock %s' % LOCKED_SHEET_UUID
        )

        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('3', soc_resp)
        self.assertIn('ok', soc_resp)

        # test that sheet is unlocked
        resp = self.client.get('/sheet/view/%s' % LOCKED_SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 0)
        self.assertEqual(resp_json['sheet']['user_id'], '')

    def test_05_cmd_unlock_sheet_locked_by_other(self):
        self.ws_view.user_id = self.USER_ID

        self.ws_view.dispatch(
            '#3 unlock %s' % LOCKED_SHEET_UUID
        )

        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('-3', soc_resp)
        self.assertIn('cannot unlock %s' % LOCKED_SHEET_UUID, soc_resp)

    @patch('app.mysocket.rip_book', MagicMock())
    def test_06_cmd_force_unlock(self):
        self.ws_view.user_id = self.USER_ID

        self.ws_view.dispatch(
            '#3 force_unlock %s' % LOCKED_SHEET_UUID
        )

        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('3', soc_resp)
        self.assertIn('ok', soc_resp)

        # test that sheet is unlocked
        resp = self.client.get('/sheet/view/%s' % LOCKED_SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 0)
        self.assertEqual(resp_json['sheet']['user_id'], '')

    def test_07_cmd_reacquire(self):
        self.ws_view.user_id = USER_ID
        sheet_version = 7

        self.assertNotIn(LOCKED_SHEET_UUID, self.ws_view.current_locks)

        self.ws_view.dispatch(
            '#3 reacquire %s %s' % (
                LOCKED_SHEET_UUID, sheet_version
            )
        )
        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('3', soc_resp)
        self.assertIn('ok', soc_resp)
        self.assertIn(LOCKED_SHEET_UUID, self.ws_view.current_locks)

    def test_08_cmd_reacquire_changed_sheet(self):
        self.ws_view.user_id = USER_ID
        sheet_version = 3

        self.assertNotIn(LOCKED_SHEET_UUID, self.ws_view.current_locks)

        self.ws_view.dispatch(
            '#3 reacquire %s %s' % (
                LOCKED_SHEET_UUID, sheet_version
            )
        )
        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('-3', soc_resp)
        self.assertIn('The sheet has been changed by another user.', soc_resp)

    def test_09_cmd_reacquire_locked_by_other(self):
        self.ws_view.user_id = self.USER_ID
        sheet_version = 7

        self.assertNotIn(LOCKED_SHEET_UUID, self.ws_view.current_locks)

        self.ws_view.dispatch(
            '#3 reacquire %s %s' % (
                LOCKED_SHEET_UUID, sheet_version
            )
        )
        soc_resp = self.ws_view.outbox.pop()

        self.assertIn('-3', soc_resp)
        self.assertIn('The sheet has been locked by another user.', soc_resp)

    def test_10_cmd_reap(self):
        # reap locks
        self.ws_view.dispatch('#7 reap')

        # test that sheets are unlocked
        resp = self.client.get('/sheet/view/%s' % EXPIRED_LOCKED_SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 0)
        self.assertEqual(resp_json['sheet']['user_id'], '')

        resp = self.client.get('/sheet/view/%s' % LOCKED_SHEET_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json['sheet']['locked'], 1)
        self.assertEqual(resp_json['sheet']['user_id'], USER_ID)
