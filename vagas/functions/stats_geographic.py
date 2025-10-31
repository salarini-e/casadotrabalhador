# vagas/services/stats_geographic.py
from django.db.models import Count, Sum, Q
from vagas.models import Empresa

def candidatos_por_bairro(queryset, total_candidatos):
    qs = queryset.exclude(Q(bairro__isnull=True) | Q(bairro__exact='')).values('bairro').annotate(total=Count('id')).order_by('-total')[:10]
    return [
        {
            'bairro': i['bairro'],
            'total': i['total'],
            'percentual': round((i['total'] / total_candidatos) * 100, 1) if total_candidatos else 0,
        }
        for i in qs
    ]

def bairros_por_vaga(vagas_query, filtro_aplicado=False):
    if filtro_aplicado:
        empresas = Empresa.objects.filter(vaga_emprego__in=vagas_query).distinct()
        qs = empresas.exclude(Q(bairro__isnull=True) | Q(bairro__exact='')).values('bairro').annotate(
            total_vagas=Sum('vaga_emprego__quantidadeVagas', filter=Q(vaga_emprego__in=vagas_query)),
            total_empresas=Count('id', distinct=True),
        ).order_by('-total_vagas')[:10]
    else:
        qs = Empresa.objects.exclude(Q(bairro__isnull=True) | Q(bairro__exact='')).values('bairro').annotate(
            total_vagas=Sum('vaga_emprego__quantidadeVagas'),
            total_empresas=Count('id', distinct=True),
        ).order_by('-total_vagas')[:10]
    return list(qs)

def top_cargos_por_candidatos(queryset, n_top=15):
    qs = queryset.values('vaga__cargo__nome').annotate(total=Count('id')).order_by('-total')[:n_top]
    return [
        {
            'cargo': i['vaga__cargo__nome'],
            'total': i['total'],
        }
        for i in qs
    ]

def top_empresas_por_vagas(vagas_query, n_top=10):
    qs = vagas_query.values('empresa__nome').annotate(total_vagas=Sum('quantidadeVagas')).order_by('-total_vagas')[:n_top]
    return [
        {
            'empresa': i['empresa__nome'],
            'total_vagas': i['total_vagas'],
        }
        for i in qs
    ]