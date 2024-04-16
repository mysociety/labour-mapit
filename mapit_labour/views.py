import itertools
from logging import getLogger
from pprint import pformat

from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.conf import settings
from django.utils.cache import add_never_cache_headers
from django.urls import reverse
from django.http import Http404
from django.views.decorators.cache import never_cache

from django_q.tasks import fetch
from django_q.models import OrmQ

from mapit.shortcuts import output_json, get_object_or_404
from mapit.models import Generation, Area
from mapit.views.postcodes import add_codes, enclosing_areas
from mapit.middleware import ViewException
from mapit.views.areas import area as mapit_area

from .models import UPRN, CSVImportTaskProgress
from .forms import ImportCSVForm

logger = getLogger(__name__)

# valid field names for AddressBase Core lookups
FIELD_NAMES = [
    "parent_uprn",
    "uprn",
    "udprn",
    "usrn",
    "toid",
    "classification_code",
    "easting",
    "northing",
    "latitude",
    "longitude",
    "rpc",
    "last_update_date",
    "po_box",
    "organisation",
    "sub_building",
    "building_name",
    "building_number",
    "street_name",
    "locality",
    "town_name",
    "post_town",
    "island",
    "postcode",
    "delivery_point_suffix",
    "gss_code",
    "change_code",
    # This does appear in the AddressBase Core record but is
    # queried in a different way so isn't included in this list.
    # "single_line_address",
]


@never_cache
def uprn(request, uprn, format="json"):
    uprn = get_object_or_404(UPRN, format=format, uprn=uprn)

    query = Generation.objects.query_args(request, format)
    areas = list(add_codes(Area.objects.by_location(uprn.location, query)))

    shortcuts = {}
    for area in areas:
        if area.type.code in ("COP", "LBW", "LGE", "MTW", "UTE", "UTW"):
            shortcuts["ward"] = area.id
            shortcuts["council"] = area.parent_area_id
        elif area.type.code == "CED":
            shortcuts.setdefault("ward", {})["county"] = area.id
            shortcuts.setdefault("council", {})["county"] = area.parent_area_id
        elif area.type.code == "DIW":
            shortcuts.setdefault("ward", {})["district"] = area.id
            shortcuts.setdefault("council", {})["district"] = area.parent_area_id
        elif area.type.code in ("WMC",):
            # XXX Also maybe 'EUR', 'NIE', 'SPC', 'SPE', 'WAC', 'WAE', 'OLF', 'OLG', 'OMF', 'OMG'):
            shortcuts[area.type.code] = area.id

    # Add manual enclosing areas.
    extra = []
    for area in areas:
        if area.type.code in enclosing_areas.keys():
            extra.extend(enclosing_areas[area.type.code])
    areas = itertools.chain(areas, Area.objects.filter(id__in=extra))

    if format == "html":
        api_key = None
        if key := request.user.api_key.first():
            api_key = key.key
        return render(
            request,
            "mapit_labour/uprn.html",
            {
                "uprn": uprn.as_dict(),
                "areas": areas,
                "json_view": "mapit_labour-uprn",
                "api_key": api_key,
            },
        )

    out = uprn.as_dict()
    out["areas"] = dict((area.id, area.as_dict()) for area in areas)

    if shortcuts:
        out["shortcuts"] = shortcuts
    return output_json(out)


def addressbase(request):
    lookup = {
        k.lower(): request.GET[k].upper()
        for k in request.GET.keys()
        if k.lower() in FIELD_NAMES
    }
    single_line_address = request.GET.get("single_line_address")

    if not lookup and not single_line_address:
        raise ViewException(
            "json",
            "At least one AddressBase Core field should be specified in the query parameters.",
            400,
        )

    uprns = UPRN.objects.all().values_list("addressbase", flat=True)

    if lookup:
        uprns = uprns.filter(addressbase__contains=lookup)
    if single_line_address:
        uprns = uprns.filter(single_line_address__contains=single_line_address.upper())
    return output_json(list(uprns[: settings.ADDRESSBASE_RESULTS_LIMIT]))


def health_check(request):
    """
    This is just a simple view that the Varnish load balancer uses to determine
    whether this site is available and healthy.
    """
    return HttpResponse("Everything OK")


def import_csv(request):
    if request.method == "POST":
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            task_id = form.add_import_task()
            return HttpResponseRedirect(f"/import/csv/{task_id}")
    else:
        form = ImportCSVForm()
    return render(request, "mapit_labour/import_csv.html", {"form": form})


def import_csv_status(request, task_id):
    context = {}
    allow_cache = True

    if task := fetch(task_id):
        # task has finished, resulting in success or failure
        context["task"] = task
    else:
        for q in OrmQ.objects.all():
            if q.task_id() == task_id:
                context["queued"] = q
                try:
                    context["progress"] = CSVImportTaskProgress.objects.get(
                        task_id=task_id
                    )
                except CSVImportTaskProgress.DoesNotExist:
                    pass
                allow_cache = False
                break
        else:
            raise Http404
    response = render(request, "mapit_labour/import_csv_status.html", context)
    if not allow_cache:
        add_never_cache_headers(response)
    return response


def area(request, area_id, format=""):
    """
    Look for a LBR/LR Area that has this GSS code and redirect, otherwise
    call the original MapIt view.
    """
    try:
        a = (
            Area.objects.filter(
                codes__type__code="gss",
                codes__code=area_id,
                type__code__in=("LBR", "LR"),
            )
            .select_related(None)  # Try and make the query as small as possible
            .prefetch_related(None)
            .only("id")
            .get()
        )
        params = {"area_id": a.id}
        if format:
            params["format"] = format
        return HttpResponseRedirect(reverse("area", kwargs=params))
    except Area.DoesNotExist:
        return mapit_area(request, area_id, format)
