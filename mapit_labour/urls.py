from django.conf.urls import url

from mapit_labour.views import (
    uprn,
    addressbase,
    health_check,
    import_csv,
    import_csv_status,
)


format_end = r"(?:\.(?P<format>html|json))?"

urlpatterns = [
    url(r"^uprn/(?P<uprn>[0-9]+)%s$" % format_end, uprn, name="mapit_labour-uprn"),
    url(r"^addressbase$", addressbase, name="mapit_labour-addressbase"),
    url(r"^import/csv/?$", import_csv, name="mapit_labour-import_csv"),
    url(
        r"^import/csv/(?P<task_id>[0-9a-f]+)$",
        import_csv_status,
        name="mapit_labour-import_csv_status",
    ),
    url(r"^health$", health_check),
]
