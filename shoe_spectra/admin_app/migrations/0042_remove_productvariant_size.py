# Generated by Django 5.0.7 on 2024-08-15 14:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0041_remove_productvariant_quantity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productvariant',
            name='size',
        ),
    ]
