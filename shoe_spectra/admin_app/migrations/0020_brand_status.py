# Generated by Django 5.0.7 on 2024-08-03 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0019_category_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]