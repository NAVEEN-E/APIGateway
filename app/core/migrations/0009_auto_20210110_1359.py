# Generated by Django 3.1.4 on 2021-01-10 08:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auto_20210110_1341'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='contact_no',
            new_name='contact',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='profile_picture',
            new_name='picture',
        ),
    ]