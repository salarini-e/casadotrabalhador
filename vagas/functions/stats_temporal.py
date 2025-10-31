# vagas/services/stats_temporal.py
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Count

from vagas.models import Vaga_Emprego, Candidato, Cargo

def gerar_series_candidatos_por_mes(meses=13):
    agora = datetime.now()
    resultado = []
    for i in range(meses):
        mes_inicio = agora.replace(day=1) - relativedelta(months=i)
        mes_fim = mes_inicio + relativedelta(months=1)
        total = Candidato.objects.filter(dt_inclusao__gte=mes_inicio, dt_inclusao__lt=mes_fim).count()
        resultado.append({'mes': mes_inicio.strftime('%m/%Y'), 'total': total})
    return list(reversed(resultado))

def gerar_series_candidatos_por_mes_com_filtro(candidato_query, data_inicio=None, data_fim=None, max_meses=12):
    # Determina range padrão se não for passado
    if not data_inicio:
        data_inicio = candidato_query.earliest('dt_inclusao').dt_inclusao
    if not data_fim:
        data_fim = candidato_query.latest('dt_inclusao').dt_inclusao

    # Converte strings para datetime se necessário
    if isinstance(data_inicio, str):
        data_inicio = datetime.strptime(data_inicio, "%d/%m/%Y")
    if isinstance(data_fim, str):
        data_fim = datetime.strptime(data_fim, "%d/%m/%Y")

    # Começa no primeiro dia do mês inicial
    inicio = data_inicio.replace(day=1)
    fim = data_fim.replace(day=1)

    meses = []
    atual = inicio
    while atual <= fim:
        meses.append(atual)
        atual += relativedelta(months=1)

    meses = meses[-max_meses:]

    resultado = []
    for mes in meses:
        proximo_mes = mes + relativedelta(months=1)

        # Define intervalo real do mês, respeitando o filtro
        inicio_mes = max(mes, data_inicio)
        fim_mes = min(proximo_mes - relativedelta(days=1), data_fim)

        total = candidato_query.filter(
            dt_inclusao__gte=inicio_mes,
            dt_inclusao__lte=fim_mes
        ).count()

        resultado.append({
            'mes': mes.strftime('%m/%y'),
            'total': total
        })

    return resultado
