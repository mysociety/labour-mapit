# Generated by Django 3.2.10 on 2021-12-13 22:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mapit_labour', '0003_alter_uprn_location'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='apikey',
            options={'verbose_name': 'API key'},
        ),
        migrations.AlterModelOptions(
            name='uprn',
            options={'ordering': ('uprn',), 'verbose_name': 'UPRN'},
        ),
    ]