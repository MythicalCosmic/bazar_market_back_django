from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("base", "0013_add_referral_reward_system"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourierProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("rating", models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=3)),
                ("vehicle_type", models.CharField(choices=[("motorcycle", "Motorcycle"), ("car", "Car"), ("bicycle", "Bicycle")], default="motorcycle", max_length=20)),
                ("vehicle_plate", models.CharField(blank=True, default="", max_length=20)),
                ("is_online", models.BooleanField(default=False)),
                ("prefs", models.JSONField(blank=True, default=dict)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="courier_profile", to="base.user")),
            ],
            options={
                "db_table": "courier_profiles",
            },
        ),
        migrations.CreateModel(
            name="PushDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.CharField(max_length=255, unique=True)),
                ("platform", models.CharField(blank=True, default="", max_length=16)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_devices", to="base.user")),
            ],
            options={
                "db_table": "push_devices",
            },
        ),
        migrations.CreateModel(
            name="CourierOrderState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("new", "New"), ("accepted", "Accepted"), ("picked", "Picked up"), ("onway", "On the way"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], db_index=True, default="new", max_length=12)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("picked_at", models.DateTimeField(blank=True, null=True)),
                ("onway_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("courier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="courier_states", to="base.user")),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="courier_state", to="base.order")),
            ],
            options={
                "db_table": "courier_order_states",
            },
        ),
        migrations.AddIndex(
            model_name="pushdevice",
            index=models.Index(fields=["user"], name="idx_push_devices_user"),
        ),
        migrations.AddIndex(
            model_name="courierorderstate",
            index=models.Index(fields=["courier", "status"], name="idx_courier_state_cs"),
        ),
    ]
