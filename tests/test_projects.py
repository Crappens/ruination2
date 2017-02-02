"""Test for app.projects
"""

import json
from mock import MagicMock, patch

from app.common.exceptions import InvalidParameterException
from app.common.utils import PageSize, pagesize_map
from app.models import Book
from app.projects.project_api import decode_trim_size, get_svg, on_first_login

from tests import TestCase
from tests.sample_data import (BOOK_UUID, COMPLETED_SHEET, ENFOLD_PROJECT_DATA, EXPIRED_LOCKED_SHEET_UUID,
    LOCKED_SHEET_UUID, PUBLISHED_SHEET, SHEET_UUID, SHEET2_UUID, USER_ID, USER_ID2)


class TestProjectResource(TestCase):

    def test_01_get_project(self):
        resp = self.client.get('/projects/%s' % BOOK_UUID)

        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')

        resp_json = json.loads(resp.data)

        self.assertIn('book', resp_json)
        self.assertEqual(resp_json['book'].get('id'), BOOK_UUID)

        self.assertIn('pageCount', resp_json['book'])
        self.assertIn('userId', resp_json['book'])
        self.assertIn('bookName', resp_json['book'])
        self.assertIn('sheets', resp_json['book'])
        self.assertIn('bingingEdge', resp_json['book'])
        self.assertIn('bookConfig', resp_json['book'])
        self.assertIn('width', resp_json['book'])
        self.assertIn('height', resp_json['book'])
        self.assertIn('coverHidden', resp_json['book'])
        self.assertIn('preferences', resp_json['book'])
        self.assertIn('id', resp_json['book'])
        self.assertIn('updateDate', resp_json['book'])
        self.assertIn('insertDate', resp_json['book'])
        self.assertIn('insertByUserId', resp_json['book'])
        self.assertIn('updateByUserId', resp_json['book'])
        self.assertIn('deletedTimeStamp', resp_json['book'])
        self.assertIn('versionSource', resp_json['book'])
        self.assertIn('version', resp_json['book'])

    def test_02_get_project_not_found(self):
        resp = self.client.get('/projects/1234')
        self.check_404(resp, 'project not found', '1234')

    def test_03_update_project_not_found(self):
        resp = self.client.patch(
            '/projects/1234',
            data=json.dumps({
                'version': 2,
                'cover_options': 'XYZ',
                'endsheet_options': 'BAAN',
                'page_count': 7,
                'preferences': 'my,super,book',
            }),
            headers={'Content-Type': 'application/json',}
        )
        self.check_404(resp, 'project not found', '1234')

    def test_04_update_project(self):
        resp = self.client.patch(
            '/projects/%s' % BOOK_UUID,
            data=json.dumps({
                'version': 2,
                'cover_options': 'XYZ',
                'endsheet_options': 'BAAN',
                'page_count': 7,
                'preferences': 'my,super,book',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')

        resp_json = json.loads(resp.data)

        self.assertIn('project', resp_json)
        self.assertEqual(resp_json['project'].get('id'), BOOK_UUID)
        self.assertEqual(resp_json['project'].get('version'), 2)
        self.assertEqual(resp_json['project'].get('cover_options'), 'XYZ')
        self.assertEqual(resp_json['project'].get('endsheet_options'), 'BAAN')
        self.assertEqual(resp_json['project'].get('pageCount'), 7)
        self.assertEqual(resp_json['project'].get('preferences'), 'my,super,book')

    def test_05_update_project_wrong_patch_options(self):
        resp = self.client.patch(
            '/projects/%s' % BOOK_UUID,
            data=json.dumps({
                'bookName': 'Changed book name',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 400, 'Unexpected status code (!= 400)')

        resp_json = json.loads(resp.data)

        self.assertIn('errors(s)', resp_json)
        errors = resp_json['errors(s)']
        self.assertEqual(len(errors), 1)
        self.assertIn('unknown field(s)', errors[0])
        u_fields = errors[0]['unknown field(s)']
        self.assertEqual(u_fields, ['bookName'])

    def test_06_delete_project(self):
        resp = self.client.delete('/projects/%s' % BOOK_UUID)
        self.assertEqual(resp.status_code, 405, 'Unexpected status code (!= 405)')


class TestBookPreferenceResource(TestCase):

    def test_01_update_book(self):
        resp = self.client.put(
            '/books/preferences/%s.json' % BOOK_UUID,
            data=json.dumps({
                'version': 2,
                'cover_options': 'XYZ',
                'endsheet_options': 'BAAN',
                'page_count': 7,
                'preferences': 'my,super,book',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json, dict(message=True))

        # load boook and check things were changed
        resp = self.client.get('/projects/%s' % BOOK_UUID)
        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertIn('book', resp_json)
        self.assertEqual(resp_json['book'].get('id'), BOOK_UUID)
        self.assertEqual(resp_json['book'].get('version'), 3)
        self.assertEqual(resp_json['book'].get('cover_options'), 'XYZ')
        self.assertEqual(resp_json['book'].get('endsheet_options'), 'BAAN')
        self.assertEqual(resp_json['book'].get('pageCount'), 7)
        self.assertEqual(resp_json['book'].get('preferences'), 'my,super,book')

    def test_02_update_unknown_book(self):
        resp = self.client.put(
            '/books/preferences/%s.json' % 'testBook',
            data=json.dumps({
                'cover_options': 'changed me',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.check_404(resp, 'project', 'testBook')


class TestSheetResource(TestCase):

    def test_01_get_sheet(self):
        resp = self.client.get('/sheet/view/%s' % SHEET_UUID)

        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')

        resp_json = json.loads(resp.data)

        self.assertIn('sheet', resp_json)
        self.assertEqual(resp_json['sheet'].get('id'), SHEET_UUID)

    def test_02_get_sheet_not_found(self):
        resp = self.client.get('/sheet/view/1234')
        self.check_404(resp, 'sheet not found', '1234')

    def test_03_update_sheet_not_found(self):
        resp = self.client.put(
            '/sheet/view/1234',
            data=json.dumps({
                'hidden': False,
                'version': 1,
                'status': 'ready',
                'type': 'SHEET',
                'page': 7,
                'user_id': '123456789',
                'completed': True,
                'locked': True,
            }),
            headers={'Content-Type': 'application/json',}
        )
        self.check_404(resp, 'sheet not found', '1234')

    def test_04_update_sheet(self):
        resp = self.client.put(
            '/sheet/view/%s' % SHEET_UUID,
            data=json.dumps({
                'hidden': False,
                'version': 3,
                'status': 'ready',
                'type': 'SHEET',
                'page': 7,
                'user_id': '123456789',
                'completed': False,
                'locked': True,
                'spread_name': 'Test Spread',
                'due_date': '2011-11-11 00:00:00',
                'approval_status': 'Approved',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json, {'completed': 0, 'version': 4})

        resp = self.client.put(
            '/sheet/view/%s' % SHEET_UUID,
            data=json.dumps({
                'hidden': False,
                'version': 7,
                'status': 'ready',
                'type': 'SHEET',
                'page': 7,
                'user_id': '123456789',
                'completed': True,
                'locked': True,
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 200, 'Unexpected status code (!= 200)')
        resp_json = json.loads(resp.data)
        self.assertEqual(resp_json, {'completed': 1, 'version': 8})

    def test_05_update_sheet_wrong_patch_options(self):
        resp = self.client.put(
            '/sheet/view/%s' % SHEET_UUID,
            data=json.dumps({
                'width': 99,
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 400, 'Unexpected status code (!= 400)')

        resp_json = json.loads(resp.data)

        self.assertIn('errors(s)', resp_json)
        errors = resp_json['errors(s)']
        self.assertEqual(len(errors), 1)
        self.assertIn('unknown field(s)', errors[0])
        u_fields = errors[0]['unknown field(s)']
        self.assertEqual(u_fields, ['width'])

    def test_06_update_sheet_locked(self):
        resp = self.client.put(
            '/sheet/view/%s' % LOCKED_SHEET_UUID,
            data=json.dumps({
                'hidden': False,
                'version': 3,
                'status': 'ready',
                'type': 'SHEET',
                'page': 7,
                'user_id': '123456789',
                'completed': False,
                'locked': False,
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 400, 'Unexpected status code (!= 400)')
        self.assertTrue('Unable to modify locked resource.' in resp.data)

    def test_07_delete_sheet(self):
        resp = self.client.delete('/sheet/view/%s' % SHEET_UUID)
        self.assertEqual(resp.status_code, 405, 'Unexpected status code (!= 405)')

    def test_08_update_sheet_invalid_due_date(self):
        resp = self.client.put(
            '/sheet/view/%s' % SHEET_UUID,
            data=json.dumps({
                'due_date': '2011-11-111',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 400, 'Unexpected status code (!= 400)')

    def test_09_update_sheet_invalid_approval_status(self):
        resp = self.client.put(
            '/sheet/view/%s' % SHEET_UUID,
            data=json.dumps({
                'approval_status': 'Test',
            }),
            headers={'Content-Type': 'application/json',}
        )

        self.assertEqual(resp.status_code, 400, 'Unexpected status code (!= 400)')


response_mock = MagicMock()
response_mock.json = MagicMock(return_value=ENFOLD_PROJECT_DATA)
requests_get_mock = MagicMock(return_value=response_mock)


class TestProjectApi(TestCase):

    def test_01_decode_trim_size(self):
        pagesize = decode_trim_size('8')

        self.assertIsNotNone(pagesize)
        self.assertIsInstance(pagesize, PageSize)
        self.assertIsNotNone(pagesize.height)
        self.assertIsNotNone(pagesize.width)

    def test_02_bad_trim_size(self):
        self.assertRaises(InvalidParameterException, decode_trim_size, '9090')
        self.assertRaises(InvalidParameterException, decode_trim_size, 8)

    @patch('app.projects.project_api.requests.get', requests_get_mock)
    @patch('app.projects.project_api.rip_book', MagicMock())
    def test_03_on_first_login(self):
        new_book = on_first_login(
            user_id='myTestUserId42',
            project_number='633777'
        )

        self.assertIsInstance(new_book, Book)
        self.assertEqual(new_book.number, '633777')
        self.assertEqual(new_book.user_id, 'myTestUserId42')
        self.assertEqual(len(new_book.sheets), 52)

        # check sheets ordering
        sheets = new_book.sheets[:]

        cover_sheet = sheets.pop(0)
        first_sheet = sheets.pop(0)
        last_sheet = sheets.pop(-1)

        self.assertEqual(cover_sheet.type, "COVER")
        self.assertIsNone(cover_sheet.parent_sheet)
        self.assertEqual(cover_sheet.sort_order, 0)

        self.assertEqual(first_sheet.type, "FIRST_SHEET")
        self.assertEqual(first_sheet.parent_sheet, cover_sheet.id)
        self.assertEqual(first_sheet.sort_order, 1)

        current_sheet = first_sheet

        for index, sheet in enumerate(sheets, start=2):
            self.assertEqual(sheet.type, "SHEET")
            self.assertEqual(sheet.sort_order, index)
            self.assertEqual(current_sheet.id, sheet.parent_sheet)

            current_sheet = sheet

        self.assertEqual(last_sheet.type, "LAST_SHEET")
        self.assertEqual(last_sheet.parent_sheet, current_sheet.id)
        self.assertEqual(last_sheet.sort_order, len(new_book.sheets) - 1)

    @patch('app.projects.project_api.requests.get', requests_get_mock)
    @patch('app.projects.project_api.rip_book', MagicMock(side_effect=ValueError))
    def test_04_on_first_login_existing_book(self):
        new_book = on_first_login(
            user_id='myTestUserId42',
            project_number='112234'
        )

        self.assertIsInstance(new_book, Book)
        self.assertEqual(new_book.number, '112234')
        self.assertEqual(len(new_book.sheets), 0)

    def test_05_get_svg_cover_and_sheet(self):
        expected_svg = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:se="http://svg-edit.googlecode.com" xmlns:lyb="http://www.myyear.com" width="1260" height="828">
<g id="background_layer"><title>Background</title>
<g lyb:dropTarget="g" id="background_group_F"><rect lyb:background="F" lyb:dropTarget="border" id="background_F" y="0" x="0" width="1260" height="828"  fill="none" stroke="none" /></g>
<g lyb:dropTarget="g" id="background_group_L"><rect lyb:background="L" lyb:dropTarget="border" id="background_L" y="0" x="0" width="630" height="828"  fill="none" stroke="none" /></g>
<g lyb:dropTarget="g" id="background_group_R"><rect lyb:background="R" lyb:dropTarget="border" id="background_R" y="0" x="630" width="630" height="828"  fill="none" stroke="none" /></g>
</g>
<g id="layer_1"><title>Layer 1</title></g>
<g se:guide="true" se:lock="L" id="guide_LEFT"><title>Safety Zone LEFT</title>
<rect id="guide_FULL_rect" y="0" x="0" width="1260" height="828" stroke="#0000FF" fill="none"/>
<rect id="guide_LEFT_CUT_rect" y="18" x="18" width="612" height="792" stroke="#00FF00" fill="none"/>
<rect id="guide_LEFT_SAFETY_rect" y="36" x="36" width="585" height="756" stroke="#0000FF" fill="none"/>
</g>
<g se:guide="true" se:lock="L" id="guide_RIGHT"><title>Safety Zone RIGHT</title>
<rect id="guide_RIGHT_CUT_rect" y="18" x="630" width="612" height="792" stroke="#00FF00" fill="none"/>
<rect id="guide_RIGHT_SAFETY_rect" y="36" x="639" width="585" height="756" stroke="#0000FF" fill="none"/>
</g>
<g se:guide="true" se:lock="L" id="gg_layer"><title>MY Grid and Guides Layer</title>
<rect id="guide_FULL_BLEED_rect" y="9" x="9" width="1242" height="810" stroke="#FF0000" stroke-width="18" opacity="0.5" fill="none"/></g>
<g se:lock="L" id="folio_layer"><title>Folio Layer</title>
<text height="10" width="100" y="792" x="36" stroke-width="0" fill="none" id="ft_l"><tspan xml:space="preserve" id="fts_l" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0" x="36">LEFT_FOLIO</tspan></text><text height="10" width="100" y="792" x="1224" text-anchor="end" stroke-width="0" fill="none" id="ft_r"><tspan xml:space="preserve" id="fts_r" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0" x="1224">RIGHT_FOLIO</tspan></text></g>
</svg>'''
        ps = pagesize_map.get('8')

        result_svg = get_svg(ps, 'COVER', False)
        self.assertEqual(expected_svg, result_svg, 'cover')

        result_svg = get_svg(ps, 'SHEET', False)
        self.assertEqual(expected_svg, result_svg, 'sheet')

    def test_06_get_svg_first_sheet(self):
        expected_svg = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:se="http://svg-edit.googlecode.com" xmlns:lyb="http://www.myyear.com" width="1260" height="828">
<g id="background_layer"><title>Background</title>
<g lyb:dropTarget="g" id="background_group_F"><rect lyb:background="F" lyb:dropTarget="border" id="background_F" y="0" x="0" width="1260" height="828"  fill="none" stroke="none" /></g>
<g lyb:dropTarget="g" id="background_group_L"><rect lyb:background="L" lyb:dropTarget="border" id="background_L" y="0" x="0" width="630" height="828"  fill="none" stroke="none" /></g>
<g lyb:dropTarget="g" id="background_group_R"><rect lyb:background="R" lyb:dropTarget="border" id="background_R" y="0" x="630" width="630" height="828"  fill="none" stroke="none" /></g>
</g>
<g id="layer_1"><title>Layer 1</title></g>
<g se:guide="true" se:lock="L" id="empty_page_left"><title>Empty Page LEFT</title>
<rect id="guide_LEFT_rect" y="0" x="0" width="630" height="828" fill="#363637"/></g>
<g se:guide="true" se:lock="L" id="guide_RIGHT"><title>Safety Zone RIGHT</title>
<rect id="guide_RIGHT_CUT_rect" y="18" x="630" width="612" height="792" stroke="#00FF00" fill="none"/>
<rect id="guide_RIGHT_SAFETY_rect" y="36" x="639" width="585" height="756" stroke="#0000FF" fill="none"/>
</g>
<g se:guide="true" se:lock="L" id="gg_layer"><title>MY Grid and Guides Layer</title>
<rect id="guide_FULL_BLEED_rect" y="9" x="9" width="1242" height="810" stroke="#FF0000" stroke-width="18" opacity="0.5" fill="none"/></g>
<g se:lock="L" id="folio_layer"><title>Folio Layer</title>
<text height="10" width="100" y="792" x="36" stroke-width="0" fill="none" id="ft_l"><tspan xml:space="preserve" id="fts_l" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0" x="36"></tspan></text><text height="10" width="100" y="792" x="1224" text-anchor="end" stroke-width="0" fill="none" id="ft_r"><tspan xml:space="preserve" id="fts_r" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0" x="1224">RIGHT_FOLIO</tspan></text></g>
</svg>'''
        ps = pagesize_map.get('8')

        result_svg = get_svg(ps, 'FIRST_SHEET', False)
        self.assertEqual(expected_svg, result_svg)

    def test_07_get_svg_last_sheet(self):
        expected_svg = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:se="http://svg-edit.googlecode.com" xmlns:lyb="http://www.myyear.com" width="1260" height="828">
<g id="background_layer"><title>Background</title>
<g lyb:dropTarget="g" id="background_group_F"><rect lyb:background="F" lyb:dropTarget="border" id="background_F" y="0" x="0" width="1260" height="828"  fill="none" stroke="none" /></g>
<g lyb:dropTarget="g" id="background_group_L"><rect lyb:background="L" lyb:dropTarget="border" id="background_L" y="0" x="0" width="630" height="828"  fill="none" stroke="none" /></g>
<g lyb:dropTarget="g" id="background_group_R"><rect lyb:background="R" lyb:dropTarget="border" id="background_R" y="0" x="630" width="630" height="828"  fill="none" stroke="none" /></g>
</g>
<g id="layer_1"><title>Layer 1</title></g>
<g se:guide="true" se:lock="L" id="guide_LEFT"><title>Safety Zone LEFT</title>
<rect id="guide_FULL_rect" y="0" x="0" width="1260" height="828" stroke="#0000FF" fill="none"/>
<rect id="guide_LEFT_CUT_rect" y="18" x="18" width="612" height="792" stroke="#00FF00" fill="none"/>
<rect id="guide_LEFT_SAFETY_rect" y="36" x="36" width="585" height="756" stroke="#0000FF" fill="none"/>
</g>
<g se:guide="true" se:lock="L" id="empty_page_right"><title>Empty Page RIGHT</title>
<rect id="guide_RIGHT_rect" y="0" x="630" width="630" height="828" fill="#363637"/></g>
<g se:guide="true" se:lock="L" id="gg_layer"><title>MY Grid and Guides Layer</title>
<rect id="guide_FULL_BLEED_rect" y="9" x="9" width="1242" height="810" stroke="#FF0000" stroke-width="18" opacity="0.5" fill="none"/></g>
<g se:lock="L" id="folio_layer"><title>Folio Layer</title>
<text height="10" width="100" y="792" x="36" stroke-width="0" fill="none" id="ft_l"><tspan xml:space="preserve" id="fts_l" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0" x="36">LEFT_FOLIO</tspan></text><text height="10" width="100" y="792" x="1224" text-anchor="end" stroke-width="0" fill="none" id="ft_r"><tspan xml:space="preserve" id="fts_r" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0" x="1224"></tspan></text></g>
</svg>'''
        ps = pagesize_map.get('8')

        result_svg = get_svg(ps, 'LAST_SHEET', False)
        self.assertEqual(expected_svg, result_svg)


class TestClearSheet(TestCase):

    def test_01_clear_sheet(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('1', resp_json['result'])

    def test_02_clear_sheets(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID, SHEET2_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('2', resp_json['result'])

    def test_03_clear_locked_sheet(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [LOCKED_SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID2,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn(LOCKED_SHEET_UUID, resp_json['Error'])

    def test_04_clear_completed_sheet(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [COMPLETED_SHEET],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn(COMPLETED_SHEET, resp_json['Error'])

    def test_05_clear_published_sheet(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [PUBLISHED_SHEET],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn(PUBLISHED_SHEET, resp_json['Error'])

    def test_06_clear_sheet_without_user_id_header(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn('user-id', resp_json['Error'])

    def test_07_clear_locked_sheet_by_other_user(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [LOCKED_SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID2,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn(LOCKED_SHEET_UUID, resp_json['Error'])

    def test_08_clear_locked_sheet(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [LOCKED_SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('1', resp_json['result'])

    def test_09_clear_expired_locked_sheet(self):
        resp = self.client.post(
            '/sheet/clear',
            data=json.dumps({
                'sheets_ids': [EXPIRED_LOCKED_SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID2,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('1', resp_json['result'])


class TestAprpoveSheet(TestCase):

    def test_01_approve_sheet(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID],
                'approval_status': 'Approved',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('1', resp_json['result'])

        resp = self.client.get('/sheet/view/%s' % SHEET_UUID)

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('sheet', resp_json)
        self.assertEqual(resp_json['sheet'].get('approval_status'), 'Approved')

    def test_02_approve_sheets(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID, SHEET2_UUID],
                'approval_status': 'Free',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('2', resp_json['result'])

        resp = self.client.get('/sheet/view/%s' % SHEET_UUID)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('sheet', resp_json)
        self.assertEqual(resp_json['sheet'].get('approval_status'), 'Free')

        resp = self.client.get('/sheet/view/%s' % SHEET2_UUID)
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('sheet', resp_json)
        self.assertEqual(resp_json['sheet'].get('approval_status'), 'Free')

    def test_03_approve_sheet_missing_sheets_ids(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'approval_status': 'Approved',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn('sheets_ids', resp_json['Error'])

    def test_04_approve_sheet_missing_approval_status(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID],
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn('approval_status', resp_json['Error'])

    def test_05_approve_sheet_invalid_approve_status(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID],
                'approval_status': 'Unknown',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn('Unknown', resp_json['Error'])

    def test_06_approve_sheet_unknown_sheet(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID, 'Unknown'],
                'approval_status': 'Free',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn('Unknown', resp_json['Error'])

    def test_07_approve_sheet_without_user_id(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [SHEET_UUID],
                'approval_status': 'Free',
            }),
            headers={
                'Content-Type': 'application/json',
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn('user-id', resp_json['Error'])

    def test_08_approve_locked_sheet(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [LOCKED_SHEET_UUID],
                'approval_status': 'Active',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID,
            }
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('result', resp_json)
        self.assertIn('1', resp_json['result'])

        resp = self.client.get('/sheet/view/%s' % LOCKED_SHEET_UUID)

        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.data)
        self.assertIn('sheet', resp_json)
        self.assertEqual(resp_json['sheet'].get('approval_status'), 'Active')

    def test_09_approve_locked_sheet_by_other_user(self):
        resp = self.client.post(
            '/sheet/update',
            data=json.dumps({
                'sheets_ids': [LOCKED_SHEET_UUID],
                'approval_status': 'Free',
            }),
            headers={
                'Content-Type': 'application/json',
                'user-id': USER_ID2,
            }
        )

        self.assertEqual(resp.status_code, 400)
        resp_json = json.loads(resp.data)
        self.assertIn('Error', resp_json)
        self.assertIn(LOCKED_SHEET_UUID, resp_json['Error'])
