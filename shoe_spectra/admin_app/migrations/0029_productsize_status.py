# Generated by Django 5.0.7 on 2024-08-07 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0028_delete_productimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='productsize',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]