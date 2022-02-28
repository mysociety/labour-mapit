from django.conf.urls import url

from mapit_labour.views import uprn, addressbase, health_check, branches_upload


format_end = r"(?:\.(?P<format>html|json))?"

urlpatterns = [
    url(r"^uprn/(?P<uprn>[0-9]+)%s$" % format_end, uprn, name="mapit_labour-uprn"),
    url(r"^addressbase$", addressbase, name="mapit_labour-addressbase"),
    url(r"^branches_upload$", branches_upload, name="mapit_labour-branches_upload"),
    url(r"^health$", health_check),
]
