from flask import current_app
from boto.s3.key import Key


def upload(project_id, sheet_id, img_string, i_type, version):
    try:
        if i_type == "jpg":
            ext = ".jpg"
            content_type = "image/jpeg"
        else:
            ext = ".png"
            content_type = "image/png"
        bucket = current_app.s3_conn.get_bucket(current_app.config['S3_BUCKET_NAME'])
        key = Key(bucket, project_id + "/" + sheet_id + "_" + str(version) + ext)
        key.set_metadata('Content-Type', content_type)
        key.set_contents_from_string(img_string)
    except Exception as Ex:
        print Ex


def delete(url):
    try:
        url_split = url.split("/")
        key_path = url_split[-2] + "/" + url_split[-1]
        bucket = current_app.s3_conn.get_bucket(current_app.config['S3_BUCKET_NAME'])
        key = Key(bucket, key_path)
        bucket.delete_key(key)
    except Exception as Ex:
        print Ex
