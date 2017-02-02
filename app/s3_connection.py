from boto.s3.connection import S3Connection


def init_s3_connection(app):
    if app.config['S3_AWS_ACCESS_KEY']:
        return S3Connection(app.config['S3_AWS_ACCESS_KEY'], app.config['S3_AWS_SECRET_KEY'])
