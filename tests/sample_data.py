"""Sample data for ruination unit tests.
"""

BOOK_UUID = '002f60ef38a841f28497b30dac37c026'
USER_ID = '583579e4837a4d5aa1ed087567bf0aef'
USER_ID2 = '796e4460f323463389de87f978cefc56'

SHEET_UUID = '5dd020b494a2445081d8fdcbc3adbca1'
SHEET2_UUID = 'c52fc66234de4d53b035edc01f3b61fa'
LOCKED_SHEET_UUID = '3137ca9964b4447fbc8f69a51b131c0f'
EXPIRED_LOCKED_SHEET_UUID = '92553ba9b7b74b0c8265d3eadc9404f0'
COMPLETED_SHEET = '909425baa37e4471aee8fbf25cf31d0a'
PUBLISHED_SHEET = '8b1ea04c9ea94f34b83d35a95b2069cb'


B4PUB_SAMPLE_DATA_SQL_HEADERS = [
    "INSERT INTO `book` (`id`, `number`, `trim_size`, `page_count`) VALUES %s",
    "INSERT INTO `sheet` (`id`, `locked`, `sort_order`, `svg`, `user_id`, `version`, `locked_until`, `book_id`, `completed`, `status`, `proofed`) VALUES %s",
    "INSERT INTO `project_status` (`project_status_id`, `project_status_name`) VALUES %s",
    "INSERT INTO `user` (`user_id`,`user_type_id`,`user_uuid`,`user_first_name`,`user_last_name`,`user_email`,`user_name`) VALUES %s",
    "INSERT INTO `project` (`project_id`, `school_id`, `project_uuid`, `project_number`, `project_name`, `project_year`) VALUES %s",
]


B4PUB_SAMPLE_DATA_SQL_VALUES = [
    (
        "('%s', '112233', '7', 100)" % BOOK_UUID,
        "('bb4cf69cf93340fba2cbd6f2d910eea9', '112234', '7', 100)",
    ), (
        "('%s', 0, 0, '<svg/>', null, 7, null, '%s', 0, null, 1)" % (SHEET_UUID, BOOK_UUID),
        "('%s', 0, 0, '<svg/>', null, 7, null, '%s', 0, null, 0)" % (SHEET2_UUID, BOOK_UUID),
        "('%s', 1, 0, '<svg/>', '%s', 7, '2077-11-11 11:11:11', '%s', 0, null, 0)" % (LOCKED_SHEET_UUID, USER_ID, BOOK_UUID),
        "('%s', 1, 0, '<svg/>', '%s', 7, '2011-11-11 11:11:11', '%s', 0, null, 0)" % (EXPIRED_LOCKED_SHEET_UUID, USER_ID, BOOK_UUID),
        "('%s', 0, 0, '<svg/>', null, 7, null, '%s', 1, null, 0)" % (COMPLETED_SHEET, BOOK_UUID),
        "('%s', 0, 0, '<svg/>', null, 7, null, '%s', 0, 'PUBLISHED', 0)" % (PUBLISHED_SHEET, BOOK_UUID),
    ), (
        "(0, 'Unused')",
        "(1, 'Free')",
        "(2, 'Active')",
        "(3, 'Approved')",
    ), (
        "(1, 1, '%s', 'Alice', 'Tester', 'alice.tester@test.com', 'tester_alice')" % USER_ID,
        "(2, 1, '%s', 'Bob', 'Tester', 'bob.tester@test.com', 'tester_bob')" % USER_ID2,
    ), (
        "(1, 1, 'b7b801fa3b914fdd8d9422ea1c512954', '633777', '2016 Tester High 33777', 2016)",
        "(2, 2, 'bb4cf69cf93340fba2cbd6f2d910eea9', '112234', '2016 Tester High 12234', 2016)",
    ),
]


ENFOLD_PROJECT_DATA = {
    'project': {
        'address': '333 Tester Street',
        'address2': None,
        'adviser': 'Tester Adviser',
        'adviser_email': 'adviser@tester.com',
        'ae_email': 'ae@tester.com',
        'ae_name': 'Tester Ae',
        'ae_number': '123456',
        'ae_phone': '111-222-3333',
        'bind_type': '3',
        'cover_design': 'sch',
        'cust_copies': 167,
        'customer': '33777',
        'customer_name': 'Tester High',
        'description': '2016 Tester High',
        'enabled': True,
        'es_design': 'so',
        'id': 'b7b801fa3b914fdd8d9422ea1c512954',
        'name': '2016 Tester High 33777',
        'number': '633777',
        'pages': 100,
        'product_line': 'spc',
        'region': '2',
        'rep_email': 'rep@tester.com',
        'rep_name': 'Tester Rep',
        'rep_number': '654321',
        'rep_phone': '111-222-3333',
        'season': '2',
        'smi_number': '98765',
        'software': 'sw',
        'stage': None,
        'store': 'sp',
        'trim_size': '8',
        'variant': '155992',
        'year': 2016,
    }
}
