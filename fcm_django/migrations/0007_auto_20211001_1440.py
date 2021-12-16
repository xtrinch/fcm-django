from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fcm_django", "0006_auto_20210802_1140"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fcmdevice",
            name="id",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]
