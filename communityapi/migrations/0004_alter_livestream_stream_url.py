# Generated by Django 4.2.20 on 2025-03-22 06:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "communityapi",
            "0003_livestream_thumbnail_alter_livestream_recording_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="livestream",
            name="stream_url",
            field=models.TextField(
                help_text="streamUrl for the live stream source", max_length=500
            ),
        ),
    ]
