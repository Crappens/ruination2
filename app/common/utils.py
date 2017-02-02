import calendar
import datetime
import time
import iso8601
import six
import uuid

from collections import namedtuple

from flask import jsonify, current_app, request
from lxml import etree

# ISO 8601 extended time format with microseconds
_ISO8601_TIME_FORMAT_SUBSECOND = '%Y-%m-%dT%H:%M:%S.%f'
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
PERFECT_TIME_FORMAT = _ISO8601_TIME_FORMAT_SUBSECOND

# TODO: NEW PAGE SIZES FOR SPREAD SIZING UPDATES
pagesize_map_new = {
    # Dict to map known page sizes.
    # Here inches are converted to points, width is doubled and the bleed is added.
    '7': (int(36 + 144 * 7.75), int(36 + 72 * 10.5)),
    '8': (int(36 + 144 * 8.5), int(36 + 72 * 11)),
    '9': (int(36 + 144 * 9.0), int(36 + 72 * 12.0))
}

PageSize = namedtuple("PageSize", "width, height")

pagesize_map = {
    # Dict to map known page sizes.
    # Here inches are converted to points, width is doubled and the bleed is added.
    '7': PageSize(int(36 + 144 * 7.75), int(36 + 72 * 10.5)),
    '8': PageSize(int(36 + 144 * 8.5), int(36 + 72 * 11.0)),
    '9': PageSize(int(36 + 144 * 9.0), int(36 + 72 * 12.0))
}

pixelconversion_map = {
    1152: {'height': 10.5, 'width': 7.75, 'trim_size': '7'},  # Height and width are sans-bleed border
    1260: {'height': 11.0, 'width': 8.5, 'trim_size': '8'},  # Add half an inch to both for spread size
    1332: {'height': 12.0, 'width': 9.0, 'trim_size': '9'}
}


def fix_clippaths(svg):
    base = etree.fromstring(svg)
    defs = [x for x in list(base) if "defs" in str(x.tag)]
    if len(defs) != 1:
        return svg
    else:
        defs = defs[0]
        if any(["use" in str(x) for x in list(defs)]):
            new_defs = etree.Element("defs")
            for x in list(defs):
                if "use" in x.tag:
                    c_id = x.get("id").replace("use", "clipPath")
                    c_path = etree.SubElement(new_defs, "clippath", id=c_id)
                    c_use = etree.SubElement(c_path, "use", id=x.get("id"))
                    c_use.set("{http://www.w3.org/1999/xlink}href", x.get("{http://www.w3.org/1999/xlink}href"))
                else:
                    new_defs.append(x)
            if len(list(new_defs)) > 0:
                base.remove(defs)
                base.insert(1, new_defs)
            return etree.tostring(base)
        else:
            return svg


def remove_broken_filters(svg):
    base = etree.fromstring(svg)
    defs = [x for x in list(base) if "defs" in str(x.tag)]
    layer_1 = [x for x in list(base) if x.get("id") == "layer_1"]
    filters_to_remove = []
    if len(defs) != 1:
        return svg
    else:
        defs = defs[0]
        if any(["filter" in str(x) for x in list(defs)]):
            new_defs = etree.Element("defs")
            for x in list(defs):
                if "filter" in x.tag:
                    print list(x)
                    if len(list(x)) != 0:
                        new_defs.append(x)
                    else:
                        filters_to_remove.append(x.get("id"))
                else:
                    new_defs.append(x)
            for item in base.iterfind(".//{http://www.w3.org/2000/svg}g[@filter]"):
                if any([x in item.get("filter") for x in filters_to_remove]):
                    del item.attrib["filter"]
            base.remove(defs)
            base.insert(1, new_defs)
            return etree.tostring(base)
        else:
            return svg


# Strips newlines, tabs and all extra spacing out of the prettified lxml etree
def stringify(prettified):
    finalized = prettified.replace('\n', '').replace('\t', '')
    while ' <' in finalized or '> ' in finalized:
        finalized = finalized.replace(' <', '<')
        finalized = finalized.replace('> ', '>')
    return finalized


