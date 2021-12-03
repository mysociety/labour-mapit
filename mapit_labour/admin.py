import json

from django.db.models import JSONField
from django.db import connection
from django.contrib.gis import admin
from django.forms import widgets
from django.core.paginator import Paginator
from django.utils.functional import cached_property


from mapit_labour.models import UPRN

# Adapted from https://medium.com/squad-engineering/estimated-counts-for-faster-django-admin-change-list-963cbf43683e
class LargeTablePaginator(Paginator):
    """
    Warning: Postgresql only hack
    Overrides the count method of QuerySet objects to get an estimate instead of actual count when not filtered.
    However, this estimate can be stale and hence not fit for situations where the count of objects actually matter.
    """
    @cached_property
    def count(self):
        query = self.object_list.query
        if not query.where:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT reltuples FROM pg_class WHERE relname = %s",
                               [query.model._meta.db_table])
                return int(cursor.fetchone()[0])
            except:  # pragma: no cover
                pass
        return super(LargeTablePaginator, self).count

class PrettyJSONWidget(widgets.Textarea):
    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=2)
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split("\n")]
            self.attrs["rows"] = min(max(len(row_lengths) + 2, 10), 30)
            self.attrs["cols"] = min(max(max(row_lengths) + 2, 40), 120)
            self.attrs["readonly"] = True
            return value
        except Exception:  # pragma: no cover
            return super(PrettyJSONWidget, self).format_value(value)


class UPRNAdmin(admin.OSMGeoAdmin):
    list_display = ("uprn", "single_line_address")
    search_fields = ["single_line_address"]
    formfield_overrides = {JSONField: {"widget": PrettyJSONWidget}}
    show_full_result_count = False
    paginator = LargeTablePaginator

    def single_line_address(self, obj):
        return obj.addressbase['single_line_address']


admin.site.register(UPRN, UPRNAdmin)
