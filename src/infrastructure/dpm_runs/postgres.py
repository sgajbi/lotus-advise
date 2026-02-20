from importlib.util import find_spec


class PostgresDpmRunRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn

    def __getattr__(self, _name: str):
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED")
