# Generated by Django 5.0.7 on 2024-09-06 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0055_coupon_min_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupon_code',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
