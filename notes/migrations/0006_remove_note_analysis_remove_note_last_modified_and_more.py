# Generated by Django 5.0.4 on 2024-04-21 04:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0005_notegroup_note_groups_userprofile'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='note',
            name='analysis',
        ),
        migrations.RemoveField(
            model_name='note',
            name='last_modified',
        ),
        migrations.AddField(
            model_name='note',
            name='keywords',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
