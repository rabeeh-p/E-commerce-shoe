# Generated by Django 5.0.7 on 2024-08-04 15:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0024_remove_product_colors'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='shoe_size',
        ),
    ]