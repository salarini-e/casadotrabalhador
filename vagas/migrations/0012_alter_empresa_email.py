# Generated by Django 3.2.12 on 2022-05-11 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vagas', '0011_auto_20220511_1448'),
    ]

    operations = [
        migrations.AlterField(
            model_name='empresa',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Email p/ encaminhamento'),
        ),
    ]
