# Generated by Django 3.2.6 on 2021-12-01 13:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0007_auto_20211017_1245'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='price_stripe_id',
            field=models.CharField(max_length=200, null=True),
        ),
    ]