def scale_spread(svg, height_ratio, width_ratio, new_height_width, new_svg):
    svg.set("height", str(new_height_width.height))
    svg.set("width", str(new_height_width.width))
    new_layer_1 = next((x for x in list(new_svg) if x.get("id") == "layer_1"), None)
    new_svg.remove(new_layer_1)
    old_defs = next((x for x in list(svg) if "defs" in str(x.tag)), None)
    if old_defs is not None:
        new_svg.insert(1, old_defs)
    added_flow_to_new = False
    for layer in list(svg):
        layer_id = layer.get("id")
        if layer_id in ("layer_1", "flowing_layer"):
            for obj in layer.getiterator():
                if "title" in obj.tag:
                    continue
                if obj.get("id") == "layer_1":
                    continue
                x = obj.get("x")
                y = obj.get("y")
                height = obj.get("height")
                width = obj.get("width")
                x1 = obj.get("x1")
                y1 = obj.get("y1")
                x2 = obj.get("x2")
                y2 = obj.get("y2")
                cx = obj.get("cx")
                cy = obj.get("cy")
                rx = obj.get("rx")
                ry = obj.get("ry")
                for value in [("x", x), ("y", y), ("height", height), ("width", width), ("x1", x1), ("y1", y1),
                              ("x2", x2), ("y2", y2), ("cx", cx), ("cy", cy), ("rx", rx), ("ry", ry)]:
                    if any(i in value[0] for i in ["x", "width"]) and value[1] is not None:
                        obj.set(value[0], str(float(value[1]) * width_ratio))
                    if any(i in value[0] for i in ["y", "height"]) and value[1] is not None:
                        obj.set(value[0], str(float(value[1]) * height_ratio))
            if layer_id == "layer_1":
                if old_defs is not None:
                    if added_flow_to_new:
                        new_svg.insert(3, layer)
                    else:
                        new_svg.insert(2, layer)
                else:
                    if added_flow_to_new:
                        new_svg.insert(2, layer)
                    else:
                        new_svg.insert(1, layer)
            if layer_id == "flowing_layer":
                if old_defs is not None:
                    new_svg.insert(2, layer)
                else:
                    new_svg.insert(1, layer)
                added_flow_to_new = True
        if layer_id == "background_layer":
            for obj in layer.getiterator():
                if obj.get("id") == "background_F":
                    obj.set("height", str(new_height_width.height))
                    obj.set("width", str(new_height_width.width))
                if obj.get("id") == "background_L":
                    obj.set("height", str(new_height_width.height))
                    obj.set("width", str(new_height_width.width / 2))
                if obj.get("id") == "background_R":
                    obj.set("height", str(new_height_width.height))
                    obj.set("width", str(new_height_width.width / 2))
                    obj.set("x", str(new_height_width.width / 2))
                if "image" in obj.tag:
                    if int(obj.get("x")) == -10:
                        ratio = float(obj.get("height")) / float(obj.get("width"))
                        obj.set("width", str(new_height_width.width + 10))
                        img_width = float(obj.get("width"))
                        obj.set("height", str(img_width * ratio))
                        img_height = float(obj.get("height"))
                        obj.set("y", str(int((new_height_width.height - img_height) / 2)))
                        rect_sibling = list(obj.getparent().getparent())[1]
                        rect_x = new_height_width.width / 2 if int(rect_sibling.get("x")) > 500 else 0
                        full = obj.getparent().getparent().getparent().get("id").split("_")[-1] == "F"
                        rect_sibling.set("x", str(rect_x))
                        rect_sibling.set("height", str(new_height_width.height))
                        rect_sibling.set("width",
                                         str(new_height_width.width / 2) if not full else str(new_height_width.width))
                    elif int(obj.get("y")) == -10:
                        ratio = float(obj.get("width")) / float(obj.get("height"))
                        obj.set("height", str(new_height_width.height + 10))
                        img_height = float(obj.get("height"))
                        obj.set("width", str(img_height * ratio))
                        img_width = float(obj.get("width"))
                        obj.set("x", str(int((new_height_width.width - img_width) / 2)))
                        rect_sibling = list(obj.getparent().getparent())[1]
                        full = obj.getparent().getparent().getparent().get("id").split("_")[-1] == "F"
                        rect_x = new_height_width.width / 2 if int(rect_sibling.get("x")) > 0 else 0
                        rect_sibling.set("x", str(rect_x))
                        rect_sibling.set("height", str(new_height_width.height))
                        rect_sibling.set("width",
                                         str(new_height_width.width / 2) if not full else str(new_height_width.width))
                    else:
                        rect_sibling = list(obj.getparent().getparent())[1]
                        rect_x = new_height_width.width / 2 if int(rect_sibling.get("x")) > 500 else 0
                        full = obj.getparent().getparent().getparent().get("id").split("_")[-1] == "F"
                        rect_sibling.set("x", str(rect_x))
                        rect_sibling.set("height", str(new_height_width.height))
                        rect_sibling.set("width",
                                         str(new_height_width.width / 2) if not full else str(new_height_width.width))
                        obj.set("width", rect_sibling.get("width"))
                        obj.set("height", rect_sibling.get("height"))
                        obj.set("x", rect_sibling.get("x"))

            new_svg.remove(next((x for x in list(new_svg) if x.get("id") == "background_layer"), None))
            new_svg.insert(0, layer)

    return stringify(etree.tostring(new_svg, pretty_print=True))


