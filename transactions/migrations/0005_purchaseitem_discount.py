# Generated by Django 3.0.7 on 2023-11-06 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0004_auto_20231017_2157'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseitem',
            name='discount',
            field=models.IntegerField(default=1),
        ),
    ]
