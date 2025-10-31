# vagas/services/stats_advanced.py
from django.db.models import Sum, Count, Q

from vagas.models import Vaga_Emprego, RequisicaoVaga, Cargo, Candidato
from django.utils import timezone
from datetime import timedelta

def calcular_tempo_medio_aprovacao(queryset):
    formularios_aprovados = queryset.filter(status_requisicao='AP').exclude(dt_atualizacao__isnull=True)
    if not formularios_aprovados.exists():
        return 0
    total_horas = sum(
        (f.dt_atualizacao - f.dt_inclusao).total_seconds() / 3600
        for f in formularios_aprovados
        if f.dt_atualizacao and f.dt_inclusao
    )
    return total_horas / formularios_aprovados.count()


def calcular_funil_vagas(vagas_query, candidatos_query):
    total_vagas = vagas_query.count()
    total_candidatos = candidatos_query.count()
    taxa = total_candidatos / total_vagas if total_vagas else 0

    novas_vagas = vagas_query.filter().count()
    novas_vagas_posicoes = vagas_query.filter().aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
    vagas_encerradas = vagas_query.filter(ativo=False).count()
    vagas_encerradas_posicoes = vagas_query.filter(ativo=False).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
    return {
        'taxa_candidatos_por_vaga': round(taxa, 1),
        'novas_vagas': novas_vagas,
        'novas_vagas_posicoes': novas_vagas_posicoes,
        'vagas_encerradas': vagas_encerradas,
        'vagas_encerradas_posicoes': vagas_encerradas_posicoes,
        'saldo_vagas': novas_vagas - vagas_encerradas,
        'saldo_posicoes': novas_vagas_posicoes - vagas_encerradas_posicoes,
        }

