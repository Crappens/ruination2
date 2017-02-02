from marshmallow import Schema, fields


class SheetSchema(Schema):

    hidden = fields.Boolean(required=False)
    version = fields.Integer(required=True)
    project_id = fields.String(required=True)
    bookId = fields.String(attribute='book_id')
    status = fields.String(required=True, default="PENDING")
    type = fields.String(required=True, default="SHEET")
    svg = fields.String(required=True)
    lowSVG = fields.String(attribute='svg')
    parent_sheet = fields.String(required=True, default=None)
    sort_order = fields.Integer(required=True)
    active = fields.Boolean(required=True, default=False)
    completed = fields.Boolean(required=True, default=False)
    locked = fields.Boolean(required=True, default=False)
    user_id = fields.String(required=True)

    class Meta:
        fields = (
            "id", "hidden", "version", "project_id", "status", "type", "page",
            "thumbnail_url", "parent_sheet", "sort_order", "active", "completed", "locked",
            "width", "height", "bleed_margin", "user_id", 'bookId', 'lowSVG'
        )


class ProjectSchema(Schema):

    sheets = fields.Nested(SheetSchema, many=True)
    user_id = fields.String(required=True)
    bookName = fields.String(required=True, attribute='name')
    number = fields.String(required=True)
    width = fields.Integer(required=True)
    heigth = fields.Integer(required=True)
    pageCount = fields.Integer(required=True, attribute='page_count')
    bleedMargin = fields.String(attribute='bleed_margin')
    trim_size = fields.String(required=True)
    userId = fields.String(required=True, attribute='user_id')
    updateDate = fields.String(attribute='updated')
    insertDate = fields.String(attribute='created')
    insertByUserId = fields.String(default=None)
    updateByUserId = fields.String(default=None)
    deletedTimeStamp = fields.String(default=None)
    versionSource = fields.String(default=None)
    version = fields.Integer(default=0)
    preferences = fields.String(default="")
    bingingEdge = fields.String(default='side')
    bookConfig = fields.String(default=None)
    coverHidden = fields.Boolean(default=False)

    class Meta:
        fields = (
            "id", "number", "bookName", "width", "height", "bleedMargin", "cover_options",
            "endsheet_options", "pageCount", "trim_size", "sheets", "userId", 'updateDate',
            'insertDate', 'insertByUserId', 'updateByUserId', 'deletedTimeStamp', 'versionSource',
            'version', 'preferences', 'bingingEdge', 'bookConfig', 'coverHidden'
        )
