# Generated by Django 5.0.7 on 2024-07-30 18:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0002_brand_color'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stock', models.PositiveIntegerField()),
                ('size', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='admin_app.brand')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='admin_app.category')),
                ('colors', models.ManyToManyField(related_name='products', to='admin_app.color')),
                ('gender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='admin_app.gender')),
            ],
        ),
    ]
