# Generated by Django 2.2.13 on 2020-07-21 21:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_order_billing_address'),
    ]

    operations = [
        migrations.RenameField(
            model_name='billingaddress',
            old_name='countries',
            new_name='country',
        ),
    ]