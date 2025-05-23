# Generated by Django 4.2.20 on 2025-04-24 05:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("consultantapi", "0010_alter_bookpackage_table_alter_visapackage_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookpackage",
            name="visa_type",
            field=models.CharField(
                choices=[
                    ("D-2", "D-2 Student"),
                    ("D-4", "D-4 Language Training"),
                    ("E-6", "E-6 Entertainment"),
                    ("C-4", "C-4 Short-Term Work"),
                ],
                help_text="Which visa the user is applying for",
                max_length=3,
            ),
        ),
        migrations.AlterField(
            model_name="visapackage",
            name="visa_type",
            field=models.CharField(
                choices=[
                    ("D-2", "D-2 Student"),
                    ("D-4", "D-4 Language Training"),
                    ("E-6", "E-6 Entertainment"),
                    ("C-4", "C-4 Short-Term Work"),
                ],
                max_length=4,
            ),
        ),
    ]
