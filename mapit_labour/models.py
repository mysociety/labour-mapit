from __future__ import unicode_literals

import re
import string
import random
from django.conf import settings
from django.db import connection
from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GinIndex
from django.dispatch import receiver
from django.apps import apps

from mapit.models import str2int


class UPRN(models.Model):
    uprn = models.PositiveBigIntegerField(primary_key=True)
    postcode = models.CharField(max_length=7)
    location = models.PointField(srid=27700)
    addressbase = models.JSONField()

    # It's unnecessarily complex to index the value of a key in a JSONB
    # field and perform `LIKE %`-style matching, so this field has been
    # promoted from the AddressBase Core record to a field directly on
    # the model.
    single_line_address = models.TextField(db_index=True, editable=False)

    class Meta:
        ordering = ("uprn",)
        indexes = [
            GinIndex(fields=["addressbase"]),
            GinIndex(
                name="mapit_labour_sl_address_gin",
                fields=["single_line_address"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        return str(self.uprn)

    def as_dict(self):
        (lon, lat) = self.as_wgs84()

        return {
            "uprn": self.uprn,
            "postcode": self.postcode,
            "easting": self.location[0],
            "northing": self.location[1],
            "wgs84_lon": lon,
            "wgs84_lat": lat,
            "addressbase_core": self.addressbase,
        }

    def as_wgs84(self):
        cursor = connection.cursor()
        srid = 4326
        cursor.execute(
            "SELECT ST_AsText(ST_Transform(ST_GeomFromText('POINT(%f %f)', 27700), %d))"
            % (self.location[0], self.location[1], srid)
        )
        row = cursor.fetchone()
        m = re.match(r"POINT\((.*?) (.*)\)", row[0])
        return list(map(float, m.groups()))


# Taken from https://github.com/mysociety/mapit.mysociety.org, sans-Redis bits
class APIKey(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="api_key", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=40, blank=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s: %s" % (self.user, self.key)

    @staticmethod
    def generate_key(size=40, chars=string.ascii_letters + string.digits):
        return "".join(random.choice(chars) for x in range(size))


@receiver(models.signals.post_save)
def create_key_for_new_user(sender, **kwargs):
    """Create a new APIKey for a user who just signed up."""
    if sender != apps.get_model(settings.AUTH_USER_MODEL):
        return

    # We don't care if this isn't a newly-created User.
    if not kwargs["created"]:
        return

    user = kwargs["instance"]
    # If there was a key already for them (who knows, it could happen) we
    # delete it, assuming that the user account system has responsibility for
    # making sure the account should exist.
    try:
        key = APIKey.objects.get(user=user)
        key.delete()  # pragma: no cover
    except APIKey.DoesNotExist:
        pass

    APIKey.objects.create(user=user, key=APIKey.generate_key())
