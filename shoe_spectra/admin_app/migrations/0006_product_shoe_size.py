# Generated by Django 5.0.7 on 2024-07-30 18:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0005_shoesize'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='shoe_size',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='admin_app.shoesize'),
            preserve_default=False,
        ),
    ]