def isotime(at=None, subsecond=False):
    """Stringify time in ISO 8601 format."""
    if not at:
        at = utcnow()
    st = at.strftime(_ISO8601_TIME_FORMAT
                     if not subsecond
                     else _ISO8601_TIME_FORMAT_SUBSECOND)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if tz == 'UTC' else tz)
    return st


def parse_isotime(timestr):
    """Parse time from ISO 8601 format."""
    try:
        return iso8601.parse_date(timestr)
    except iso8601.ParseError as e:
        raise ValueError(six.text_type(e))
    except TypeError as e:
        raise ValueError(six.text_type(e))


def strtime(at=None, fmt=PERFECT_TIME_FORMAT):
    """Returns formatted utcnow."""
    if not at:
        at = utcnow()
    return at.strftime(fmt)


def parse_strtime(timestr, fmt=PERFECT_TIME_FORMAT):
    """Turn a formatted time back into a datetime."""
    return datetime.datetime.strptime(timestr, fmt)


def normalize_time(timestamp):
    """Normalize time in arbitrary timezone to UTC naive object."""
    offset = timestamp.utcoffset()
    if offset is None:
        return timestamp
    return timestamp.replace(tzinfo=None) - offset


def is_older_than(before, seconds):
    """Return True if before is older than seconds."""
    if isinstance(before, six.string_types):
        before = parse_strtime(before).replace(tzinfo=None)
    return utcnow() - before > datetime.timedelta(seconds=seconds)


def is_newer_than(after, seconds):
    """Return True if after is newer than seconds."""
    if isinstance(after, six.string_types):
        after = parse_strtime(after).replace(tzinfo=None)
    return after - utcnow() > datetime.timedelta(seconds=seconds)


def utcnow_ts():
    """Timestamp version of our utcnow function."""
    if utcnow.override_time is None:
        # NOTE(kgriffs): This is several times faster
        # than going through calendar.timegm(...)
        return int(time.time())

    return calendar.timegm(utcnow().timetuple())


def utcnow():
    """Overridable version of utils.utcnow."""
    if utcnow.override_time:
        try:
            return utcnow.override_time.pop(0)
        except AttributeError:
            return utcnow.override_time
    return datetime.datetime.utcnow()


def iso8601_from_timestamp(timestamp):
    """Returns a iso8601 formated date from timestamp."""
    return isotime(datetime.datetime.utcfromtimestamp(timestamp))


utcnow.override_time = None


def set_time_override(override_time=None):
    """Overrides utils.utcnow.

    Make it return a constant time or a list thereof, one at a time.

    :param override_time: datetime instance or list thereof. If not
                          given, defaults to the current UTC time.
    """
    utcnow.override_time = override_time or datetime.datetime.utcnow()


def advance_time_delta(timedelta):
    """Advance overridden time using a datetime.timedelta."""
    assert(utcnow.override_time is not None)
    try:
        for dt in utcnow.override_time:
            dt += timedelta
    except TypeError:
        utcnow.override_time += timedelta


