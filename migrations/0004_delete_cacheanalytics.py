# Generated by Django 4.0.6 on 2022-08-17 11:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('extra_analytics', '0003_cacheanalytics_updated_at'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CacheAnalytics',
        ),
    ]
