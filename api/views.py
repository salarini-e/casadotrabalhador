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
            # Período para análise (último ano)
            data_limite = timezone.now() - timedelta(days=365)
            
            # 1. ESTATÍSTICAS GERAIS
            estatisticas_gerais = {
                'total_vagas_ativas': Vaga_Emprego.objects.filter(ativo=True).count(),
                'total_vagas_inativas': Vaga_Emprego.objects.filter(ativo=False).count(),
                'total_empresas': Empresa.objects.count(),
                'total_candidatos': Candidato.objects.count(),
                'total_candidatos_unicos': Candidato.objects.values('cpf').distinct().count(),
                'total_requisicoes': RequisicaoVaga.objects.count(),
                'requisicoes_aprovadas': RequisicaoVaga.objects.filter(status_requisicao='AP').count(),
                'candidatos_selecionados': CandidatoSelecionado.objects.filter(status_selecao='AP').count(),
            }
            
            # 2. VAGAS POR MÊS - Método simplificado para evitar problemas de timezone
            vagas_por_mes = []
            for i in range(12):
                data_inicio = timezone.now().replace(day=1) - timedelta(days=30*i)
                data_fim = data_inicio + timedelta(days=31)
                total = Vaga_Emprego.objects.filter(
                    dt_inclusao__gte=data_inicio,
                    dt_inclusao__lt=data_fim
                ).count()
                vagas_por_mes.append({
                    'mes': data_inicio.strftime('%Y-%m'),
                    'total': total
                })
            vagas_por_mes.reverse()
            
            # 3. CANDIDATOS POR MÊS - Método simplificado
            candidatos_por_mes = []
            for i in range(12):
                data_inicio = timezone.now().replace(day=1) - timedelta(days=30*i)
                data_fim = data_inicio + timedelta(days=31)
                total = Candidato.objects.filter(
                    dt_inclusao__gte=data_inicio,
                    dt_inclusao__lt=data_fim
                ).count()
                candidatos_por_mes.append({
                    'mes': data_inicio.strftime('%Y-%m'),
                    'total': total
                })
            candidatos_por_mes.reverse()
            
            # 4. REQUISIÇÕES POR STATUS
            requisicoes_por_status = (
                RequisicaoVaga.objects
                .values('status_requisicao')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # 5. TOP 10 CARGOS MAIS DEMANDADOS
            top_cargos = (
                Vaga_Emprego.objects
                .values('cargo__nome')
                .annotate(total_vagas=Count('id'))
                .order_by('-total_vagas')[:10]
            )
            
            # 6. TOP 10 EMPRESAS COM MAIS VAGAS
            top_empresas = (
                Vaga_Emprego.objects
                .values('empresa__nome')
                .annotate(total_vagas=Count('id'))
                .order_by('-total_vagas')[:10]
            )
            
            # 7. ESCOLARIDADE MAIS REQUISITADA
            escolaridade_requisitada = (
                Vaga_Emprego.objects
                .values('escolaridade__nome')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # 8. DISTRIBUIÇÃO POR TIPO DE VAGA
            tipos_vaga = (
                Vaga_Emprego.objects
                .values('tipo_de_vaga')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # 9. EXPERIÊNCIA REQUISITADA
            experiencia_requisitada = (
                Vaga_Emprego.objects
                .values('experiencia')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            
            # 10. INDICADORES DE CONVERSÃO
            total_vagas = Vaga_Emprego.objects.count()
            total_candidatos_count = Candidato.objects.count()
            total_requisicoes_count = RequisicaoVaga.objects.count()
            
            conversao = {
                'taxa_aprovacao_requisicoes': round(
                    (RequisicaoVaga.objects.filter(status_requisicao='AP').count() / 
                     max(total_requisicoes_count, 1)) * 100, 2
                ),
                'media_candidatos_por_vaga': round(
                    total_candidatos_count / max(total_vagas, 1), 2
                ),
                'vagas_com_candidatos': Vaga_Emprego.objects.filter(candidato__isnull=False).distinct().count(),
                'percentual_vagas_com_candidatos': round(
                    (Vaga_Emprego.objects.filter(candidato__isnull=False).distinct().count() / 
                     max(total_vagas, 1)) * 100, 2
                )
            }
            
            # 11. ÚLTIMAS ATIVIDADES (últimos 30 dias)
            data_30_dias = timezone.now() - timedelta(days=30)
            atividades_recentes = {
                'novas_vagas': Vaga_Emprego.objects.filter(dt_inclusao__gte=data_30_dias).count(),
                'novos_candidatos': Candidato.objects.filter(dt_inclusao__gte=data_30_dias).count(),
                'novas_requisicoes': RequisicaoVaga.objects.filter(dt_inclusao__gte=data_30_dias).count(),
                'vagas_desativadas': Vaga_Emprego.objects.filter(
                    dt_desativacao__gte=data_30_dias
                ).count(),
            }
            
            # 12. EMPRESAS MAIS ATIVAS
            empresas_ativas = (
                Empresa.objects
                .annotate(
                    total_candidatos=Count('vaga_emprego__candidato'),
                    vagas_ativas=Count('vaga_emprego', filter=Q(vaga_emprego__ativo=True))
                )
                .filter(total_candidatos__gt=0)
                .order_by('-total_candidatos')[:10]
                .values('nome', 'total_candidatos', 'vagas_ativas')
            )
            
            # Formatação dos dados para JSON
            response_data = {
                'estatisticas_gerais': estatisticas_gerais,
                'graficos': {
                    'vagas_por_mes': vagas_por_mes,
                    'candidatos_por_mes': candidatos_por_mes,
                    'requisicoes_por_status': [
                        {
                            'status': dict(RequisicaoVaga.STATUS_CHOICES).get(item['status_requisicao'], item['status_requisicao']),
                            'total': item['total']
                        } for item in requisicoes_por_status
                    ],
                    'top_cargos': list(top_cargos),
                    'top_empresas': list(top_empresas),
                    'escolaridade_requisitada': list(escolaridade_requisitada),
                    'tipos_vaga': [
                        {
                            'tipo': dict(Vaga_Emprego.TIPO_DE_VAGA_CHOICES).get(item['tipo_de_vaga'], item['tipo_de_vaga']),
                            'total': item['total']
                        } for item in tipos_vaga
                    ],
                    'experiencia_requisitada': [
                        {
                            'experiencia': dict(Vaga_Emprego.EXPERIENCIA_CHOICES).get(item['experiencia'], item['experiencia']),
                            'total': item['total']
                        } for item in experiencia_requisitada
                    ]
                },
                'conversao': conversao,
                'atividades_recentes': atividades_recentes,
                'empresas_ativas': list(empresas_ativas),
                'data_atualizacao': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return Response(response_data)
            
        except Exception as e:
            # Em caso de erro, retorna dados básicos
            return Response({
                'error': 'Erro ao gerar indicadores',
                'message': str(e),
                'estatisticas_gerais': {
                    'total_vagas_ativas': Vaga_Emprego.objects.filter(ativo=True).count(),
                    'total_vagas_inativas': Vaga_Emprego.objects.filter(ativo=False).count(),
                    'total_empresas': Empresa.objects.count(),
                    'total_candidatos': Candidato.objects.count(),
                },
                'data_atualizacao': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }, status=500)
