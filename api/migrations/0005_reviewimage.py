# Generated by Django 5.1.7 on 2025-03-12 12:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_alter_product_main_image_alter_productimage_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("image", models.ImageField(upload_to="media/reviews/")),
                (
                    "review",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="api.review",
                    ),
                ),
            ],
            options={
                "db_table": "review_image",
            },
        ),
    ]
