from flask.ext.enfold import EnfoldHttpClient
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.cache import Cache

enfold_client = EnfoldHttpClient()
app_cache = Cache()
sql_db = SQLAlchemy()

extension_list = list(
    frozenset(['enfold_client', 'app_cache', 'sql_db'])
)
