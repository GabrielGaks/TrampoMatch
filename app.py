import os

from trampomatch import create_app

app = create_app(os.environ.get("APP_CONFIG", "development"))
