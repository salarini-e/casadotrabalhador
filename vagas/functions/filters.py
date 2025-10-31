# vagas/services/filters.py
from datetime import datetime

def processar_filtro_periodo(request):
    """Processa o filtro de data (POST e sessão)."""
    filtro_aplicado = False
    data_inicio = None
    data_fim = None

    # Limpar filtros
    if request.GET.get('limpar_filtros'):
        request.session.pop('filtro_periodo', None)
        return None, None, False, True  # último True sinaliza redirecionamento

    # POST — aplicar novo filtro
    if request.method == 'POST':
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        if data_inicio_str and data_fim_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                request.session['filtro_periodo'] = {'data_inicio': data_inicio_str, 'data_fim': data_fim_str}
                filtro_aplicado = True
            except ValueError:
                pass
    elif 'filtro_periodo' in request.session:
        try:
            filtro = request.session['filtro_periodo']
            data_inicio = datetime.strptime(filtro['data_inicio'], '%Y-%m-%d').date()
            data_fim = datetime.strptime(filtro['data_fim'], '%Y-%m-%d').date()
            filtro_aplicado = True
        except Exception:
            request.session.pop('filtro_periodo', None)

    return data_inicio, data_fim, filtro_aplicado, False
