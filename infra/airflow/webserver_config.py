from __future__ import annotations

import os

from flask_appbuilder.const import AUTH_DB


AUTH_TYPE = AUTH_DB
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
