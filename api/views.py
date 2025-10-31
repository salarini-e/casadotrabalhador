from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from requests import request
from rest_framework.parsers import JSONParser
from vagas.models import (
    Cargo, Vaga_Emprego, Empresa, Candidato, Escolaridade, 
    RequisicaoVaga, CandidatoSelecionado, SolicitacaoDesativacao
)
from .serializer import VagaSerializer, CargoSerializer

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import permission_classes
from rest_framework import generics

from django.db.models import Count, Q, Sum, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from datetime import datetime, timedelta
from django.utils import timezone


class Listar_Vagas(generics.ListAPIView):
    queryset=Vaga_Emprego.objects.filter(ativo=True)
    serializer_class=VagaSerializer
    # authentication_classes = (JSONWebTokenAuthentication)
    permission_classes=[IsAuthenticated]

class Listar_Cargos(generics.ListAPIView):
    queryset=Cargo.objects.all()
    serializer_class=CargoSerializer
    # authentication_classes = (JSONWebTokenAuthentication)
    permission_classes=[IsAuthenticated]


class IndicadoresDashboard(APIView):
    """
    View para retornar indicadores e dados para plotagem de gráficos do dashboard
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Parâmetros opcionais para filtros
            periodo_dias = int(request.GET.get('periodo_dias', 30))  # Para novos candidatos
            top_limit = int(request.GET.get('top_limit', 10))  # Para top cargos/empresas
            
            # Datas de referência
            data_limite_novos = timezone.now() - timedelta(days=periodo_dias)
            data_30_dias = timezone.now() - timedelta(days=30)
            
            # 1. ESTATÍSTICAS BÁSICAS PRINCIPAIS
            estatisticas_basicas = {
                # Cargos ativos (que possuem vagas ativas)
                'cargos_ativos': Cargo.objects.filter(vaga_emprego__ativo=True).distinct().count(),
                
                # Vagas ativas
                'vagas_ativas': Vaga_Emprego.objects.filter(ativo=True).count(),
                
                # Novos candidatos (no período especificado)
                'novos_candidatos_absoluto': Candidato.objects.filter(dt_inclusao__gte=data_limite_novos).count(),
                'novos_candidatos_online': Candidato.objects.filter(
                    dt_inclusao__gte=data_limite_novos, 
                    candidato_online=True
                ).count(),
                'novos_candidatos_balcao': Candidato.objects.filter(
                    dt_inclusao__gte=data_limite_novos, 
                    candidato_online=False
                ).count(),
                
                # Total de candidatos
                'total_candidatos_absoluto': Candidato.objects.count(),
                'total_candidatos_online': Candidato.objects.filter(candidato_online=True).count(),
                'total_candidatos_balcao': Candidato.objects.filter(candidato_online=False).count(),
                
                # Total de empresas parceiras
                'total_empresas_parceiras': Empresa.objects.count(),
            }
            
            # 2. TOP CARGOS (flexível por parâmetro)
            top_cargos = list(
                Vaga_Emprego.objects
                .values('cargo__nome')
                .annotate(quantidade=Count('id'))
                .order_by('-quantidade')[:top_limit]
                .values_list('cargo__nome', 'quantidade')
            )
            top_cargos_dados = [{'titulo': nome, 'quantidade': qtd} for nome, qtd in top_cargos]
            
            # 3. EVOLUÇÃO MENSAL DE CANDIDATOS (últimos 12 meses)
            evolucao_mensal_candidatos = []
            for i in range(12):
                data_inicio = timezone.now().replace(day=1) - timedelta(days=30*i)
                data_fim = data_inicio + timedelta(days=31)
                total = Candidato.objects.filter(
                    dt_inclusao__gte=data_inicio,
                    dt_inclusao__lt=data_fim
                ).count()
                evolucao_mensal_candidatos.append({
                    'mes': data_inicio.strftime('%Y-%m'),
                    'total': total
                })
            evolucao_mensal_candidatos.reverse()
            
            # 4. CANDIDATOS POR BAIRRO
            candidatos_por_bairro = list(
                Candidato.objects
                .exclude(bairro__isnull=True)
                .exclude(bairro__exact='')
                .values('bairro')
                .annotate(total=Count('id'))
                .order_by('-total')[:20]  # Top 20 bairros
            )
            
            # 5. VAGAS POR BAIRRO (baseado no bairro da empresa)
            vagas_por_bairro = list(
                Vaga_Emprego.objects
                .exclude(empresa__bairro__isnull=True)
                .exclude(empresa__bairro__exact='')
                .values('empresa__bairro')
                .annotate(total=Count('id'))
                .order_by('-total')[:20]  # Top 20 bairros
            )
            
            # 6. CANDIDATOS POR FUNCIONÁRIO (quem fez o encaminhamento)
            candidatos_por_funcionario = list(
                Candidato.objects
                .filter(funcionario_encaminhamento__isnull=False)
                .values('funcionario_encaminhamento__first_name', 'funcionario_encaminhamento__last_name')
                .annotate(total=Count('id'))
                .order_by('-total')[:10]
            )
            # Formatando nome completo
            candidatos_por_funcionario = [
                {
                    'funcionario': f"{item['funcionario_encaminhamento__first_name']} {item['funcionario_encaminhamento__last_name']}".strip(),
                    'total': item['total']
                } for item in candidatos_por_funcionario
            ]
            
            # 7. TOP EMPRESAS (com mais candidatos)
            top_empresas = list(
                Empresa.objects
                .annotate(total_candidatos=Count('vaga_emprego__candidato'))
                .filter(total_candidatos__gt=0)
                .order_by('-total_candidatos')[:top_limit]
                .values('nome', 'total_candidatos')
            )
            
            # 8. CANDIDATOS POR ESCOLARIDADE
            candidatos_por_escolaridade = list(
                Candidato.objects
                .values('escolaridade__nome')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # 9. RELAÇÃO CANDIDATOS ONLINE/BALCÃO POR MÊS (últimos 12 meses)
            relacao_online_balcao_mensal = []
            for i in range(12):
                data_inicio = timezone.now().replace(day=1) - timedelta(days=30*i)
                data_fim = data_inicio + timedelta(days=31)
                
                online = Candidato.objects.filter(
                    dt_inclusao__gte=data_inicio,
                    dt_inclusao__lt=data_fim,
                    candidato_online=True
                ).count()
                
                balcao = Candidato.objects.filter(
                    dt_inclusao__gte=data_inicio,
                    dt_inclusao__lt=data_fim,
                    candidato_online=False
                ).count()
                
                relacao_online_balcao_mensal.append({
                    'mes': data_inicio.strftime('%Y-%m'),
                    'online': online,
                    'balcao': balcao
                })
            relacao_online_balcao_mensal.reverse()
            
            # 10. ÚLTIMAS VAGAS A ENTRAR (últimas 10)
            ultimas_vagas_entrar = list(
                Vaga_Emprego.objects
                .select_related('empresa', 'cargo')
                .order_by('-dt_inclusao')[:10]
                .values(
                    'id', 'empresa__nome', 'cargo__nome', 
                    'dt_inclusao', 'quantidadeVagas', 'ativo'
                )
            )
            
            # 11. ÚLTIMAS VAGAS A SAIR (últimas 10 desativadas com contagem de candidatos)
            ultimas_vagas_sair = []
            vagas_desativadas = (
                Vaga_Emprego.objects
                .filter(ativo=False, dt_desativacao__isnull=False)
                .select_related('empresa', 'cargo')
                .order_by('-dt_desativacao')[:10]
            )
            
            for vaga in vagas_desativadas:
                ultimas_vagas_sair.append({
                    'id': vaga.id,
                    'empresa__nome': vaga.empresa.nome,
                    'cargo__nome': vaga.cargo.nome,
                    'dt_desativacao': vaga.dt_desativacao,
                    'quantidadeVagas': vaga.quantidadeVagas,
                    'total_candidatos': vaga.candidato_set.count()
                })
            
            # Formatação dos dados para JSON
            response_data = {
                # Estatísticas principais
                'estatisticas_basicas': estatisticas_basicas,
                
                # Gráficos e dados estruturados
                'graficos': {
                    'top_cargos': top_cargos_dados,
                    'evolucao_mensal_candidatos': evolucao_mensal_candidatos,
                    'candidatos_por_bairro': candidatos_por_bairro,
                    'vagas_por_bairro': vagas_por_bairro,
                    'candidatos_por_funcionario': candidatos_por_funcionario,
                    'relacao_online_balcao_mensal': relacao_online_balcao_mensal,
                },
                
                # Rankings e listas
                'rankings': {
                    'top_empresas': top_empresas,
                    'candidatos_por_escolaridade': candidatos_por_escolaridade,
                },
                
                # Atividades recentes
                'atividades_recentes': {
                    'ultimas_vagas_entrar': ultimas_vagas_entrar,
                    'ultimas_vagas_sair': ultimas_vagas_sair,
                },
                
                # Metadados
                'parametros': {
                    'periodo_novos_candidatos_dias': periodo_dias,
                    'top_limit': top_limit,
                },
                'data_atualizacao': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return Response(response_data)
            
        except Exception as e:
            # Em caso de erro, retorna dados básicos
            return Response({
                'error': 'Erro ao gerar indicadores',
                'message': str(e),
                'estatisticas_basicas': {
                    'cargos_ativos': 0,
                    'vagas_ativas': Vaga_Emprego.objects.filter(ativo=True).count(),
                    'total_candidatos_absoluto': Candidato.objects.count(),
                    'total_empresas_parceiras': Empresa.objects.count(),
                },
                'data_atualizacao': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }, status=500)

from django.utils import timezone
from datetime import timedelta

from vagas.models import Vaga_Emprego, Candidato
from vagas.functions.filters import processar_filtro_periodo
from vagas.functions.stats_general import get_estatisticas_gerais
from vagas.functions.stats_advanced import calcular_funil_vagas
from vagas.functions.stats_temporal import gerar_series_candidatos_por_mes_com_filtro
from vagas.functions.stats_geographic import (
    candidatos_por_bairro,
    bairros_por_vaga,
    top_empresas_por_vagas,
    top_cargos_por_candidatos,
)

class IndicadoresAvancadosDashboard(APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Processa o filtro de período (GET/POST/sessão)
            data_inicio, data_fim, filtro_aplicado, limpar = processar_filtro_periodo(request)
            if limpar:
                return Response({'redirect': True})  # sinaliza que filtros foram limpos

            # Fallback (últimos 90 dias)
            if not data_inicio or not data_fim:
                data_fim = timezone.now().date()
                data_inicio = data_fim - timedelta(days=90)

            # QuerySets principais filtrados
            vagas_query = Vaga_Emprego.objects.filter(dt_inclusao__range=(data_inicio, data_fim))
            candidatos_query = Candidato.objects.filter(dt_inclusao__range=(data_inicio, data_fim))

            # Estatísticas gerais
            estatisticas = get_estatisticas_gerais(vagas_query, candidatos_query)

            # Funil de vagas (não sei porque dei o nome funil)
            funil = calcular_funil_vagas(vagas_query, candidatos_query)

            # Séries temporais (mensais)
            series_candidatos = gerar_series_candidatos_por_mes_com_filtro(
                candidatos_query,
                data_inicio=data_inicio,
                data_fim=data_fim,
                max_meses=12
            )

            # Dados geográficos
            total_candidatos = candidatos_query.count()
            geo_candidatos = candidatos_por_bairro(candidatos_query, total_candidatos)
            geo_vagas = bairros_por_vaga(vagas_query, filtro_aplicado=filtro_aplicado)

            # Rankings e tops
            top_empresas = top_empresas_por_vagas(vagas_query)
            top_cargos = top_cargos_por_candidatos(candidatos_query)

            # Estrutura de resposta
            response_data = {
                'filtros': {
                    'data_inicio': data_inicio.strftime('%Y-%m-%d'),
                    'data_fim': data_fim.strftime('%Y-%m-%d'),
                    'filtro_aplicado': filtro_aplicado,
                },
                'estatisticas': estatisticas,
                'funil': funil,
                'series': {
                    'candidatos_por_mes': series_candidatos,
                },
                'geografico': {
                    'candidatos_por_bairro': geo_candidatos,
                    'vagas_por_bairro': geo_vagas,
                },
                'rankings': {
                    'top_empresas': top_empresas,
                    'top_cargos': top_cargos,
                },
                'data_atualizacao': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            return Response(response_data)

        except Exception as e:
            return Response({
                'error': 'Erro ao gerar indicadores avançados',
                'message': str(e)
            }, status=500)
