import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fcm_django", "0011_fcmdevice_fcm_django_registration_id_user_id_idx"),
        swapper.dependency("fcm_django", "fcmdevice"),
    ]

    operations = [
        migrations.CreateModel(
            name="FCMDeviceTopic",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("topic", models.CharField(db_index=True, max_length=900)),
                ("date_subscribed", models.DateTimeField(auto_now_add=True)),
                (
                    "device",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_subscriptions",
                        to=swapper.get_model_name("fcm_django", "fcmdevice"),
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("device", "topic"),
                        name="fcm_django_unique_device_topic",
                    )
                ],
            },
        ),
    ]
