# Generated by Django 3.2.13 on 2022-10-07 18:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vagas', '0007_auto_20221007_1535'),
    ]

    operations = [
        migrations.RenameField(
            model_name='candidato',
            old_name='dt_atualizaocao',
            new_name='dt_atualizacao',
        ),
    ]
