# Generated by Django 4.2.20 on 2025-04-24 04:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("consultantapi", "0009_bookpackage_visapackage"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="bookpackage",
            table="book_package",
        ),
        migrations.AlterModelTable(
            name="visapackage",
            table="visa_package",
        ),
    ]
