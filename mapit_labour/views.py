import itertools
from logging import getLogger

from django.shortcuts import render

from mapit.shortcuts import output_json, get_object_or_404
from mapit_labour.models import UPRN
from mapit.models import Generation, Area
from mapit.views.postcodes import add_codes, enclosing_areas
from mapit.middleware import ViewException

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


def uprn(request, uprn, format="json"):
    uprn = get_object_or_404(UPRN, format=format, uprn=uprn)

    try:
        generation = int(request.GET["generation"])
    except:
        generation = Generation.objects.current()
    areas = list(add_codes(Area.objects.by_location(uprn.location, generation)))

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
        return render(
            request,
            "mapit_labour/uprn.html",
            {
                "uprn": uprn.as_dict(),
                "areas": areas,
                "json_view": "mapit_labour-uprn",
            },
        )

    out = uprn.as_dict()
    out["areas"] = dict((area.id, area.as_dict()) for area in areas)

    if shortcuts:
        out["shortcuts"] = shortcuts
    return output_json(out, include_debug_db_queries=False)


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
        # return output_json(list(uprns[:10]))
    if single_line_address:
        uprns = uprns.filter(single_line_address__contains=single_line_address.upper())
    return render(
        request,
        "mapit_labour/uprns.html",
        {
            "uprns": uprns[:10],
        },
    )
