from django.db import migrations

def popular_campos_responsavel(apps, schema_editor):
    """Popula os novos campos com dados dos usuários existentes"""
    ResponsavelEmpresa = apps.get_model('vagas', 'ResponsavelEmpresa')
    
    for responsavel in ResponsavelEmpresa.objects.all():
        if responsavel.user:
            # Preencher nome do usuário
            if not responsavel.nome:
                responsavel.nome = responsavel.user.first_name or responsavel.user.username
            
            # Preencher email do usuário
            if not responsavel.email:
                responsavel.email = responsavel.user.email or f"nao-informado-{responsavel.id}@exemplo.com"
            
            # Preencher CPF padrão (será alterado manualmente depois)
            if not responsavel.cpf:
                responsavel.cpf = f"00000000{responsavel.id:03d}"  # CPF fictício baseado no ID
            
            responsavel.save()

def reverter_populacao(apps, schema_editor):
    """Reverter não é necessário, pois os dados são preservados"""
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('vagas', '0022_alter_responsavelempresa_options_and_more'),
    ]

    operations = [
        migrations.RunPython(popular_campos_responsavel, reverter_populacao),
    ]