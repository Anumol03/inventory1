# Generated by Django 3.0.7 on 2023-11-20 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0005_purchaseitem_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseitem',
            name='grand_total',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='purchaseitem',
            name='net_amount',
            field=models.IntegerField(default=1),
        ),
    ]