def advance_time_seconds(seconds):
    """Advance overridden time by seconds."""
    advance_time_delta(datetime.timedelta(0, seconds))


def clear_time_override():
    """Remove the overridden time."""
    utcnow.override_time = None


def marshall_now(now=None):
    """Make an rpc-safe datetime with microseconds.

    Note: tzinfo is stripped, but not required for relative times.
    """
    if not now:
        now = utcnow()
    return dict(day=now.day, month=now.month, year=now.year, hour=now.hour,
                minute=now.minute, second=now.second,
                microsecond=now.microsecond)


def unmarshall_time(tyme):
    """Unmarshall a datetime dict."""
    return datetime.datetime(day=tyme['day'],
                             month=tyme['month'],
                             year=tyme['year'],
                             hour=tyme['hour'],
                             minute=tyme['minute'],
                             second=tyme['second'],
                             microsecond=tyme['microsecond'])


def delta_seconds(before, after):
    """Return the difference between two timing objects.

    Compute the difference in seconds between two date, time, or
    datetime objects (as a float, to microsecond resolution).
    """
    delta = after - before
    return total_seconds(delta)


def total_seconds(delta):
    """Return the total seconds of datetime.timedelta object.

    Compute total seconds of datetime.timedelta, datetime.timedelta
    doesn't have method total_seconds in Python2.6, calculate it manually.
    """
    try:
        return delta.total_seconds()
    except AttributeError:
        return ((delta.days * 24 * 3600) + delta.seconds +
                float(delta.microseconds) / (10 ** 6))


def is_soon(dt, window):
    """Determines if time is going to happen in the next window seconds.

    :params dt: the time
    :params window: minimum seconds to remain to consider the time not soon

    :return: True if expiration is within the given duration
    """
    soon = (utcnow() + datetime.timedelta(seconds=window))
    return normalize_time(dt) <= soon


def set_model_uuid_and_dates(instance):

    if instance.id in [None, '']:
        instance.id = uuid.uuid4().hex

    now = datetime.datetime.now()

    # The server handles these fields for some models.
    # so... set them if necessary, and don't worry about it if the
    # assignment fails.
    try:
        instance.created = now
    except AttributeError:
        pass

    try:
        instance.updated = now
    except AttributeError:
        pass


def json_response_factory(status_code, data, pretty_print=False):
    resp = jsonify(data)
    resp.status_code = status_code
    return resp


def not_found_response(resource, id):
    return json_response_factory(
        status_code=404,
        data={"error": {"description": "%s not found with id %s" % (resource, id)}}
    )


def bad_request(data):
    return json_response_factory(status_code=400, data=data)


def server_exception(origional_exception):
    return json_response_factory(status_code=500, data={"error": str(origional_exception)})


def method_not_allowed():
    resp = jsonify({"error": {"description": "method not allowed."}})
    resp.status_code = 405
    return resp


def log_request_message(message, request_msg=None):

    log_message = "INFO: [%s] from %s - message %s FROM: %s" % (
        request.method, request.full_path, message, request.remote_addr
    )

    if request_msg:
        current_app.logger.info(log_message, extra={'data': {'request': request_msg.data}})

    elif not request_msg:
        current_app.logger.info(log_message)


def log_request_warning(message, request_msg=None):
    log_message = "WARNING: [%s] from %s - message %s FROM: %s" % (
        request.method, request.full_path, message, request.remote_addr
    )

    if request_msg:
        current_app.logger.warning(log_message, extra={'data': {'request': request_msg.data}})

    elif not request_msg:
        current_app.logger.warning(log_message)


def log_request_error(message, request_msg=None):
    log_message = "ERROR: [%s] from %s - message %s FROM: %s" % (
        request.method, request.full_path, message, request.remote_addr
    )

    if request_msg:
        current_app.logger.error(log_message, extra={'data': {'request': request_msg.data}})

    elif not request_msg:
        current_app.logger.error(log_message)


def log_request_exception(exception):

    message = "Exception: [%s] %s from %s - message: %s" % (
        request.method, request.full_path, request.remote_addr, exception.message
    )
    current_app.logger.exception(message)
