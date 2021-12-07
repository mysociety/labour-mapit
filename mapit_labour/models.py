from __future__ import unicode_literals

import re
from django.db import connection
from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GinIndex

from mapit.models import str2int


class UPRN(models.Model):
    uprn = models.PositiveBigIntegerField(primary_key=True)
    postcode = models.CharField(max_length=7)
    location = models.PointField()
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
        (easting, northing) = self.as_uk_grid()

        return {
            "uprn": self.uprn,
            "postcode": self.postcode,
            "wgs84_lon": self.location[0],
            "wgs84_lat": self.location[1],
            "easting": easting,
            "northing": northing,
            "addressbase_core": self.addressbase,
        }

    def as_uk_grid(self):
        cursor = connection.cursor()
        srid = 27700
        cursor.execute(
            "SELECT ST_AsText(ST_Transform(ST_GeomFromText('POINT(%f %f)', 4326), %d))"
            % (self.location[0], self.location[1], srid)
        )
        row = cursor.fetchone()
        m = re.match(r"POINT\((.*?) (.*)\)", row[0])
        return list(map(str2int, m.groups()))
