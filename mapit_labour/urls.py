from django.urls import re_path, path

from mapit_labour.views import (
    uprn,
    addressbase,
    health_check,
    import_csv,
    import_csv_status,
    area,
)


format_end = r"(?:\.(?P<format>html|json))?"

urlpatterns = [
    re_path(r"^uprn/(?P<uprn>[0-9]+)%s$" % format_end, uprn, name="mapit_labour-uprn"),
    path("addressbase", addressbase, name="mapit_labour-addressbase"),
    path("import/csv", import_csv, name="mapit_labour-import_csv"),
    re_path(
        r"^import/csv/(?P<task_id>[0-9a-f]+)$",
        import_csv_status,
        name="mapit_labour-import_csv_status",
    ),
    path("health", health_check),
    # Override the existing mapit.views.areas.area view with our own that
    # supports lookup of branches/regions by GSS code. Necessary because
    # the pseudo-GSS codes assigned to these areas don't match the
    # pattern being looked for in mapit_gb.countries.area_code_lookup.
    # URL pattern deliberately limits to LR_/BR_ prefix so most hits should
    # go straight to original view function.
    re_path(r"^area/(?P<area_id>[BL]R_[0-9A-Z_]+)%s$" % format_end, area),
]
