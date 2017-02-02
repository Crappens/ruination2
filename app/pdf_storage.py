from flask import current_app
from boto.s3.key import Key


def upload(local_path, pdf_name):
    try:
        content_type = "application/pdf"
        bucket = current_app.s3_conn.get_bucket(current_app.config['S3_BUCKET_NAME'])
        key = Key(bucket, pdf_name)
        key.set_metadata('Content-Type', content_type)
        with open(local_path, 'rb') as f:
            key.set_contents_from_string(f.read())
        t_path = current_app.config["THUMBNAIL_PATH"]
        new_path = t_path + pdf_name
        return new_path
    except Exception as Ex:
        print Ex
