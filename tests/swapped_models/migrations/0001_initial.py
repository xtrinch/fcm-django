# IMPORTANT
# This migration required to check functionality with swapped model.
# So if there are any changes in the Swapped Model then you have to regenerate this migration.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomDevice",
            fields=[
                (
                    "name",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="Name"
                    ),
                ),
                (
                    "active",
                    models.BooleanField(
                        default=True,
                        help_text="Inactive devices will not be sent notifications",
                        verbose_name="Is active",
                    ),
                ),
                (
                    "date_created",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Creation date"
                    ),
                ),
                (
                    "device_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Unique device identifier",
                        max_length=255,
                        null=True,
                        verbose_name="Device ID",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("ios", "ios"),
                            ("android", "android"),
                            ("web", "web"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("registration_id", models.CharField(max_length=515, unique=True)),
                ("more_data", models.TextField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_query_name="fcmdevice",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["registration_id", "user"],
                        name="swapped_mod_registr_2cb0a2_idx",
                    )
                ],
            },
        ),
    ]
