# Generated by Django 3.1.4 on 2021-01-10 10:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20210110_1537'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appmodule',
            name='roles',
        ),
        migrations.AddField(
            model_name='user',
            name='roles',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.role'),
        ),
    ]
