# Generated by Django 3.2.12 on 2022-04-06 15:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mapit_labour', '0004_auto_20211213_2234'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSVImportTaskProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(max_length=64)),
                ('progress', models.TextField(null=True)),
            ],
        ),
    ]
