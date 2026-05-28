from app.constants.paths import PROJECT_ROOT


DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'app.sqlite3'}"
