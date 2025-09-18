from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Cria o grupo empresa_user e configura suas permissões'

    def handle(self, *args, **options):
        # Criar o grupo empresa_user
        grupo_empresa, created = Group.objects.get_or_create(name='empresa_user')
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Grupo "empresa_user" criado com sucesso')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Grupo "empresa_user" já existe')
            )
        
        # Definir permissões básicas para usuários de empresa
        from vagas.models import Vaga_Emprego, Candidato, ResponsavelEmpresa
        
        # Content types
        vaga_ct = ContentType.objects.get_for_model(Vaga_Emprego)
        candidato_ct = ContentType.objects.get_for_model(Candidato)
        responsavel_ct = ContentType.objects.get_for_model(ResponsavelEmpresa)
        
        # Permissões que queremos dar aos responsáveis das empresas
        permissoes_desejadas = [
            # Visualizar vagas da própria empresa
            f'view_{Vaga_Emprego._meta.model_name}',
            # Visualizar candidatos das vagas da própria empresa  
            f'view_{Candidato._meta.model_name}',
            # Ver informações do próprio ResponsavelEmpresa
            f'view_{ResponsavelEmpresa._meta.model_name}',
        ]
        
        # Adicionar permissões ao grupo
        permissoes_adicionadas = 0
        for perm_codename in permissoes_desejadas:
            try:
                if 'vaga_emprego' in perm_codename:
                    permission = Permission.objects.get(codename=perm_codename, content_type=vaga_ct)
                elif 'candidato' in perm_codename:
                    permission = Permission.objects.get(codename=perm_codename, content_type=candidato_ct)
                elif 'responsavelempresa' in perm_codename:
                    permission = Permission.objects.get(codename=perm_codename, content_type=responsavel_ct)
                else:
                    continue
                    
                grupo_empresa.permissions.add(permission)
                permissoes_adicionadas += 1
                
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Permissão {perm_codename} não encontrada')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Configuração concluída. {permissoes_adicionadas} permissões adicionadas ao grupo empresa_user'
            )
        )
        
        # Informações adicionais
        total_responsaveis = ResponsavelEmpresa.objects.count()
        self.stdout.write(
            f'Total de responsáveis cadastrados: {total_responsaveis}'
        )