# Generated by Django 3.0.7 on 2023-10-15 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_auto_20231010_2005'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='discount',
            field=models.IntegerField(default=1),
        ),
    ]