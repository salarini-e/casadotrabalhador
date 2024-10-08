# Generated by Django 3.2.12 on 2022-08-18 18:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vagas', '0014_auto_20220818_1357'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidato',
            name='candidato_online',
            field=models.BooleanField(default=False, verbose_name='Candidato online'),
        ),
        migrations.AddField(
            model_name='candidato',
            name='escolaridade',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='vagas.escolaridade'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='candidato',
            name='sexo',
            field=models.CharField(choices=[('m', 'Masculino'), ('f', 'Feminino'), ('o', 'Outro')], default='m', max_length=1, verbose_name='Sexo do candidato'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='candidato',
            name='bairro',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Bairro do candidato'),
        ),
    ]
