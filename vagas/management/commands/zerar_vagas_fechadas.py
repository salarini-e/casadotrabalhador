from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Zera o número de vagas das vagas encerradas e acerta o histórico'

    def handle(self, *args, **options):
        
        from vagas.models import Vaga_Emprego, Historico_Vaga_Emprego
        vagas_fechadas = Vaga_Emprego.objects.filter(ativo=False).exclude(quantidadeVagas=0)
        total_atualizadas = 0
        for vaga in vagas_fechadas:
                        
            if Historico_Vaga_Emprego.objects.filter(vaga=vaga, tipo='0').exists() == False:
                if not Historico_Vaga_Emprego.objects.filter(vaga=vaga).exists():
                    vaga.criar_historico_alteracao('0', vaga.quantidadeVagas)
                elif Historico_Vaga_Emprego.objects.filter(vaga=vaga, tipo='-').exists() or Historico_Vaga_Emprego.objects.filter(vaga=self, tipo='+').exists():
                    historicos_positivos = Historico_Vaga_Emprego.objects.filter(vaga=vaga, tipo='-')
                    historicos_negativos = Historico_Vaga_Emprego.objects.filter(vaga=vaga, tipo='+')
                    total_positivo = sum([h.quantidadeVagas for h in historicos_positivos])
                    total_negativo = sum([h.quantidadeVagas for h in historicos_negativos])
                    vaga.criar_historico_alteracao('0', total_positivo - total_negativo)
            vaga.quantidadeVagas = 0
            vaga.save()
            total_atualizadas += 1
            
        self.stdout.write(vaga.style.SUCCESS(f'Total de {total_atualizadas} vagas encerradas atualizadas'))
