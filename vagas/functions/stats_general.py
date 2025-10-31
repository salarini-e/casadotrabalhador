# vagas/services/stats_general.py
from django.db.models import Sum, Count
from vagas.models import Cargo, Vaga_Emprego, Empresa, Candidato
from django.utils import timezone
from datetime import timedelta

def get_estatisticas_gerais(vagas_query, candidatos_query):
    total_vagas_ativas = vagas_query.filter(ativo=True).count()
    total_cargos_ativos = Cargo.objects.filter(vaga_emprego__in=vagas_query.filter(ativo=True)).distinct().count()
    total_posicoes_abertas = vagas_query.filter(ativo=True).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
    total_empresas_ativas = Empresa.objects.filter(vaga_emprego__in=vagas_query.filter(ativo=True)).distinct().count()
    total_candidatos = candidatos_query.count()
    candidatos_online = candidatos_query.filter(candidato_online=True).count()
    candidatos_balcao = candidatos_query.filter(candidato_online=False).count()
    novos_candidatos = candidatos_query.filter(dt_inclusao__gte=timezone.now()-timedelta(days=31))
    novos_candidatos_online = novos_candidatos.filter(candidato_online=True).count()
    novos_candidatos_balcao = novos_candidatos.filter(candidato_online=False).count()
    
    return {
        'total_cargos_ativos': total_cargos_ativos,
        'total_vagas_ativas': total_vagas_ativas,
        'total_posicoes_abertas': total_posicoes_abertas,
        'total_empresas_ativas': total_empresas_ativas,
        'total_candidatos': total_candidatos,        
        'candidatos_online': candidatos_online,
        'candidatos_balcao': candidatos_balcao,
        'novos_candidatos': novos_candidatos.count(),
        'novos_candidatos_online': novos_candidatos_online,
        'novos_candidatos_balcao': novos_candidatos_balcao,
    }
