# vagas/services/filters.py
from datetime import datetime

# def processar_filtro_periodo(request):
#     """Processa o filtro de data (POST e sessão)."""
#     filtro_aplicado = False
#     data_inicio = None
#     data_fim = None

#     # Limpar filtros
#     if request.GET.get('limpar_filtros'):
#         request.session.pop('filtro_periodo', None)
#         return None, None, False, True  # último True sinaliza redirecionamento

#     # POST — aplicar novo filtro
#     if request.method == 'POST':
#         data_inicio_str = request.POST.get('data_inicio')
#         data_fim_str = request.POST.get('data_fim')
#         if data_inicio_str and data_fim_str:
#             try:
#                 data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
#                 data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
#                 request.session['filtro_periodo'] = {'data_inicio': data_inicio_str, 'data_fim': data_fim_str}
#                 filtro_aplicado = True
#             except ValueError:
#                 pass
#     elif 'filtro_periodo' in request.session:
#         try:
#             filtro = request.session['filtro_periodo']
#             data_inicio = datetime.strptime(filtro['data_inicio'], '%Y-%m-%d').date()
#             data_fim = datetime.strptime(filtro['data_fim'], '%Y-%m-%d').date()
#             filtro_aplicado = True
#         except Exception:
#             request.session.pop('filtro_periodo', None)

#     return data_inicio, data_fim, filtro_aplicado, False

from datetime import datetime

def processar_filtro_periodo(request):
    """
    Processa o filtro de período de data (GET/POST/sessão) compatível com:
    - Views funcionais (Django)
    - APIViews (DRF)
    
    Retorna:
        data_inicio (date | None)
        data_fim (date | None)
        filtro_aplicado (bool)
        limpar (bool) -> True se filtros foram limpos
    """
    filtro_aplicado = False
    data_inicio = None
    data_fim = None
    limpar = False

    # --- 1. Limpar filtros via GET ---
    query_params = getattr(request, "query_params", request.GET)
    if query_params.get('limpar_filtros'):
        request.session.pop('filtro_periodo', None)
        return None, None, False, True

    # --- 2. Ler POST (form ou JSON) ---
    if request.method == 'POST':
        post_data = getattr(request, "data", request.POST)
        data_inicio_str = post_data.get('data_inicio')
        data_fim_str = post_data.get('data_fim')
        if data_inicio_str and data_fim_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                request.session['filtro_periodo'] = {
                    'data_inicio': data_inicio_str,
                    'data_fim': data_fim_str
                }
                filtro_aplicado = True
            except ValueError:
                pass  # pode logar ou notificar erro se quiser

    # --- 3. Ler sessão caso não tenha POST ---
    elif 'filtro_periodo' in request.session:
        try:
            filtro = request.session['filtro_periodo']
            data_inicio = datetime.strptime(filtro['data_inicio'], '%Y-%m-%d').date()
            data_fim = datetime.strptime(filtro['data_fim'], '%Y-%m-%d').date()
            filtro_aplicado = True
        except Exception:
            request.session.pop('filtro_periodo', None)

    return data_inicio, data_fim, filtro_aplicado, limpar
