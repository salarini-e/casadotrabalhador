# Import company views
from .company_views.solicitation import (
    empresa_solicitar_desativacao_vaga,
    empresa_solicitar_desativacao_formulario,
    empresa_solicitacoes_desativacao,
    solicitacao_desativacao_sucesso
)

# Import admin views
from .admin_views.solicitation import (
    admin_solicitacoes_desativacao,
    admin_processar_solicitacao_desativacao
)

# PARA AS VIEWS
import calendar
import json
from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
# AUTH
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.utils.timezone import make_aware
# MODELS E FORMS
from .forms import *
from .validations import validate_CPF
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
# OUTROS
from django.http import FileResponse, Http404, JsonResponse
import requests
import pdfkit
from datetime import date, datetime
# VIEWS
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings

from openpyxl import Workbook
from openpyxl.styles import Alignment
from urllib.parse import quote

from .models import Slide, Vaga_Emprego, CandidatoSelecionado, ResponsavelEmpresa, Cargo, Escolaridade, Empresa, Candidato, RequisicaoVaga, HistoricoRequisicao
from django.http import HttpResponseForbidden, HttpResponse

from autenticacao.models import Pessoa
from django.shortcuts import get_object_or_404


import os
import subprocess
from django.http import HttpResponse
from django.conf import settings
from balcao_de_emprego.settings import db_name, db_user, db_host, db_passwd
from django.views import View

class BackupDatabaseView(View):
    def get(self, request):
        # Caminho para salvar o backup localmente
        backup_file_path = os.path.join(settings.MEDIA_ROOT, f'{db_name}_backup.sql')

        command = [
            'mysqldump',
            '-h', db_host,
            '-P', '3306',
            '-u', db_user,
            f'--password={db_passwd}',
            db_name
        ]

        try:
            # Executando o comando e salvando o backup no arquivo
            with open(backup_file_path, 'w') as backup_file:
                subprocess.run(command, stdout=backup_file, check=True)

            # Retornar o arquivo de backup como resposta para download
            with open(backup_file_path, 'rb') as backup_file:
                response = HttpResponse(backup_file.read(), content_type='application/sql')
                response['Content-Disposition'] = f'attachment; filename={os.path.basename(backup_file_path)}'
                return response

        except subprocess.CalledProcessError as e:
            # Lidar com erros durante o backup
            return HttpResponse(f"Erro ao criar backup: {str(e)}", status=500)
        
def staff_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Acesso negado. Você não é um funcionário.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Acesso negado. Você não é um super usuário.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@staff_required
@superuser_required
def exportar_vagas_excel(request):
    # Filtrar os registros onde ativo=True
    vagas_ativas = Vaga_Emprego.objects.filter(ativo=True)

    # Criar um objeto Workbook
    wb = Workbook()
    ws = wb.active

    # Adicionar cabeçalhos das colunas
    ws.append(['ID da Vaga', 'Nome da Empresa', 'Nome do Cargo', 'Número de Vagas', 'Data de Inclusão', 'Telefone', 'Whatsapp', 'Email'])

    # Preencher os dados
    for vaga in vagas_ativas:
        # Usar email da vaga se existir, senão usar da empresa
        email_encaminhamento = vaga.email if vaga.email else vaga.empresa.email
        ws.append([vaga.id, vaga.empresa.nome, vaga.cargo.nome, vaga.quantidadeVagas, str(vaga.dt_inclusao), vaga.empresa.telefone, vaga.empresa.whatsapp, email_encaminhamento])

    # Criar uma resposta HTTP
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename={quote("vagas_ativas.xlsx")}'

    # Salvar o conteúdo do arquivo Excel na resposta
    wb.save(response)

    return response


def visualizar_vaga(request, id):
    vaga = Vaga_Emprego.objects.get(id=id)
    
    # Contar candidatos
    total_candidatos = Candidato.objects.filter(vaga=vaga).count()
    
    import datetime
    data_atual = datetime.datetime.now()        
    context = {
        'vaga': vaga,
        'total_candidatos': total_candidatos,
        'mes': data_atual.month,
        'ano': data_atual.year,
        'id': id,
    }

    return render(request, 'vagas/visualizar_vaga.html', context)

# def vagas(request):    
#     vagas = Vaga_Emprego.objects.filter(ativo=True)
#     vagas_sem_repetir_cargo = Vaga_Emprego.objects.filter(ativo=True).values('cargo').distinct()
#     vagas_em_destaque = Vaga_Emprego.objects.filter(ativo=True, destaque=True)
#     qnt_vagas = len(vagas)
#     cont = 0
#     for i in vagas:
#         cont += i.quantidadeVagas

#     print(vagas_sem_repetir_cargo)
#     context = {
#         'vagas': Vaga_Emprego.objects.filter(ativo=True).order_by('cargo__nome'),
#         'vagas_sem_repetir_cargo': vagas_sem_repetir_cargo,
#         'vagas_destaque': vagas_em_destaque,
#         'destaque': False if len(vagas_em_destaque) == 0 else True,
#         'bairros': Empresa.objects.order_by('bairro').values_list('bairro').distinct(),
#         'escolaridades': Escolaridade.objects.all().values(),        
#         'qnt_cargos': qnt_vagas,
#         'qnt_vagas': cont,        
#         'eventos': Slide.objects.all(),
#     }
#     return render(request, 'vagas/vagas_disponiveis.html', context)

def vagas(request):    
    vagas = Vaga_Emprego.objects.filter(ativo=True).select_related('cargo').order_by('cargo__nome')
    
    # Criar dicionário para agrupar vagas por cargo
    vagas_por_cargo = {}
    for vaga in vagas:
        cargo_nome = vaga.cargo.nome
        if cargo_nome not in vagas_por_cargo:
            vagas_por_cargo[cargo_nome] = []
        vagas_por_cargo[cargo_nome].append(vaga)

    vagas_em_destaque = vagas.filter(ativo=True, destaque=True)

    # Contar total de vagas
    total_vagas = sum(vaga.quantidadeVagas for vaga in vagas)
    print('Vagas em destaque:', vagas_em_destaque)
    
    # Buscar apenas bairros de empresas que possuem vagas ativas
    bairros_com_vagas_ativas = Empresa.objects.filter(
        vaga_emprego__ativo=True
    ).order_by('bairro').values_list('bairro', flat=True).distinct()
    
    context = {
        'vagas': vagas,
        'vagas_por_cargo': vagas_por_cargo,  
        'vagas_destaque': vagas_em_destaque,
        'destaque': bool(vagas_em_destaque),
        'bairros': bairros_com_vagas_ativas,
        'escolaridades': Escolaridade.objects.all().values(),        
        'qnt_cargos': len(vagas_por_cargo),
        'qnt_vagas': total_vagas,        
        'eventos': Slide.objects.all(),
    }
    return render(request, 'vagas/vagas_disponiveis.html', context)

def home(request):
    vagas_destaque = Vaga_Emprego.objects.filter(destaque=True)
    vagas = Vaga_Emprego.objects.filter(ativo=True)
    qnt_vagas = len(vagas)
    cont = 0
    for i in vagas:
        cont += i.quantidadeVagas
    if len(vagas_destaque)>0:
        msg='Vaga em destaque'
    else:
        msg='Vagas em destaques'
    context = {
        'msg': msg,
        'vagas': vagas_destaque,
        'qnt_cargos': qnt_vagas,
        'qnt_vagas': cont,
        'qnt_destaque': len(vagas_destaque),
        'eventos': Slide.objects.all(),
    }
    return render(request, 'vagas/index.html', context)


@login_required
@staff_required
def cadastrar_empresa(request):
    if request.method == 'POST':
        form = Form_Empresa(request.POST)
        if form.is_valid():
            form.save()
            context = {
                'tipo_cadastro': 'Cadastrar',
                'form': Form_Empresa(initial={'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Empresa cadastrada com sucesso!']
            }
            return render(request, 'vagas/infoempresa cadastrar.html', context)
            # return render(request, 'vagas/cadastrar_empresa.html', context)
    else:
        form = Form_Empresa(initial={'user': request.user})
    context = {
        'form': form,
        'tipo_cadastro': 'Cadastrar',
    }
    return render(request, 'vagas/infoempresa cadastrar.html', context)
    # return render(request, 'vagas/cadastrar_empresa.html', context)


@login_required
@staff_required
def alterar_empresa(request, id):
    empresa = Empresa.objects.get(id=id)
    if request.method == 'POST':
        request_POST = request.POST.copy()
        request_POST['user'] = request.user.id
        form = Form_Empresa(request_POST, instance=empresa)
        if form.is_valid():
            form.save()
            # Redireciona de volta para o perfil da empresa com mensagem de sucesso
            messages.success(request, 'Empresa alterada com sucesso!')
            return redirect(f'/empresa/profile/{empresa.id}/')
        else:
            print(form.errors)
            messages.error(request, 'Erro ao alterar empresa. Verifique os dados e tente novamente.')
    else:
        form = Form_Empresa(instance=empresa)
    
    context = {
        'form': form,
        'tipo_cadastro': 'Alterar',
    }
    return render(request, 'vagas/editar_empresa.html', context)


@login_required
@staff_required
def cadastrar_cargo(request):
    if request.method == 'POST':
        print(request.POST)
        form = Form_Cargo(request.POST)
        if form.is_valid():
            form.save()            
        else:
            print(form.errors)
            messages.error(request, 'Erro ao cadastrar cargo. Verifique os dados e tente novamente.')
        return redirect('vagas:listar_cargos')
    else:
        form = Form_Cargo(initial={'user': request.user})
    context = {
        'form': form,
        'tipo_cadastro': 'Cadastrar',
    }
    return render(request, 'vagas/cadastrar_cargo.html', context)


@login_required
@staff_required
def alterar_cargo(request, id):
    cargo = Cargo.objects.get(id=id)
    if request.method == 'POST':
        form = Form_Cargo(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cargo alterado com sucesso!')
            return redirect('vagas:listar_cargos')
        else:
            print(form.errors)
            messages.error(request, 'Erro ao alterar cargo. Verifique os dados e tente novamente.')
    else:
        form = Form_Cargo(instance=cargo)
    context = {
        'form': form,
        'tipo_cadastro': 'Alterar',
    }
    return render(request, 'vagas/cadastrar_cargo.html', context)


@login_required
@staff_required
def cadastrar_escolaridade(request):
    if request.method == 'POST':
        form = Form_Escolaridade(request.POST)
        if form.is_valid():
            form.save()
            return redirect('vagas:escolaridades')
    else:
        form = Form_Escolaridade(initial={'user': request.user})
    context = {
        'form': form,
        'tipo_cadastro': 'Cadastrar',
    }
    return render(request, 'vagas/cadastrar_escolaridade.html', context)


@login_required
@staff_required
def alterar_escolaridade(request, id):
    escolaridade = Escolaridade.objects.get(id=id)
    if request.method == 'POST':
        form = Form_Escolaridade(request.POST, instance=escolaridade)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escolaridade alterada com sucesso!')
            return redirect('vagas:escolaridades')
        else:
            print(form.errors)
            messages.error(request, 'Erro ao alterar escolaridade. Verifique os dados e tente novamente.')
    else:
        form = Form_Escolaridade(instance=escolaridade)
    context = {
        'form': form,
        'tipo_cadastro': 'Alterar',
    }
    return render(request, 'vagas/cadastrar_escolaridade.html', context)


@login_required
@staff_required
def cadastrar_vagaOfertada(request):
    if request.method == 'POST':
        gambiarra = {}
        print('request', request.POST)
        for item in request.POST:
            if item == 'cargo':
                try:
                    gambiarra[item] = Cargo.objects.get(
                        nome=request.POST[item]).id
                except:
                    gambiarra[item] = request.POST[item]
            elif item == 'empresa':
                try:
                    gambiarra[item] = Empresa.objects.get(
                        nome=request.POST[item]).id
                except:
                    gambiarra[item] = request.POST[item]
            else:
                gambiarra[item] = request.POST[item]
            gambiarra['user'] = request.user.id
            gambiarra['ativo'] = True
        form = CadastroInternoVagasForm(gambiarra)
        print('gambiarra',gambiarra)
        if form.is_valid():
            form.save()
            context = {
                'tipo_cadastro': 'cadastrar',
                'form': CadastroInternoVagasForm(initial={'ativo': True, 'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Vaga cadastrada com sucesso!']
            }
            return render(request, 'vagas/cadastrar_vagaOfertada.html', context)
        else:
            print('form.errors', form.errors)
    else:
        form = CadastroInternoVagasForm(initial={'ativo': True, 'user': request.user})
    context = {
        'tipo_cadastro': 'cadastrar',
        'form': form,
        'hidden': ['user', 'ativo']
    }
    return render(request, 'vagas/cadastrar_vagaOfertada.html', context)


@login_required
@staff_required
def remover_vaga(request, id):
    if request.method == 'POST':
        try:
            vaga = Vaga_Emprego.objects.get(id=request.POST['remover'])
            vaga.ativo = False
            vaga.save()
            return redirect('vagas:vagas')
        except:
            pass
    context = {
        'id': id,
        'vaga': Vaga_Emprego.objects.get(id=id)
    }
    return render(request, 'vagas/remover_vagaOfertada.html', context)


@login_required
@staff_required
def cadastrar_vaga_emLote(request):
    if request.method == 'POST':
        try:
            empresa = Empresa.objects.get(nome=request.POST['empresa'])
            success = True
        except:
            success = False
        if success:
            form = CadastroInternoVagasForm(
                initial={'ativo': True, 'user': request.user})
            context = {
                'empresa': request.POST['empresa'],
                'tipo_cadastro': 'cadastrar',
                'form': form,
                'hidden': ['user', 'ativo']
            }
            return render(request, 'vagas/cadastrar_vagas_emLote_2.html', context)
    form = CadastroInternoVagasForm(initial={'ativo': True, 'user': request.user})
    context = {
        'tipo_cadastro': 'cadastrar',
        'form': form,
        'hidden': ['user', 'ativo']
    }
    return render(request, 'vagas/cadastrar_vagas_emLote.html', context)


def get_empresa(request):
    try:
        # empresas=Empresa.objects.filter(nome__startswith=request.GET.get('nome')).order_by('nome')
        empresas = Empresa.objects.filter(
            nome__icontains=request.GET.get('empresa')).order_by('nome')
    except Exception as E:
        empresas = None
    context = {
        'results': empresas,
    }
    return render(request, 'vagas/resultEmpresaSearchs.html', context)


def get_cargo(request):
    try:
        # empresas=Empresa.objects.filter(nome__startswith=request.GET.get('nome')).order_by('nome')
        cargos = Cargo.objects.filter(
            nome__icontains=request.GET.get('vaga')).order_by('nome')
    except Exception as E:
        cargos = None
    context = {
        'results': cargos,
    }
    return render(request, 'vagas/resultVagaSearchs.html', context)




@login_required
@staff_required
def alterar_vaga(request, id):
    if request.method == 'POST':
        gambiarra = {}
        for item in request.POST:
            if item == 'cargo':
                try:
                    gambiarra[item] = Cargo.objects.get(
                        nome=request.POST[item]).id
                except:
                    gambiarra[item] = request.POST[item]
            elif item == 'empresa':
                try:
                    gambiarra[item] = Empresa.objects.get(
                        nome=request.POST[item]).id
                except:
                    gambiarra[item] = request.POST[item]
            else:
                gambiarra[item] = request.POST[item]
        gambiarra['user'] = request.user.id
        gambiarra['ativo'] = True
        form = CadastroInternoVagasForm(gambiarra)
        vaga = Vaga_Emprego.objects.get(id=id)
        if form.is_valid():

            form = CadastroVagasForm(gambiarra, instance=vaga)
            print(gambiarra)
            print(form.errors)
            
            form.save()
            return redirect('vagas:vagas')
        else:
            print(form.errors)
    else:
        vaga = Vaga_Emprego.objects.get(id=id)
        form = CadastroInternoVagasForm(instance=vaga)

    context = {
        'id': id,
        'tipo_cadastro': 'Alterar',
        'form': form,
        'hidden': ['user', 'ativo'],
        'cargo': vaga.cargo.nome,
        'empresa': vaga.empresa.nome
    }
    return render(request, 'vagas/cadastrar_vagaOfertada.html', context)




@staff_required
def empresas(request):
    context = {
        'empresas': Empresa.objects.all()
    }
    return render(request, 'vagas/listar_empresas.html', context)

@staff_required
def escolaridades(request):
    context = {
        'escolaridades': Escolaridade.objects.all()
    }
    return render(request, 'vagas/listar_escolaridade.html', context)

@staff_required
def listar_cargos(request):
    context = {
        'cargos': Cargo.objects.all()
    }
    return render(request, 'vagas/listar_cargos.html', context)

@staff_required
def imprimir_vagas(request):
    vagas = Vaga_Emprego.objects.filter(ativo=True).order_by('cargo__nome')
    cont = 0
    for i in vagas:
        cont += i.quantidadeVagas

    context = {
        'vagas': vagas,
        'total': cont
    }
    return render(request, 'vagas/imprimir_vagas.html', context)


@xframe_options_exempt
def vagas_table(request):
    context = {
        'vagas': Vaga_Emprego.objects.filter(ativo=True)
    }
    return render(request, 'vagas/vagas.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        # Abaixo recebemos a validação da API do Google do reCAPTCHA
        ''' Begin reCAPTCHA validation '''
        recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            'secret': '6LdiIsweAAAAADv7tYKHZ1fCP4pi6FwIZTw4X4Rl',
            'response': recaptcha_response
        }
        r = requests.post(
            'https://www.google.com/recaptcha/api/siteverify', data=data)
        result = r.json()
        ''' End reCAPTCHA validation '''

        # Se o reCAPTCHA garantir que o usuário é um robô
        if result['success']:
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                try:
                    return redirect(request.GET['next'])
                except:
                    return redirect('vagas:home')
            else:
                context = {
                    'error': True,
                }
                return render(request, 'registration/login.html', context)
        else:
            context = {
                'error2': True,
            }
            return render(request, 'registration/login.html', context)
    return render(request, 'registration/login.html')


def encaminhar(request, id):
    today = date.today()
    vaga = Vaga_Emprego.objects.get(id=id)
    if request.method == 'POST':
        context = {
            'vaga': vaga,
            'date': today,
            'candidato': {'nome': request.POST['nome']}
        }
        return render(request, 'vagas/encaminhar.html', context)

    return redirect('vagas:encaminhamento', id)


def encaminhamento(request, id, user_id=0):
    candidato = Candidato.objects.get(id=id)
    if str(int(user_id)) != str(int(0)):
        if request.user.is_staff:
            user = User.objects.get(id=user_id)
        else:
            user = False    
    else:
        user = False

    from datetime import date
    today = date.today()
    
    # Determinar email de encaminhamento prioritário
    email_encaminhamento = candidato.vaga.email if candidato.vaga.email else candidato.vaga.empresa.email
    
    context = {
        'vaga': candidato.vaga,
        'date': today,
        'candidato': candidato,
        'sistema': True,
        'user': user,
        'email_encaminhamento': email_encaminhamento
    }
    if request.user.is_staff:
        return render(request, 'vagas/encaminhar.html', context)
    return render(request, 'vagas/encaminhamento_online.html', context)


def gera_encaminhamento_to_pdf(request, id, user_id=0):
    try:
        url_pdf = '/home/casa_do_trabalhador/site/balcao_de_emprego/vagas/static/pdf/' + \
            str(id)+'.pdf'
        # url_pdf='/home/eduardo/projects/casadotrabalhador/vagas/static/pdf/'+id+'.pdf'
        pdfkit.from_url('https://casadotrabalhador.pmnf.rj.gov.br/visualizar-vaga/alt0x' +
                        str(id)+'0'+str(user_id)+'01/encaminhamento', url_pdf)
        # pdfkit.from_url('http://localhost:8000/visualizar-vaga/alt0x'+str(id)+'0'+str(user_id)+'01/encaminhamento', url_pdf)

        context = {
            'pdf': url_pdf
        }
        try:
            return FileResponse(open(url_pdf, 'rb'), content_type='application/pdf')
        except Exception as E:
            raise Http404()
    except Exception as E:
        return redirect('/')


def candidatarse(request, id):
    # Inicializar pessoa com valor padrão para evitar UnboundLocalError
    pessoa = {'nome': '', 'cpf': '', 'email': '', 'celular': ''}
    
    if request.user.is_staff:
        form = Form_Candidato(initial={'vaga': id, 'candidato_online': False})
        pessoa = {'nome': '', 'cpf': '', 'email': '', 'celular': ''}
        print('usuário staff')
    else:
        print('usuário normal')
        if request.user.is_authenticated:
            try:
                pessoa_obj = Pessoa.objects.get(user=request.user)
                pessoa = {
                    'nome': pessoa_obj.nome or '',
                    'cpf': pessoa_obj.cpf or '',
                    'email': pessoa_obj.email or '',
                    'celular': pessoa_obj.telefone or ''
                }
                form = Form_Candidato(initial={'vaga': id, 'candidato_online': True, 'nome': pessoa_obj.nome, 'cpf': pessoa_obj.cpf, 'email': pessoa_obj.email, 'celular': pessoa_obj.telefone})
            except Pessoa.DoesNotExist:
                # Se pessoa não existe, usar valores padrão
                pessoa = {'nome': '', 'cpf': '', 'email': '', 'celular': ''}
                form = Form_Candidato(initial={'vaga': id, 'candidato_online': True})
        elif request.user.is_anonymous:
            form = Form_Candidato(initial={'vaga': id, 'candidato_online': True})
            pessoa = {'nome': '', 'cpf': '', 'email': '', 'celular': ''}

    if request.method == 'POST':
        form = Form_Candidato(request.POST)
        if form.is_valid():

            try:
                cpf = validate_CPF(request.POST['cpf'])
                candidato = Candidato.objects.get(cpf=cpf, vaga_id=id)
                form = Form_Candidato(request.POST, instance=candidato)

            except Exception as e:
                pass

            candidato = form.save()
            # return render(request, 'vagas/encaminhar.html', context)
            if request.user.is_staff:
                candidato.funcionario_encaminhamento = request.user
                candidato.dt_atualizacao = datetime.today()
                candidato.save()

                return redirect('vagas:encaminhamento', id=candidato.id, user_id=request.user.id)
            return redirect('vagas:encaminhamento', id=candidato.id, user_id=0)

    context = {
        'id': id,
        'form': form,
        'pessoa': pessoa
    }
    return render(request, 'vagas/candidatarse.html', context)


@login_required
@staff_required
def candidatosporvaga(request, id, mes, ano):
    candidatos = Candidato.objects.filter(vaga=id).order_by('dt_inclusao')

    if mes and ano:
        date = datetime(int(ano), int(mes), 1)

        if date.month == 12:
            _, last_day = calendar.monthrange(date.year + 1, 1)
            end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
        else:
            _, last_day = calendar.monthrange(date.year, date.month + 1)
            end_date = date + timedelta(days=last_day)

        candidatos = candidatos.filter(dt_inclusao__range=(date, end_date))


    paginator = Paginator(candidatos, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_obj.page_range = paginator.page_range

    context = {
        'candidatos': page_obj,
        'id': id,
        'mes': mes,
        'ano': ano
    }

    return render(request, 'vagas/vagas_com_candidatos listar.html', context)

def infoempresa(request):
    from django.db.models import Count, Q
    
    # Buscar empresas com contadores de vagas ativas e formulários ativos
    empresas = Empresa.objects.annotate(
        vagas_ativas_count=Count(
            'vaga_emprego', 
            filter=Q(vaga_emprego__ativo=True),
            distinct=True
        ),
        total_vagas_count=Count('vaga_emprego', distinct=True)
    ).order_by('nome')
    
    # Para cada empresa, calcular formulários manualmente devido ao relacionamento por CNPJ
    for empresa in empresas:
        formularios_da_empresa = RequisicaoVaga.objects.filter(cnpj_da_empresa=empresa.cnpj)
        empresa.formularios_ativos_count = formularios_da_empresa.filter(status_requisicao='PE').count()
        empresa.total_formularios_count = formularios_da_empresa.count()
    
    context = {
        'empresas': empresas
    }
    return render(request, 'vagas/infoempresa.html', context)

@login_required
@staff_required
def empresas_responsaveis(request):
    """View para listar empresas e seus respectivos responsáveis."""
    empresas = Empresa.objects.filter(responsaveis__isnull=False).distinct().prefetch_related('responsaveis').order_by('nome')
    
    # Adicionar informações adicionais para cada empresa
    for empresa in empresas:
        empresa.vagas_ativas_count = empresa.get_active_vagas_count()
        empresa.total_vagas_count = empresa.get_total_vagas_count()
        empresa.formularios_ativos_count = RequisicaoVaga.objects.filter(
            cnpj_da_empresa=empresa.cnpj, 
            status_requisicao__in=['AG', 'PE']
        ).count()
        empresa.total_formularios_count = RequisicaoVaga.objects.filter(
            cnpj_da_empresa=empresa.cnpj
        ).count()
    
    context = {
        'empresas': empresas,
    }
    
    return render(request, 'vagas/empresas_responsaveis.html', context)

@login_required
def empresa_profile(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    # Buscar todas as vagas da empresa
    vagas = Vaga_Emprego.objects.filter(empresa=empresa).order_by('-dt_inclusao')
    
    # Buscar todos os formulários da empresa pelo CNPJ
    formularios = RequisicaoVaga.objects.filter(cnpj_da_empresa=empresa.cnpj).order_by('-dt_inclusao')
    
    # Calcular estatísticas
    total_vagas = vagas.count()
    vagas_ativas = vagas.filter(ativo=True).count()
    
    # Candidatos únicos por CPF
    candidatos_unicos = Candidato.objects.filter(
        vaga__empresa=empresa
    ).values('cpf').distinct().count()
    
    # Total de candidatos (incluindo duplicatas)
    total_candidatos = Candidato.objects.filter(vaga__empresa=empresa).count()
    
    # Buscar responsáveis da empresa
    responsaveis = ResponsavelEmpresa.objects.filter(empresa=empresa).order_by('nome')
    responsaveis_ativos = responsaveis.filter(ativo=True).count()
    
    context = {
        'empresa': empresa,
        'vagas': vagas,
        'formularios': formularios,
        'total_vagas': total_vagas,
        'vagas_ativas': vagas_ativas,
        'candidatos_unicos': candidatos_unicos,
        'total_candidatos': total_candidatos,
        'total_formularios': formularios.count(),
        'formularios_aprovados': formularios.filter(status_requisicao='AP').count(),
        'responsaveis': responsaveis,
        'responsaveis_ativos': responsaveis_ativos,
    }
    
    return render(request, 'vagas/empresa_profile.html', context)

def infoempresa_download(request, id):
    empresa = get_object_or_404(Empresa, id=id)

    # Obtém todos os candidatos encaminhados para a empresa específica
    candidatos = Candidato.objects.filter(vaga__empresa=empresa)

    # Cria um novo workbook e uma planilha
    wb = Workbook()
    ws = wb.active

    # Configuração do cabeçalho do arquivo Excel
    ws.append(["Informações da Empresa: " + empresa.nome + " - " + empresa.cnpj +" Data emissão: " + str(date.today())])
    header = ["Nome", "CPF", "Data de Nascimento", "Sexo", "E-mail", "Celular", "Bairro", "Escolaridade", "Online", "Data de Inclusão"]

    # Adiciona o cabeçalho à planilha
    ws.append(header)

    # Adiciona os dados dos candidatos à planilha
     # Mantém o controle dos CPFs já adicionados
    cpf_set = set()

    # Adiciona os dados dos candidatos à planilha, evitando CPFs duplicados
    for candidato in candidatos:
        if candidato.cpf not in cpf_set:
            data_row = [candidato.nome, candidato.cpf, candidato.data_nascimento, candidato.get_sexo_display(), candidato.email, candidato.celular, candidato.bairro, candidato.escolaridade.nome, candidato.candidato_online, str(candidato.dt_inclusao)]
            ws.append(data_row)
            cpf_set.add(candidato.cpf)

    # Ajusta o alinhamento do texto na planilha
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.alignment = Alignment(horizontal='left')


    # Cria a resposta HTTP com o conteúdo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=Candidatos_{empresa.nome}.xlsx'

    # Salva o workbook na resposta HTTP
    wb.save(response)

    return response

@login_required
@staff_required
def pesquisar_candidatos(request):
    context = {}
    return render(request, 'vagas/pesquisar_candidatos.html', context)

from django.db.models import Min
@login_required
def get_candidatos(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))
        cpf = ''
        nome = ''
        try:
            cpf = data['cpf']
        except:
            nome = data['nome']        
        if cpf:
            try:
                candidatos = (
                    Candidato.objects.filter(cpf=cpf)
                    .values('cpf')  # agrupa pelo CPF
                    .annotate(id=Min('id'))  # pega o menor id por cpf (ou pode ser outro campo)
                )
                candidatos = Candidato.objects.filter(id__in=[c['id'] for c in candidatos])
            except Exception as E:
                candidatos = None

        elif nome:
            try:
                candidatos = (
                    Candidato.objects.filter(nome__icontains=nome)
                    .values('cpf')  # agrupa por CPF
                    .annotate(id=Min('id'))
                    .order_by('cpf')
                )
                candidatos = Candidato.objects.filter(id__in=[c['id'] for c in candidatos]).order_by('nome')
            except Exception as E:
                candidatos = None

        # if cpf:
        #     try:
        #         # empresas=Empresa.objects.filter(nome__startswith=request.GET.get('nome')).order_by('nome')
        #         candidatos = Candidato.objects.filter(cpf=cpf).distinct()
        #     except Exception as E:
        #         candidatos = None
        # elif nome:
        #     try:
        #         # empresas=Empresa.objects.filter(nome__startswith=request.GET.get('nome')).order_by('nome')
        #         candidatos = Candidato.objects.filter(
        #             nome__icontains=nome).order_by('nome').distinct('cpf')
        #     except Exception as E:
        #         candidatos = None

        else:
            print('dados informados não são os esperados')
            candidatos = None

        context = {
            'candidatos': candidatos,
        }

    return render(request, 'vagas/pesquisar_candidatos_result.html', context)


@login_required
@staff_required
def visualizar_candidato(request, id):
    candidato = Candidato.objects.get(id=id)
    context = {
        'candidato': candidato,
        'form': Form_Candidato(instance=candidato)
    }
    return render(request, 'vagas/pesquisar_visualizar_candidato.html', context)


@login_required
@staff_required
def vagascomcandidatos(request):    
    buscar = False
    context = {}

    if request.method == 'POST':

        month=request.POST['mes']
        year=request.POST['ano']

        buscar = True
        date = datetime(int(year), int(month), 1)

        if date.month == 12:
            _, last_day = calendar.monthrange(date.year + 1, 1)
            end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
        else:
            _, last_day = calendar.monthrange(date.year, date.month + 1)
            end_date = date + timedelta(days=last_day)

        candidatos_interval = Candidato.objects.filter(dt_inclusao__range=(date, end_date))

        vagas_com_candidatos = []

        vagas = Vaga_Emprego.objects.all()
        for vaga in vagas:
            candidatos = candidatos_interval.filter(vaga=vaga.id).count()
            if candidatos > 0:
                vagas_com_candidatos.append({'informacao': vaga, 'total': candidatos})

        paginator = Paginator(vagas_com_candidatos, 100)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        

        queryOnline=f'''
        SELECT DISTINCT id, cpf
        FROM vagas_candidato 
        WHERE MONTH(dt_inclusao)='{month}' 
        AND YEAR(dt_inclusao)='{year}' AND candidato_online=1;'''

        queryBalcao=f'''
        SELECT DISTINCT id, cpf
        FROM vagas_candidato 
        WHERE MONTH(dt_inclusao)='{month}' 
        AND YEAR(dt_inclusao)='{year}' AND candidato_online=0;'''             
        
        context = {
            'vagas': page_obj,
            'balcao':len(list(Vaga_Emprego.objects.raw(queryBalcao))),
            'online': len(list(Vaga_Emprego.objects.raw(queryOnline))),
            'buscar': buscar,
            'ano': year,
            'mes': month
        }
   
    return render(request, 'vagas/vagas_com_candidatos.html', context)


@login_required
@staff_required
def candidatosporfuncionario(request):
    usuarios = User.objects.filter(groups__name='atendente')
    lista = []
    month = ''
    year = ''
    filtro_aplicado = False
    
    # Verificar se há ação de limpar filtros
    if request.GET.get('limpar_filtros'):
        if 'filtro_funcionario' in request.session:
            del request.session['filtro_funcionario']
        return redirect('vagas:candidatosporfuncionario')
    
    # Processar POST (aplicar filtro)
    if request.method == 'POST':
        month = request.POST['mes']
        year = request.POST['ano']
        
        # Salvar na sessão
        request.session['filtro_funcionario'] = {
            'mes': month,
            'ano': year
        }
        filtro_aplicado = True
        
        date = datetime(int(year), int(month), 1)

        if date.month == 12:
            _, last_day = calendar.monthrange(date.year + 1, 1)
            end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
        else:
            _, last_day = calendar.monthrange(date.year, date.month + 1)
            end_date = date + timedelta(days=last_day)

        candidatos_interval = Candidato.objects.filter(dt_inclusao__range=(date, end_date))
    
    # Verificar se há filtro salvo na sessão
    elif 'filtro_funcionario' in request.session:
        try:
            filtro_session = request.session['filtro_funcionario']
            month = filtro_session['mes']
            year = filtro_session['ano']
            filtro_aplicado = True
            
            date = datetime(int(year), int(month), 1)

            if date.month == 12:
                _, last_day = calendar.monthrange(date.year + 1, 1)
                end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
            else:
                _, last_day = calendar.monthrange(date.year, date.month + 1)
                end_date = date + timedelta(days=last_day)

            candidatos_interval = Candidato.objects.filter(dt_inclusao__range=(date, end_date))
        except (ValueError, KeyError):
            # Limpar filtro inválido da sessão
            del request.session['filtro_funcionario']
            candidatos_interval = Candidato.objects.all()
    else: 
        candidatos_interval = Candidato.objects.all()

    total_encaminhamentos = 0
    for i in usuarios:
        encaminhamentos = len(candidatos_interval.filter(funcionario_encaminhamento=i))
        total_encaminhamentos += encaminhamentos
    
    # Agora calcular percentuais e montar a lista
    lista = []
    for i in usuarios:
        encaminhamentos = len(candidatos_interval.filter(funcionario_encaminhamento=i))
        percentual = (encaminhamentos / total_encaminhamentos * 100) if total_encaminhamentos > 0 else 0
        # Garantir que o percentual não exceda 100%
        percentual = min(round(percentual, 1), 100.0)
        lista.append([i.first_name, encaminhamentos, i.id, percentual])
    
    # Calculate the average
    media_por_atendente = 0
    if len(usuarios) > 0:
        media_por_atendente = total_encaminhamentos / len(usuarios)
        
    context = {
        'lista': lista,
        'mes': month,
        'ano': year,
        'total_encaminhamentos': total_encaminhamentos,
        'media_por_atendente': media_por_atendente,
        'filtro_aplicado': filtro_aplicado,
        'periodo_descricao': f"{month}/{year}" if filtro_aplicado and month and year else ''
    }

    # Use the new admin template
    return render(request, 'vagas/admin_candidatos_por_funcionario.html', context)


@login_required
@staff_required
def funcionario_encaminhados(request, id):
    import calendar
    from datetime import datetime, timedelta
    
    funcionario = User.objects.get(id=id)
    candidatos = Candidato.objects.filter(funcionario_encaminhamento=id)
    
    # Aplicar filtro de período se fornecido na URL ou sessão
    filtro_aplicado = False
    periodo_descricao = ''
    
    # Verificar parâmetros da URL primeiro
    mes_param = request.GET.get('mes')
    ano_param = request.GET.get('ano')
    
    if mes_param and ano_param:
        try:
            date = datetime(int(ano_param), int(mes_param), 1)
            
            if date.month == 12:
                _, last_day = calendar.monthrange(date.year + 1, 1)
                end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
            else:
                _, last_day = calendar.monthrange(date.year, date.month + 1)
                end_date = date + timedelta(days=last_day)
            
            candidatos = candidatos.filter(dt_inclusao__range=(date, end_date))
            filtro_aplicado = True
            periodo_descricao = f"{mes_param}/{ano_param}"
        except ValueError:
            pass
    
    # Se não há parâmetros na URL, verificar sessão
    elif 'filtro_funcionario' in request.session:
        try:
            filtro_session = request.session['filtro_funcionario']
            mes = filtro_session['mes']
            ano = filtro_session['ano']
            
            date = datetime(int(ano), int(mes), 1)
            
            if date.month == 12:
                _, last_day = calendar.monthrange(date.year + 1, 1)
                end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
            else:
                _, last_day = calendar.monthrange(date.year, date.month + 1)
                end_date = date + timedelta(days=last_day)
            
            candidatos = candidatos.filter(dt_inclusao__range=(date, end_date))
            filtro_aplicado = True
            periodo_descricao = f"{mes}/{ano}"
        except (ValueError, KeyError):
            pass
    
    # Apply search and status filters if provided
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        candidatos = candidatos.filter(status=status_filter)
    
    if search_query:
        candidatos = candidatos.filter(
            Q(nome__icontains=search_query) |
            Q(vaga__cargo__nome__icontains=search_query) |
            Q(vaga__empresa__nome__icontains=search_query)
        )
    
    # Get all candidatos for statistics before pagination
    todos_candidatos = candidatos
    
    paginator = Paginator(candidatos, 250)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_obj.page_range = paginator.page_range

    context = {
        'object_list': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'todos_candidatos': todos_candidatos,
        'funcionario': funcionario.first_name,
        'funcionario_id': id,
        'filtro_aplicado': filtro_aplicado,
        'periodo_descricao': periodo_descricao
    }

    return render(request, 'vagas/admin_candidatos_por_funcionario_detalhe.html', context)


@login_required
def sair(request):
    if request.user.is_authenticated:
        logout(request)
        return redirect('vagas:home')
    else:
        return redirect('/accounts/login')


# @login_required
# @staff_required
# def painel_administrativo(request):
#     from django.db.models import Count, Sum, Avg, Q, F, Case, When, IntegerField
#     from datetime import datetime, timedelta
#     from dateutil.relativedelta import relativedelta
#     import calendar
    
#     # Processamento dos filtros de período
#     filtro_aplicado = False
#     data_inicio = None
#     data_fim = None
    
#     # Verificar se há ação de limpar filtros
#     if request.GET.get('limpar_filtros'):
#         if 'filtro_periodo' in request.session:
#             del request.session['filtro_periodo']
#         return redirect('vagas:painel_administrativo')
    
#     # Processar POST (aplicar filtro)
#     if request.method == 'POST':
#         data_inicio_str = request.POST.get('data_inicio')
#         data_fim_str = request.POST.get('data_fim')
        
#         if data_inicio_str and data_fim_str:
#             try:
#                 data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
#                 data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                
#                 # Salvar na sessão
#                 request.session['filtro_periodo'] = {
#                     'data_inicio': data_inicio_str,
#                     'data_fim': data_fim_str
#                 }
#                 filtro_aplicado = True
#             except ValueError:
#                 pass
    
#     # Verificar se há filtro salvo na sessão
#     elif 'filtro_periodo' in request.session:
#         try:
#             filtro_session = request.session['filtro_periodo']
#             data_inicio = datetime.strptime(filtro_session['data_inicio'], '%Y-%m-%d').date()
#             data_fim = datetime.strptime(filtro_session['data_fim'], '%Y-%m-%d').date()
#             filtro_aplicado = True
#         except (ValueError, KeyError):
#             # Limpar filtro inválido da sessão
#             del request.session['filtro_periodo']
    
#     # Aplicar filtros nas queries principais
#     vagas_query = Vaga_Emprego.objects.all()
#     candidatos_query = Candidato.objects.all()
#     formularios_query = RequisicaoVaga.objects.all()
    
#     if filtro_aplicado and data_inicio and data_fim:
#         vagas_query = vagas_query.filter(dt_inclusao__range=[data_inicio, data_fim])
#         candidatos_query = candidatos_query.filter(dt_inclusao__range=[data_inicio, data_fim])
#         formularios_query = formularios_query.filter(dt_inclusao__range=[data_inicio, data_fim])
    
#     # Estatísticas gerais (com filtro aplicado se houver)
#     total_vagas_ativas = vagas_query.filter(ativo=True).count()
#     total_posicoes_abertas = vagas_query.filter(ativo=True).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#     total_empresas_ativas = Empresa.objects.filter(vaga_emprego__in=vagas_query.filter(ativo=True)).distinct().count()
#     total_candidatos = candidatos_query.count()
#     candidatos_online = candidatos_query.filter(candidato_online=True).count()
#     candidatos_balcao = candidatos_query.filter(candidato_online=False).count()
    
#     # Estatísticas do mês atual (ajustadas para o filtro se aplicado)
#     hoje = datetime.now()
#     inicio_mes = datetime(hoje.year, hoje.month, 1)
#     if filtro_aplicado:
#         candidatos_mes = candidatos_query.count()
#         vagas_mes = vagas_query.count()
#     else:
#         candidatos_mes = Candidato.objects.filter(dt_inclusao__gte=inicio_mes).count()
#         vagas_mes = Vaga_Emprego.objects.filter(dt_inclusao__gte=inicio_mes).count()
    
#     # Data para últimos 31 dias
#     ultimos_31_dias = hoje - timedelta(days=31)
    
#     # === NOVAS MÉTRICAS AVANÇADAS ===
    
#     # 1. TEMPO MÉDIO DE APROVAÇÃO DE FORMULÁRIOS
#     formularios_aprovados = formularios_query.filter(
#         status_requisicao='AP'
#     ).exclude(dt_atualizacao__isnull=True)
    
#     tempo_medio_aprovacao = 0
#     if formularios_aprovados.exists():
#         total_tempo = sum([
#             (f.dt_atualizacao - f.dt_inclusao).total_seconds() / 3600  # em horas
#             for f in formularios_aprovados 
#             if f.dt_atualizacao and f.dt_inclusao
#         ])
#         tempo_medio_aprovacao = total_tempo / formularios_aprovados.count() if formularios_aprovados.count() > 0 else 0
    
#     # 2. FUNIL DE CONVERSÃO: Vagas → Candidatos
#     total_vagas_criadas = vagas_query.count()
#     total_candidatos_sistema = candidatos_query.count()
    
#     # Taxa de candidatos por vaga
#     taxa_candidatos_por_vaga = total_candidatos_sistema / total_vagas_criadas if total_vagas_criadas > 0 else 0
    
#     # === INDICADORES DE ENTRADA E SAÍDA DE VAGAS ===
    
#     # Calcular vagas que entraram (foram criadas) no período
#     if filtro_aplicado and data_inicio and data_fim:
#         vagas_ = Vaga_Emprego.objects.filter(ativo=True, dt_inclusao__range=[data_inicio, data_fim]).select_related('cargo', 'empresa').order_by('cargo__nome')
#         # Vagas criadas no período (número de registros Vaga_Emprego)
#         vagas_entraram_registros = Vaga_Emprego.objects.filter(
#             dt_inclusao__range=[data_inicio, data_fim]
#         ).count()
        
#         # Quantidade total de posições abertas no período
#         vagas_entraram_posicoes = Vaga_Emprego.objects.filter(
#             dt_inclusao__range=[data_inicio, data_fim]
#         ).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
        
#         # Vagas que saíram (foram desativadas) no período
#         # Para vagas com dt_desativacao, usar essa data
#         vagas_sairam_com_data = Vaga_Emprego.objects.filter(
#             dt_desativacao__range=[data_inicio, data_fim],
#             ativo=False
#         )
        
#         # Para vagas sem dt_desativacao mas que foram desativadas (ativo=False)
#         # e que foram atualizadas no período, considerar dt_atualizacao
#         vagas_sairam_sem_data = Vaga_Emprego.objects.filter(
#             ativo=False,
#             dt_desativacao__isnull=True,
#             dt_atualizacao__range=[data_inicio, data_fim]
#         ).exclude(dt_inclusao__range=[data_inicio, data_fim])  # Excluir vagas criadas e desativadas no mesmo período
        
#         # Contar registros que saíram
#         vagas_sairam_registros = vagas_sairam_com_data.count() + vagas_sairam_sem_data.count()
        
#         # Contar posições que saíram
#         posicoes_sairam_com_data = vagas_sairam_com_data.aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#         posicoes_sairam_sem_data = vagas_sairam_sem_data.aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#         vagas_sairam_posicoes = posicoes_sairam_com_data + posicoes_sairam_sem_data
        
#     else:
#         vagas_ = Vaga_Emprego.objects.filter(ativo=True).select_related('cargo', 'empresa').order_by('cargo__nome')
#         # Sem filtro, mostrar estatísticas do mês atual
#         inicio_mes_atual = datetime(hoje.year, hoje.month, 1)
#         fim_mes_atual = inicio_mes_atual + relativedelta(months=1)
        
#         # Vagas que entraram este mês
#         vagas_entraram_registros = Vaga_Emprego.objects.filter(
#             dt_inclusao__gte=inicio_mes_atual,
#             dt_inclusao__lt=fim_mes_atual
#         ).count()
        
#         vagas_entraram_posicoes = Vaga_Emprego.objects.filter(
#             dt_inclusao__gte=inicio_mes_atual,
#             dt_inclusao__lt=fim_mes_atual
#         ).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
        
#         # Vagas que saíram este mês
#         vagas_sairam_com_data_mes = Vaga_Emprego.objects.filter(
#             dt_desativacao__gte=inicio_mes_atual,
#             dt_desativacao__lt=fim_mes_atual,
#             ativo=False
#         )
        
#         vagas_sairam_sem_data_mes = Vaga_Emprego.objects.filter(
#             ativo=False,
#             dt_desativacao__isnull=True,
#             dt_atualizacao__gte=inicio_mes_atual,
#             dt_atualizacao__lt=fim_mes_atual
#         ).exclude(dt_inclusao__gte=inicio_mes_atual, dt_inclusao__lt=fim_mes_atual)
        
#         vagas_sairam_registros = vagas_sairam_com_data_mes.count() + vagas_sairam_sem_data_mes.count()
        
#         posicoes_sairam_com_data_mes = vagas_sairam_com_data_mes.aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#         posicoes_sairam_sem_data_mes = vagas_sairam_sem_data_mes.aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#         vagas_sairam_posicoes = posicoes_sairam_com_data_mes + posicoes_sairam_sem_data_mes
    
#     # Calcular saldo líquido (diferença entre entrada e saída)
#     saldo_vagas_registros = vagas_entraram_registros - vagas_sairam_registros
#     saldo_vagas_posicoes = vagas_entraram_posicoes - vagas_sairam_posicoes
    
#     # 4. ANÁLISES TEMPORAIS
    
#     # Sazonalidade de vagas por setor (últimos 12 meses)
#     doze_meses_atras = hoje - timedelta(days=365)
#     vagas_por_cargo_mes = []
    
#     top_cargos = Cargo.objects.annotate(
#         total_vagas=Count('vaga_emprego')
#     ).order_by('-total_vagas')[:5]
    
#     for cargo in top_cargos:
#         vagas_mes_cargo = []
#         for i in range(12):
#             mes_inicio = hoje.replace(day=1) - relativedelta(months=i)
#             mes_fim = mes_inicio + relativedelta(months=1)
#             total_mes = Vaga_Emprego.objects.filter(
#                 cargo=cargo,
#                 dt_inclusao__gte=mes_inicio,
#                 dt_inclusao__lt=mes_fim
#             ).count()
#             vagas_mes_cargo.append({
#                 'mes': mes_inicio.strftime('%m/%Y'),
#                 'total': total_mes
#             })
#         vagas_por_cargo_mes.append({
#             'cargo': cargo.nome,
#             'dados': list(reversed(vagas_mes_cargo))
#         })
    
#     # Picos de demanda por mês (candidatos)
#     picos_demanda_candidatos = []
#     for i in range(12):
#         mes_inicio = hoje.replace(day=1) - relativedelta(months=i)
#         mes_fim = mes_inicio + relativedelta(months=1)
#         total_candidatos_mes = Candidato.objects.filter(
#             dt_inclusao__gte=mes_inicio,
#             dt_inclusao__lt=mes_fim
#         ).count()
#         picos_demanda_candidatos.append({
#             'mes': mes_inicio.strftime('%m/%Y'),
#             'total': total_candidatos_mes
#         })
#     picos_demanda_candidatos.reverse()
    
#     # Ciclo de vida médio das vagas (tempo entre criação e desativação)
#     vagas_desativadas = Vaga_Emprego.objects.filter(
#         ativo=False,
#         dt_desativacao__isnull=False
#     )
    
#     ciclo_vida_medio = 0
#     if vagas_desativadas.exists():
#         total_dias = sum([
#             (v.dt_desativacao - v.dt_inclusao).days 
#             for v in vagas_desativadas
#             if v.dt_desativacao and v.dt_inclusao
#         ])
#         ciclo_vida_medio = total_dias / vagas_desativadas.count() if vagas_desativadas.count() > 0 else 0
    
#     # 5. MAPA DE CALOR GEOGRÁFICO (por bairros) - usando query filtrada
#     candidatos_por_bairro_qs = candidatos_query.exclude(
#         Q(bairro__isnull=True) | Q(bairro__exact='')
#     ).values('bairro').annotate(
#         total=Count('id')
#     ).order_by('-total')[:10]  # Limitado aos top 10 bairros

#     # Construir lista com percentual em relação ao total de candidatos
#     candidatos_por_bairro = []
#     for item in candidatos_por_bairro_qs:
#         pct = 0
#         try:
#             pct = round((item['total'] / total_candidatos) * 100, 1) if total_candidatos > 0 else 0
#         except Exception:
#             pct = 0
#         candidatos_por_bairro.append({
#             'bairro': item['bairro'],
#             'total': item['total'],
#             'percentual': pct,
#         })
    
#     # Bairros por vagas (empresas que mais oferecem vagas por bairro) - filtradas por período
#     if filtro_aplicado:
#         # Se há filtro, buscar empresas que tiveram vagas no período
#         empresas_periodo = Empresa.objects.filter(vaga_emprego__in=vagas_query).distinct()
#         bairros_por_vaga_qs = empresas_periodo.exclude(
#             Q(bairro__isnull=True) | Q(bairro__exact='')
#         ).values('bairro').annotate(
#             total_vagas=Sum('vaga_emprego__quantidadeVagas', filter=Q(vaga_emprego__in=vagas_query)),
#             total_empresas=Count('id', distinct=True)
#         ).filter(total_vagas__gt=0).order_by('-total_vagas')[:10]
#         total_vagas_sistema = vagas_query.aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#     else:
#         # Sem filtro, usar todas as vagas
#         bairros_por_vaga_qs = Empresa.objects.exclude(
#             Q(bairro__isnull=True) | Q(bairro__exact='')
#         ).values('bairro').annotate(
#             total_vagas=Sum('vaga_emprego__quantidadeVagas'),
#             total_empresas=Count('id', distinct=True)
#         ).filter(total_vagas__gt=0).order_by('-total_vagas')[:10]
#         total_vagas_sistema = Vaga_Emprego.objects.aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
    
#     bairros_por_vaga = []
#     for item in bairros_por_vaga_qs:
#         pct = 0
#         try:
#             pct = round((item['total_vagas'] / total_vagas_sistema) * 100, 1) if total_vagas_sistema > 0 else 0
#         except Exception:
#             pct = 0
#         bairros_por_vaga.append({
#             'bairro': item['bairro'],
#             'total_vagas': item['total_vagas'] or 0,
#             'total_empresas': item['total_empresas'],
#             'percentual': pct,
#         })
    
#     # Estatísticas dos últimos 31 dias
#     vagas_ativas_31_dias = Vaga_Emprego.objects.filter(ativo=True, dt_inclusao__gte=ultimos_31_dias).count()
#     posicoes_abertas_31_dias = Vaga_Emprego.objects.filter(ativo=True, dt_inclusao__gte=ultimos_31_dias).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
#     empresas_ativas_31_dias = Empresa.objects.filter(vaga_emprego__ativo=True, vaga_emprego__dt_inclusao__gte=ultimos_31_dias).distinct().count()
#     candidatos_31_dias = Candidato.objects.filter(dt_inclusao__gte=ultimos_31_dias).count()
    
#     # Top 15 cargos mais procurados (com filtro aplicado se houver)
#     top_cargos_total = candidatos_query.values('vaga__cargo__nome').annotate(
#         total=Count('id')
#     ).order_by('-total')[:15]
    
#     # Top 10 empresas com mais vagas (com filtro aplicado se houver)
#     top_empresas_total = vagas_query.filter(ativo=True).values('empresa__nome').annotate(
#         total=Sum('quantidadeVagas')
#     ).order_by('-total')[:10]
    
#     # Top 10 empresas com mais vagas (últimos 31 dias)
#     top_empresas_31_dias = Vaga_Emprego.objects.filter(
#         ativo=True, 
#         dt_inclusao__gte=ultimos_31_dias
#     ).values('empresa__nome').annotate(
#         total=Sum('quantidadeVagas')
#     ).order_by('-total')[:10]
    
#     # Candidatos online vs balcão (total)
#     candidatos_online_total = candidatos_online
#     candidatos_balcao_total = candidatos_balcao
    
#     # Candidatos online vs balcão (últimos 31 dias)
#     candidatos_online_31_dias = Candidato.objects.filter(
#         candidato_online=True, 
#         dt_inclusao__gte=ultimos_31_dias
#     ).count()
#     candidatos_balcao_31_dias = Candidato.objects.filter(
#         candidato_online=False, 
#         dt_inclusao__gte=ultimos_31_dias
#     ).count()
    
#     # Distribuição por escolaridade (com filtro aplicado se houver)
#     escolaridade_stats = candidatos_query.values('escolaridade__nome').annotate(
#         total=Count('id')
#     ).order_by('-total')
    
#     # Candidatos por mês (últimos 13 meses)
#     candidatos_por_mes = []
#     data_atual = datetime.now()
    
#     for i in range(13):
#         # Calcula o mês de referência
#         if data_atual.month - i > 0:
#             mes = data_atual.month - i
#             ano = data_atual.year
#         else:
#             mes = 12 + (data_atual.month - i)
#             ano = data_atual.year - 1
            
#         data_inicio_mes = datetime(ano, mes, 1)
        
#         # Calcula o fim do mês
#         if mes == 12:
#             data_fim_mes = datetime(ano + 1, 1, 1)
#         else:
#             data_fim_mes = datetime(ano, mes + 1, 1)
        
#         count = Candidato.objects.filter(dt_inclusao__gte=data_inicio_mes, dt_inclusao__lt=data_fim_mes).count()
#         candidatos_por_mes.append({
#             'mes': data_inicio_mes.strftime('%m/%Y'),
#             'total': count
#         })
    
#     candidatos_por_mes.reverse()
    
    
    
    
#     # Criar dicionário para agrupar vagas por cargo
#     vagas_por_cargo_ = {}
#     for vaga in vagas_:
#         cargo_nome = vaga.cargo.nome
#         if cargo_nome not in vagas_por_cargo_:
#             vagas_por_cargo_[cargo_nome] = []
#         vagas_por_cargo_[cargo_nome].append(vaga)

#     vagas_em_destaque = vagas_.filter(destaque=True)

#     # Contar total de vagas
#     total_vagas_ = sum(vaga.quantidadeVagas for vaga in vagas_)
    
    
#     context = {
#         'qnt_cargos': len(vagas_por_cargo_),
#         'qnt_vagas': total_vagas_,
#         'total_vagas_ativas': total_vagas_ativas,
#         'total_posicoes_abertas': total_posicoes_abertas,
#         'total_empresas_ativas': total_empresas_ativas,
#         'total_candidatos': total_candidatos,
#         'candidatos_online': candidatos_online,
#         'candidatos_balcao': candidatos_balcao,
#         'candidatos_mes': candidatos_mes,
#         'vagas_mes': vagas_mes,
        
#         # Informações do filtro
#         'filtro_aplicado': filtro_aplicado,
#         'data_inicio': data_inicio.strftime('%Y-%m-%d') if data_inicio else '',
#         'data_fim': data_fim.strftime('%Y-%m-%d') if data_fim else '',
#         'periodo_descricao': f"{data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}" if filtro_aplicado and data_inicio and data_fim else '',
        
#         # Dados dos últimos 31 dias
#         'vagas_ativas_31_dias': vagas_ativas_31_dias,
#         'posicoes_abertas_31_dias': posicoes_abertas_31_dias,
#         'empresas_ativas_31_dias': empresas_ativas_31_dias,
#         'candidatos_31_dias': candidatos_31_dias,
        
#         # Dados para gráficos comparativos
#         'top_cargos_total': top_cargos_total,
#         'top_empresas_total': top_empresas_total,
#         'top_empresas_31_dias': top_empresas_31_dias,
#         'candidatos_online_total': candidatos_online_total,
#         'candidatos_balcao_total': candidatos_balcao_total,
#         'candidatos_online_31_dias': candidatos_online_31_dias,
#         'candidatos_balcao_31_dias': candidatos_balcao_31_dias,
        
#         'escolaridade_stats': escolaridade_stats,
#         'candidatos_por_mes': candidatos_por_mes,
        
#         # === NOVAS MÉTRICAS AVANÇADAS ===
        
#         # Métricas de aprovação e funil
#         'tempo_medio_aprovacao': round(tempo_medio_aprovacao, 1),
#         'taxa_candidatos_por_vaga': round(taxa_candidatos_por_vaga, 1),
        
#         # Indicadores de entrada e saída de vagas
#         'vagas_entraram_registros': vagas_entraram_registros,
#         'vagas_entraram_posicoes': vagas_entraram_posicoes,
#         'vagas_sairam_registros': vagas_sairam_registros,
#         'vagas_sairam_posicoes': vagas_sairam_posicoes,
#         'saldo_vagas_registros': saldo_vagas_registros,
#         'saldo_vagas_posicoes': saldo_vagas_posicoes,
        
#         # Análises temporais
#         'vagas_por_cargo_mes': vagas_por_cargo_mes,
#         'picos_demanda_candidatos': picos_demanda_candidatos,
#         'ciclo_vida_medio': round(ciclo_vida_medio, 1),
        
#         # Mapa de calor geográfico
#         'candidatos_por_bairro': candidatos_por_bairro,
#         'bairros_por_vaga': bairros_por_vaga,
#         'total_vagas_sistema': total_vagas_sistema,
        
#         # Estatísticas de formulários (usando queries filtradas)
#         'total_formularios': formularios_query.count(),
#         'formularios_aprovados': formularios_query.filter(status_requisicao='AP').count(),
#         'formularios_pendentes': formularios_query.filter(status_requisicao__in=['AG', 'PE']).count(),
#         'formularios_rejeitados': formularios_query.filter(status_requisicao='RE').count(),
#     }
    
#     return render(request, 'vagas/painel_administrativo.html', context)

# vagas/views.py

from vagas.models import Vaga_Emprego, Candidato, RequisicaoVaga
from vagas.functions.filters import processar_filtro_periodo
from vagas.functions.stats_general import get_estatisticas_gerais
from vagas.functions.stats_advanced import calcular_tempo_medio_aprovacao, calcular_funil_vagas
from vagas.functions.stats_temporal import gerar_series_candidatos_por_mes, gerar_series_candidatos_por_mes_com_filtro
from vagas.functions.stats_geographic import candidatos_por_bairro, bairros_por_vaga, top_cargos_por_candidatos, top_empresas_por_vagas

@login_required
@staff_required
def painel_administrativo(request):
    # 1️⃣ Filtros
    data_inicio, data_fim, filtro_aplicado, redir = processar_filtro_periodo(request)
    if redir:
        return redirect('vagas:painel_administrativo')

    # 2️⃣ Queries filtradas
    vagas_query = Vaga_Emprego.objects.all()
    candidatos_query = Candidato.objects.all()
    formularios_query = RequisicaoVaga.objects.all()
    if filtro_aplicado:
        vagas_query = vagas_query.filter(dt_inclusao__range=[data_inicio, data_fim])
        candidatos_query = candidatos_query.filter(dt_inclusao__range=[data_inicio, data_fim])
        formularios_query = formularios_query.filter(dt_inclusao__range=[data_inicio, data_fim])

    # 3️⃣ Estatísticas principais
    stats_gerais = get_estatisticas_gerais(vagas_query, candidatos_query)

    # 4️⃣ Métricas avançadas
    tempo_medio_aprovacao = calcular_tempo_medio_aprovacao(formularios_query)
    funil = calcular_funil_vagas(vagas_query, candidatos_query)

    # 5️⃣ Geográficas e temporais
    top_cargos = top_cargos_por_candidatos(candidatos_query)
    top_empresas = top_empresas_por_vagas(vagas_query)
    
    geo_candidatos = candidatos_por_bairro(candidatos_query, stats_gerais['total_candidatos'])
    geo_vagas = bairros_por_vaga(vagas_query, filtro_aplicado)
    series_candidatos = gerar_series_candidatos_por_mes(13)
    series_candidatos_filtrado = gerar_series_candidatos_por_mes_com_filtro(candidatos_query, data_inicio, data_fim)

    
    # 6️⃣ Contexto
    context = {
        'stats_gerais': stats_gerais,
        'stats_advanced': funil,
        'tempo_medio_aprovacao': round(tempo_medio_aprovacao, 1),
        'filtro_aplicado': filtro_aplicado,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'candidatos_por_bairro': geo_candidatos,
        'bairros_por_vaga': geo_vagas,
        'candidatos_por_mes': series_candidatos,
        'top_cargos_total': top_cargos,
        'top_empresas': top_empresas,
        'picos_demanda_candidatos': series_candidatos_filtrado
    }

    return render(request, 'vagas/painel_administrativo.html', context)



@login_required
@staff_required
def painel_administrativo_excluir_cpf(request):
    return render(request, 'vagas/painel_administrativo_excluir_cpf.html')


@login_required
@staff_required
def excluir_cpf(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))
        if data['step'] == 0:
            cpf = validate_CPF(data['cpf'])
            potencialmente_excluidos = Candidato.objects.filter(
                cpf=cpf).count()

            return JsonResponse({'qnt_excluidos': potencialmente_excluidos, 'cpf': cpf, 'step': 1})

        elif data['step'] == 1:
            cpf = validate_CPF(data['cpf'])
            excluidos = Candidato.objects.filter(cpf=cpf).delete()
            return JsonResponse({'qnt_excluidos': excluidos[0], 'cpf': cpf, 'step': 1})


@login_required
@staff_required
def indicadores(request):
    timezone.activate(settings.TIME_ZONE)
    
    month = ''
    year = ''
    
    # Define default date range
    if request.method == 'POST':
        month = request.POST['mes']
        year = request.POST['ano']
        
        date_start = datetime(int(year), int(month), 1)
        
        if date_start.month == 12:
            _, last_day = calendar.monthrange(date_start.year + 1, 1)
            date_end = datetime(date_start.year + 1, 1, 1) + timedelta(days=last_day - 1)
        else:
            _, last_day = calendar.monthrange(date_start.year, date_start.month + 1)
            date_end = date_start + timedelta(days=last_day)
            
        start_date = date_start.date()
        end_date = date_end.date()
    else:
        start_date = date(2022, 9, 1)
        end_date = date.today()

    top_x = 11

    # -------------------- #

    vagas_emprego_faixa = Vaga_Emprego.objects.filter(dt_inclusao__gte = start_date, dt_inclusao__lt = end_date)
    cargos = Cargo.objects.all()
    escolaridades = Escolaridade.objects.all()
    empresas = Empresa.objects.all()

    # -------------------- #

    cargos_ofertados = []
    escolaridades_quantidades = []
    vagas_por_empresa = []
    candidatos_por_mes = []
    vagas_cadastradas_por_mes = []
    relacao_online_balcao = []

    # -------------------- #

    for cargo in cargos:
        total = vagas_emprego_faixa.filter(cargo=cargo).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum']
        if total == None:
            total = 0

        cargos_ofertados.append({'nome': cargo.nome, 'total': total})
    
    cargos_ofertados = sorted(cargos_ofertados, key=lambda x: x['total'], reverse=True)

    # ------------------------- #

    for escolaridade in escolaridades:
        total = Candidato.objects.filter(dt_inclusao__gte = start_date, dt_inclusao__lt = end_date, escolaridade=escolaridade).values('email').distinct().count()
        if total == None:
            total = 0

        escolaridades_quantidades.append({'nome': escolaridade.nome, 'total': total})

    # --------------------------- #
    
    delta = relativedelta(months=1)

    while start_date <= end_date:
        next_month = start_date + delta
        total = Candidato.objects.filter(dt_inclusao__gte = start_date, dt_inclusao__lt = next_month).values('email').distinct().count()
        if total == None:
            total = 0

        candidatos_por_mes.append({'nome': start_date, 'total': total})
        start_date += delta

    # ----------------------------- #

    start_date = date(2022, 9, 1)

    while start_date <= end_date:
        next_month = start_date + delta
        total = vagas_emprego_faixa.filter(dt_inclusao__gte = start_date, dt_inclusao__lt = next_month).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum']
        if total == None:
            total = 0

        vagas_cadastradas_por_mes.append({'nome': start_date, 'total': total})
        start_date += delta

    # ----------------------------- #

    for empresa in empresas:
        total = vagas_emprego_faixa.filter(empresa=empresa).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum']

        if total == None:
            total = 0

        vagas_por_empresa.append({'nome': empresa.nome, 'total': total})

    vagas_por_empresa = sorted(vagas_por_empresa, key=lambda x: x['total'], reverse=True)

    # ----------------------------- #

    start_date = date(2022, 9, 1)

    while start_date <= end_date:
        next_month = start_date + delta
        candidatos = Candidato.objects.filter(dt_inclusao__gte = start_date, dt_inclusao__lt = next_month).values('email').distinct()
        
        candidatos_online = candidatos.filter(candidato_online = True).count()
        candidatos_balcao = candidatos.filter(candidato_online = False).count()

        if total == None:
            total = 0

        relacao_online_balcao.append({'nome': start_date, 'online': candidatos_online, 'balcao': candidatos_balcao})
        start_date += delta

        
    # Calculate online vs balcao counts for the pie chart
    candidatos_periodo = Candidato.objects.filter(dt_inclusao__gte=start_date, dt_inclusao__lt=end_date)
    online = candidatos_periodo.filter(candidato_online=True).count()
    balcao = candidatos_periodo.filter(candidato_online=False).count()
    
    context = {
        'top_x': top_x,
        'top_cargos_ofertados': cargos_ofertados[:top_x],
        'escolaridades': escolaridades_quantidades,
        'candidatos_por_mes': candidatos_por_mes,
        'vagas_por_empresa': vagas_por_empresa[:top_x],
        'vagas_cadastradas_por_mes': vagas_cadastradas_por_mes,
        'relacao_online_balcao': relacao_online_balcao,
        'mes': month,
        'ano': year,
        'online': online,
        'balcao': balcao,
        'periodo_inicio': start_date.strftime('%d/%m/%Y'),
        'periodo_fim': end_date.strftime('%d/%m/%Y')
    }

    return render(request, 'vagas/indicadores_novo.html', context)

@login_required
@staff_required
def emails(request):

    context = {
        'buscar': False
    }

    if request.method == 'POST':

        month=request.POST['mes']
        year=request.POST['ano']

        date = datetime(int(year), int(month), 1)

        if date.month == 12:
            _, last_day = calendar.monthrange(date.year + 1, 1)
            end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
        else:
            _, last_day = calendar.monthrange(date.year, date.month + 1)
            end_date = date + timedelta(days=last_day)

        candidatos = Candidato.objects.filter(dt_inclusao__range=(date, end_date), email__isnull = False).exclude(email__exact='').values('email', 'nome').distinct()

        context = {
            'data': date,
            'mes': month,
            'ano': year,
            'candidatos': candidatos,
            'buscar': True,
        }

    return render(request, 'vagas/emails.html', context) 

@login_required
@staff_required
def download_emails(request, month, year):

    date = datetime(int(year), int(month), 1)

    if date.month == 12:
        _, last_day = calendar.monthrange(date.year + 1, 1)
        end_date = datetime(date.year + 1, 1, 1) + timedelta(days=last_day - 1)
    else:
        _, last_day = calendar.monthrange(date.year, date.month + 1)
        end_date = date + timedelta(days=last_day)

    candidatos = Candidato.objects.filter(dt_inclusao__range=(date, end_date), email__isnull = False).exclude(email__exact='').values('nome','email').distinct()

    context = {
        'listas': candidatos,
    }

    return render(request, 'vagas/email_csv.html', context) 

# Função temporária
def manutencao(request):
    return render(request, 'vagas/manutencao.html')

def meus_encaminhamentos(request):    
    try:
        pessoa = Pessoa.objects.get(user=request.user)
        candidato_encaminhamentos = Candidato.objects.filter(cpf=pessoa.cpf, vaga__ativo=True)
    except:
        candidato_encaminhamentos = None
        
    context = {
       'encaminhamentos': candidato_encaminhamentos
    }
    return render(request, 'vagas/meus_encaminhamentos.html', context)

def totem_v1(request):
    """
    View otimizada para totem com navegação por teclado (setas e enter)
    e movimentos do mouse (wheel scroll)
    """
    vagas = Vaga_Emprego.objects.filter(ativo=True).select_related('cargo', 'empresa').order_by('cargo__nome')
    
    # Criar dicionário para agrupar vagas por cargo
    vagas_por_cargo = {}
    for vaga in vagas:
        cargo_nome = vaga.cargo.nome
        if cargo_nome not in vagas_por_cargo:
            vagas_por_cargo[cargo_nome] = []
        vagas_por_cargo[cargo_nome].append(vaga)

    vagas_em_destaque = vagas.filter(destaque=True)

    # Contar total de vagas
    total_vagas = sum(vaga.quantidadeVagas for vaga in vagas)
    
    context = {
        'vagas': vagas,
        'vagas_por_cargo': vagas_por_cargo,  
        'vagas_destaque': vagas_em_destaque,
        'destaque': bool(vagas_em_destaque),
        'bairros': Empresa.objects.order_by('bairro').values_list('bairro', flat=True).distinct(),
        'escolaridades': Escolaridade.objects.all().values(),        
        'qnt_cargos': len(vagas_por_cargo),
        'qnt_vagas': total_vagas,        
        'eventos': Slide.objects.all(),
    }
    return render(request, 'vagas/totem_v1.html', context)

def totem_candidatarse(request, id):
    """
    View de candidatura específica para o totem
    """
    vaga = Vaga_Emprego.objects.get(id=id)
    
    if request.method == 'POST':
        form = Form_Candidato(request.POST)
        if form.is_valid():
            try:
                cpf = validate_CPF(request.POST['cpf'])
                candidato = Candidato.objects.get(cpf=cpf, vaga_id=id)
                form = Form_Candidato(request.POST, instance=candidato)
            except Exception as e:
                print(e)
                pass

            candidato = form.save()
            candidato.candidato_online = False
            candidato.save()
            # Redirect para página de sucesso do totem
            return redirect('vagas:totem_candidatura_sucesso', id=candidato.id)
        else:
            # Se há erros no formulário, renderizar novamente com erros
            context = {
                'vaga': vaga,
                'form': form,
                'errors': form.errors
            }
            return render(request, 'vagas/totem_candidatarse.html', context)
    else:
        form = Form_Candidato(initial={'vaga': id, 'candidato_online': True})
    
    context = {
        'vaga': vaga,
        'form': form
    }
    return render(request, 'vagas/totem_candidatarse.html', context)


def totem_candidatura_sucesso(request, id):
    """
    View de sucesso da candidatura para o totem
    """
    candidato = Candidato.objects.get(id=id)
    vaga = candidato.vaga
    
    context = {
        'candidato': candidato,
        'vaga': vaga
    }
    return render(request, 'vagas/totem_candidatura_sucesso.html', context)


# ===== VIEWS PARA ADMINISTRAÇÃO DE FORMULÁRIOS =====

@login_required
def admin_vagas_list(request):
    """Lista todas as vagas com opção de filtrar ativas/inativas"""
    
    # Determinar se deve mostrar ativas ou inativas
    mostrar_inativas = request.GET.get('inativas', 'false').lower() == 'true'
    
    if mostrar_inativas:
        vagas = Vaga_Emprego.objects.filter(ativo=False).select_related('empresa', 'cargo').prefetch_related('solicitacoes_desativacao').order_by('-dt_inclusao')
        page_title = "Vagas Inativas"
    else:
        vagas = Vaga_Emprego.objects.filter(ativo=True).select_related('empresa', 'cargo').prefetch_related('solicitacoes_desativacao').order_by('-dt_inclusao')
        page_title = "Vagas Ativas"
    
    # Adicionar contagem de candidatos e calcular totais
    total_candidatos = 0
    total_posicoes = 0
    
    for vaga in vagas:
        vaga.total_candidatos = Candidato.objects.filter(vaga=vaga).count()
        total_candidatos += vaga.total_candidatos
        total_posicoes += vaga.quantidadeVagas
    
    context = {
        'vagas': vagas,
        'mostrar_inativas': mostrar_inativas,
        'page_title': page_title,
        'total_ativas': Vaga_Emprego.objects.filter(ativo=True).count(),
        'total_inativas': Vaga_Emprego.objects.filter(ativo=False).count(),
        'total_candidatos': total_candidatos,
        'total_posicoes': total_posicoes,
    }
    
    return render(request, 'vagas/admin_vagas_list.html', context)


@staff_required
def admin_criar_vaga(request):
    """Criar nova vaga no painel administrativo"""
    
    if request.method == 'POST':
        try:
            # Criar nova vaga
            vaga = Vaga_Emprego()
            
            # Buscar empresa pelo nome (autocomplete)
            empresa_nome = request.POST.get('empresa_id', '').strip()
            if empresa_nome:
                try:
                    empresa = Empresa.objects.get(nome=empresa_nome)
                    vaga.empresa = empresa
                except Empresa.DoesNotExist:
                    messages.error(request, f'Empresa "{empresa_nome}" não encontrada.')
                    raise ValueError('Empresa não encontrada')
            else:
                messages.error(request, 'Empresa é obrigatória.')
                raise ValueError('Empresa não informada')
            
            # Buscar cargo pelo nome (autocomplete)
            cargo_nome = request.POST.get('cargo_id', '').strip()
            if cargo_nome:
                try:
                    cargo = Cargo.objects.get(nome=cargo_nome)
                    vaga.cargo = cargo
                except Cargo.DoesNotExist:
                    messages.error(request, f'Cargo "{cargo_nome}" não encontrado.')
                    raise ValueError('Cargo não encontrado')
            else:
                messages.error(request, 'Cargo é obrigatório.')
                raise ValueError('Cargo não informado')
            
            # Campos obrigatórios
            vaga.escolaridade_id = request.POST.get('escolaridade')
            vaga.quantidadeVagas = request.POST.get('quantidadeVagas')
            vaga.experiencia = request.POST.get('experiencia')
            vaga.user = request.user
            
            # Campos opcionais
            vaga.email = request.POST.get('email', '')
            vaga.tipo_de_vaga = request.POST.get('tipo_de_vaga', 'NML')
            vaga.salario = request.POST.get('salario', '')
            vaga.carga_horaria = request.POST.get('carga_horaria', '')
            vaga.regime = request.POST.get('regime', '')
            vaga.observacao = request.POST.get('observacao', '')
            vaga.atribuicoes = request.POST.get('atribuicoes', '')
            vaga.destaque = request.POST.get('destaque') == 'on'
            
            vaga.save()
            
            messages.success(request, f'Vaga criada com sucesso! REF: #{vaga.id}')
            return redirect('vagas:admin_vagas_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar vaga: {str(e)}')
    
    # Buscar dados para os dropdowns
    empresas = Empresa.objects.filter(ocultar=False).order_by('nome')
    cargos = Cargo.objects.all().order_by('nome')
    escolaridades = Escolaridade.objects.all().order_by('nome')
    
    context = {
        'empresas': empresas,
        'cargos': cargos,
        'escolaridades': escolaridades,
    }
    
    return render(request, 'vagas/admin_criar_vaga.html', context)


@login_required
def admin_formularios_list(request):
    """Lista todos os formulários de requisição"""
    formularios = RequisicaoVaga.objects.all().order_by('-dt_inclusao')
    
    # Filtros
    status = request.GET.get('status')
    empresa = request.GET.get('empresa')
    
    if status:
        formularios = formularios.filter(status_requisicao=status)
    if empresa:
        formularios = formularios.filter(nome_da_empresa__icontains=empresa)
    
    context = {
        'formularios': formularios,
        'status_choices': RequisicaoVaga.STATUS_CHOICES,
        'filtro_status': status,
        'filtro_empresa': empresa,
    }
    return render(request, 'vagas/admin_formularios_list.html', context)


@login_required 
def admin_formularios_create(request):
    """Criar novo formulário de requisição"""
    
    # Buscar empresa pelo CNPJ se fornecido via GET
    empresa_selecionada = None
    cnpj_param = request.GET.get('empresa_cnpj')
    origem = request.GET.get('origem', '')  # 'empresa' ou vazio
    empresa_id = request.GET.get('empresa_id', '')
    
    if cnpj_param:
        try:
            empresa_selecionada = Empresa.objects.get(cnpj=cnpj_param)
        except Empresa.DoesNotExist:
            pass
    
    if request.method == 'POST':
        # Chave de acesso é obrigatória
        chave_acesso = request.POST.get('chave_de_acesso', '').strip()
        
        if not chave_acesso:
            messages.error(request, 'A chave de acesso é obrigatória!')
            context = {
                'empresa_selecionada': empresa_selecionada, 
                'origem': origem, 
                'empresa_id': empresa_id
            }
            return render(request, 'vagas/admin_formularios_create.html', context)
        
        # Dados opcionais da empresa
        nome_empresa = request.POST.get('nome_da_empresa', '').strip()
        cnpj_empresa = request.POST.get('cnpj_da_empresa', '').strip()
        email_empresa = request.POST.get('email_da_empresa', '').strip()
        endereco_empresa = request.POST.get('endereco_da_empresa', '').strip()
        telefone_empresa = request.POST.get('telefone_da_empresa', '').strip()
        whatsapp_empresa = request.POST.get('whatsapp_da_empresa', '').strip()
        
        # Criar nova requisição com dados iniciais
        requisicao = RequisicaoVaga.objects.create(
            # Dados do responsável (serão preenchidos no formulário público)
            nome_do_responsavel_pela_divulgacao_da_vaga='A definir',
            cpf_do_responsavel='00000000000',  # Será alterado no formulário público
            
            # Dados da empresa (opcionais na criação)
            nome_da_empresa=nome_empresa or 'A definir',
            cnpj_da_empresa=cnpj_empresa or '00000000000000',
            email_da_empresa=email_empresa or 'nao-informado@email.com',
            endereco_da_empresa=endereco_empresa,
            telefone_da_empresa=telefone_empresa,
            whatsapp_da_empresa=whatsapp_empresa,
            
            # Dados da vaga (padrões)
            quantidade_de_vagas=1,
            cargo_ofertado='A definir',
            escolaridade_id=1,  # Assumindo que existe escolaridade com ID 1
            
            # Chave de acesso obrigatória
            chave_de_acesso=chave_acesso
        )
        
        messages.success(request, f'Formulário criado com sucesso! Chave de acesso: {chave_acesso}')
        return redirect('vagas:admin_formularios_detail', id=requisicao.pk)
    
    context = {
        'empresa_selecionada': empresa_selecionada,
        'origem': origem,
        'empresa_id': empresa_id
    }
    return render(request, 'vagas/admin_formularios_create.html', context)


@login_required
def admin_formularios_detail(request, id):
    """Visualizar detalhes de um formulário"""
    try:
        formulario = RequisicaoVaga.objects.get(pk=id)
    except RequisicaoVaga.DoesNotExist:
        raise Http404("Formulário não encontrado")
    
    # Verificar se existe vaga vinculada usando o método get_vaga()
    vaga_vinculada = formulario.get_vaga()
    candidatos_da_vaga = []
    
    if vaga_vinculada:
        # Buscar candidatos e solicicitações de desativação com prefetch
        vaga_vinculada = Vaga_Emprego.objects.select_related('empresa', 'cargo').prefetch_related(
            'solicitacoes_desativacao__empresa_responsavel',
            'solicitacoes_desativacao__processado_por'
        ).get(pk=vaga_vinculada.pk)
        candidatos_da_vaga = Candidato.objects.filter(vaga=vaga_vinculada).order_by('-dt_inclusao')
    
    context = {
        'formulario': formulario,
        'vaga_vinculada': vaga_vinculada,
        'candidatos_da_vaga': candidatos_da_vaga,
        'public_url': request.build_absolute_uri(formulario.get_public_url()),
    }
    return render(request, 'vagas/admin_formularios_detail.html', context)


@login_required
def admin_formularios_update_status(request, id):
    """Atualizar status de um formulário"""
    if request.method == 'POST':
        try:
            formulario = RequisicaoVaga.objects.get(pk=id)
            novo_status = request.POST.get('status')
            observacao = request.POST.get('observacao', '').strip()
            
            if novo_status in [choice[0] for choice in RequisicaoVaga.STATUS_CHOICES]:
                # Capturar status anterior
                status_anterior = formulario.status_requisicao
                
                # Atualizar formulário
                formulario.status_requisicao = novo_status
                if observacao:
                    formulario.observacao_interna = observacao
                formulario.save()
                
                # Criar entrada no histórico
                from .models import HistoricoRequisicao
                HistoricoRequisicao.objects.create(
                    requisicao=formulario,
                    acao='ST',  # Mudança de Status
                    status_anterior=status_anterior,
                    status_novo=novo_status,
                    observacao=observacao,
                    usuario=request.user
                )
                
                messages.success(request, 'Status atualizado com sucesso!')
                
        except RequisicaoVaga.DoesNotExist:
            messages.error(request, 'Formulário não encontrado.')
    
    return redirect('vagas:admin_formularios_detail', id=id)


# ===== VIEW PÚBLICA PARA EMPRESAS =====

def formulario_autenticacao(request, hash_id):
    """Página de autenticação com hash e chave de acesso"""
    # Verificar se o formulário existe pelo hash
    try:
        requisicao = RequisicaoVaga.objects.get(hash_id=hash_id)
    except RequisicaoVaga.DoesNotExist:
        return render(request, 'vagas/formulario_nao_encontrado.html')
    
    if request.method == 'POST':
        chave_acesso = request.POST.get('chave_acesso', '').strip()
        
        if not chave_acesso:
            messages.error(request, 'Por favor, digite a chave de acesso.')
            return render(request, 'vagas/formulario_autenticacao.html', {'hash_id': hash_id, 'requisicao': requisicao})
        
        # Verificar se a chave de acesso confere
        if chave_acesso != requisicao.chave_de_acesso:
            messages.error(request, 'Chave de acesso incorreta. Verifique e tente novamente.')
            return render(request, 'vagas/formulario_autenticacao.html', {'hash_id': hash_id, 'requisicao': requisicao})
        
        # Gerar hash de autenticação para o cookie
        import hashlib
        import secrets
        timestamp = str(timezone.now().timestamp())
        auth_hash = hashlib.sha256(f"{chave_acesso}{timestamp}{secrets.token_hex(16)}".encode()).hexdigest()
        
        # Salvar o hash no objeto para verificação posterior
        requisicao.auth_hash_temp = auth_hash
        requisicao.save()
        
        # Redirecionar para o formulário com cookie
        if requisicao.status_requisicao == 'AG':
            response = redirect('vagas:formulario_publico', hash_id=hash_id)
        else:
            response = redirect('vagas:formulario_detalhes_externo', hash_id=hash_id)
        
        # Cookie seguro com o hash de autenticação
        response.set_cookie(
            'formulario_auth',
            auth_hash,
            max_age=3600,  # 1 hora
            secure=False,  # True em produção com HTTPS
            httponly=True,
            samesite='Lax'
        )
        
        return response
    
    context = {
        'hash_id': hash_id,
        'requisicao': requisicao,
    }
    return render(request, 'vagas/formulario_autenticacao.html', context)


def formulario_publico(request, hash_id):
    """Formulário público para empresas preencherem"""
    try:
        requisicao = RequisicaoVaga.objects.get(hash_id=hash_id)
    except RequisicaoVaga.DoesNotExist:
        return render(request, 'vagas/formulario_nao_encontrado.html')
    
    # Verificar autenticação via cookie
    auth_cookie = request.COOKIES.get('formulario_auth')
    if not auth_cookie or auth_cookie != requisicao.auth_hash_temp:
        messages.error(request, 'Acesso não autorizado. Faça a autenticação novamente.')
        return redirect('vagas:formulario_autenticacao', hash_id=hash_id)
    
    # Verificar se já foi preenchido
    if requisicao.status_requisicao in ['AP', 'RE']:
        return render(request, 'vagas/formulario_ja_processado.html', {'requisicao': requisicao})
    
    if request.method == 'POST':
        # Verificar novamente a autenticação no envio
        auth_cookie_post = request.COOKIES.get('formulario_auth')
        if not auth_cookie_post or auth_cookie_post != requisicao.auth_hash_temp:
            messages.error(request, 'Sessão expirada. Faça a autenticação novamente.')
            return redirect('vagas:formulario_autenticacao', hash_id=hash_id)
        
        # Atualizar todos os campos do formulário
        requisicao.nome_do_responsavel_pela_divulgacao_da_vaga = request.POST.get('nome_responsavel', '')
        requisicao.cpf_do_responsavel = request.POST.get('cpf_responsavel', '')
        requisicao.contato_do_responsavel = request.POST.get('contato_responsavel', '')
        
        # Empresa (incluindo nome e CNPJ que podem ser editados)
        requisicao.nome_da_empresa = request.POST.get('nome_empresa', '')
        requisicao.cnpj_da_empresa = request.POST.get('cnpj_empresa', '')
        requisicao.endereco_da_empresa = request.POST.get('endereco_empresa', '')
        requisicao.telefone_da_empresa = request.POST.get('telefone_empresa', '')
        requisicao.segmento_da_empresa = request.POST.get('segmento_empresa', '')
        requisicao.whatsapp_da_empresa = request.POST.get('whatsapp_empresa', '')
        
        # Vaga
        requisicao.quantidade_de_vagas = int(request.POST.get('quantidade_vagas', 1))
        requisicao.cargo_ofertado = request.POST.get('cargo_ofertado', '')
        requisicao.tipo_de_vaga = request.POST.get('tipo_vaga', 'NML')
        requisicao.regime = request.POST.get('regime', '')
        requisicao.faixa_salarial = request.POST.get('faixa_salarial', 'ACB')
        requisicao.valor_salario = request.POST.get('valor_salario', '')
        
        # Benefícios
        requisicao.vale_transporte = bool(request.POST.get('vale_transporte'))
        requisicao.vale_alimentacao = bool(request.POST.get('vale_alimentacao'))
        requisicao.outros_beneficios = request.POST.get('outros_beneficios', '')
        requisicao.carga_horaria = request.POST.get('carga_horaria', '40')
        requisicao.outra_carga_horaria = request.POST.get('outra_carga_horaria', '')
        
        # Requisitos
        escolaridade_id = request.POST.get('escolaridade')
        if escolaridade_id:
            requisicao.escolaridade_id = int(escolaridade_id)
        requisicao.experiencia = request.POST.get('experiencia', 'Não')
        requisicao.observacao = request.POST.get('observacao', '')
        
        # Formas de contato
        requisicao.enviar_curriculo_para_email = bool(request.POST.get('enviar_email'))
        requisicao.email_para_envio = request.POST.get('email_envio', '')
        requisicao.levar_curriculo_direto_ao_local = bool(request.POST.get('levar_curriculo'))
        requisicao.endereco_para_levar_curriculo = request.POST.get('endereco_curriculo', '')
        requisicao.via_telefone_ou_whatsapp = bool(request.POST.get('via_telefone'))
        requisicao.telefone_ou_whatsapp = request.POST.get('telefone_whatsapp', '')
        requisicao.outra_forma_de_contato = bool(request.POST.get('outra_forma'))
        requisicao.outra_forma_de_contato_descricao = request.POST.get('outra_forma_descricao', '')
        
        # Atualizar status para pendente mas manter o hash para visualização dos detalhes
        requisicao.status_requisicao = 'PE'
        requisicao.save()
        
        # Redirecionar para página de detalhes (mantendo o cookie ativo)
        messages.success(request, 'Formulário enviado com sucesso! Você pode visualizar os detalhes abaixo.')
        return redirect('vagas:formulario_detalhes_externo', hash_id=hash_id)
    
    # Buscar escolaridades para o formulário
    escolaridades = Escolaridade.objects.all()
    
    context = {
        'requisicao': requisicao,
        'escolaridades': escolaridades,
        'tipo_vaga_choices': RequisicaoVaga.TIPO_DE_VAGA_CHOICES,
        'regime_choices': RequisicaoVaga.REGIME_CHOICES,
        'faixa_salarial_choices': RequisicaoVaga.FAIXA_SALARIAL_CHOICES,
        'carga_horaria_choices': RequisicaoVaga.CARGA_HORARIA_CHOICES,
        'experiencia_choices': RequisicaoVaga.EXPERIENCIA_CHOICES,
    }
    return render(request, 'vagas/formulario_publico.html', context)


def formulario_detalhes_externo(request, hash_id):
    """Página de detalhes externa para a empresa visualizar o formulário preenchido"""
    try:
        requisicao = RequisicaoVaga.objects.get(hash_id=hash_id)
    except RequisicaoVaga.DoesNotExist:
        return render(request, 'vagas/formulario_nao_encontrado.html')
    
    # Verificar autenticação via cookie
    auth_cookie = request.COOKIES.get('formulario_auth')
    if not auth_cookie or auth_cookie != requisicao.auth_hash_temp:
        messages.error(request, 'Acesso não autorizado. Faça a autenticação novamente.')
        return redirect('vagas:formulario_autenticacao', hash_id=hash_id)
    
    # Verificar se o formulário foi preenchido
    if requisicao.status_requisicao == 'AG':
        messages.info(request, 'Este formulário ainda não foi preenchido.')
        return redirect('vagas:formulario_publico', hash_id=hash_id)
    
    # Verificar se existe vaga vinculada usando o método get_vaga()
    vaga_vinculada = requisicao.get_vaga()
    candidatos_selecionados = []
    candidatos_selecionados_cpfs = []
    candidatos_da_vaga = []
    solicitacoes_desativacao = []
    
    if vaga_vinculada:
        candidatos_selecionados = CandidatoSelecionado.objects.filter(requisicao_vaga=requisicao)
        candidatos_selecionados_cpfs = list(candidatos_selecionados.values_list('cpf', flat=True))
        
        # Buscar solicitações de desativação da vaga
        from .models import SolicitacaoDesativacao
        solicitacoes_desativacao = SolicitacaoDesativacao.objects.filter(
            vaga=vaga_vinculada, formulario=requisicao
        ).order_by('-dt_criacao')
        
        # Buscar pessoas que se candidataram a esta vaga
        # Primeiro, buscar os candidatos do modelo Candidato
        candidatos_modelo = Candidato.objects.filter(vaga=vaga_vinculada)
        
        # Depois buscar as pessoas correspondentes no modelo Pessoa
        # from autenticacao.models import Pessoa
        # cpfs_candidatos = candidatos_modelo.values_list('cpf', flat=True)
        # candidatos_da_vaga = Pessoa.objects.filter(cpf__in=cpfs_candidatos)
    
    context = {
        'requisicao': requisicao,
        'vaga_vinculada': vaga_vinculada,
        'candidatos_selecionados': candidatos_selecionados,
        'candidatos_selecionados_cpfs': candidatos_selecionados_cpfs,
        'candidatos_da_vaga': candidatos_modelo,
        'solicitacoes_desativacao': solicitacoes_desativacao,
        'escolaridades': Escolaridade.objects.all(),
    }
    return render(request, 'vagas/formulario_detalhes_externo.html', context)


def formulario_sucesso(request):
    """Página de sucesso após envio do formulário"""
    return render(request, 'vagas/formulario_sucesso.html')


def cadastrar_vaga_aprovada(request, id):
    """Tela para cadastrar vaga baseada em formulário aprovado"""
    # Verificar se o formulário existe
    try:
        requisicao = RequisicaoVaga.objects.get(pk=id)
    except RequisicaoVaga.DoesNotExist:
        messages.error(request, 'Requisição não encontrada.')
        return redirect('vagas:admin_formularios_list')
    
    # Verificar se foi aprovado
    if requisicao.status_requisicao != 'AP':
        messages.error(request, 'Esta requisição precisa estar aprovada para cadastrar a vaga.')
        return redirect('vagas:admin_formularios_detail', id=id)
    
    if request.method == 'POST':
        # Processar formulário de cadastro de vaga
        try:
            # Verificar se vai criar nova empresa ou usar existente
            empresa_id = request.POST.get('empresa_id')
            if empresa_id == 'nova' or not empresa_id:
                # Verificar se já existe empresa com esse CNPJ
                try:
                    empresa = Empresa.objects.get(cnpj=requisicao.cnpj_da_empresa)
                except Empresa.DoesNotExist:
                    # Criar nova empresa baseada nos dados da requisição
                    empresa = Empresa.objects.create(
                        nome=requisicao.nome_da_empresa,
                        cnpj=requisicao.cnpj_da_empresa,
                        email=requisicao.email_da_empresa,
                        telefone=requisicao.telefone_da_empresa,
                        whatsapp=requisicao.whatsapp_da_empresa,
                        endereco=requisicao.endereco_da_empresa,
                        user=request.user
                    )
            else:
                empresa = Empresa.objects.get(pk=empresa_id)
            
            # Verificar se vai criar novo cargo ou usar existente
            cargo_id = request.POST.get('cargo_id')
            if cargo_id == 'novo' or not cargo_id:
                # Verificar se já existe cargo com esse nome
                try:
                    cargo = Cargo.objects.get(nome=requisicao.cargo_ofertado)
                except Cargo.DoesNotExist:
                    # Criar novo cargo baseado no nome da requisição
                    cargo = Cargo.objects.create(
                        nome=requisicao.cargo_ofertado,
                        user=request.user
                    )
            else:
                cargo = Cargo.objects.get(pk=cargo_id)
            
            # Validar dados obrigatórios
            quantidade_vagas = request.POST.get('quantidade_vagas')
            escolaridade_id = request.POST.get('escolaridade')
            experiencia = request.POST.get('experiencia')
            
            if not quantidade_vagas or not escolaridade_id or not experiencia:
                messages.error(request, 'Por favor, preencha todos os campos obrigatórios.')
                return redirect('vagas:cadastrar_vaga_aprovada', id=id)
            
            # Criar a vaga
            vaga = Vaga_Emprego.objects.create(
                empresa=empresa,
                cargo=cargo,
                requisicao_vaga=requisicao,  # Vincular à requisição
                quantidadeVagas=int(quantidade_vagas),
                escolaridade_id=int(escolaridade_id),
                salario=request.POST.get('salario', ''),
                experiencia=experiencia,
                observacao=request.POST.get('observacao', ''),
                tipo_de_vaga=request.POST.get('tipo_de_vaga'),
                carga_horaria=request.POST.get('carga_horaria', ''),
                regime=request.POST.get('regime', ''),
                atribuicoes=request.POST.get('atribuicoes', ''),
                email=request.POST.get('email', ''),
                destaque=request.POST.get('destaque') == 'on',
                user=request.user
            )
            
            # Criar histórico
            from .models import HistoricoRequisicao
            HistoricoRequisicao.objects.create(
                requisicao=requisicao,
                acao='ED',  # Edição/Processamento
                observacao=f'Vaga cadastrada no sistema: {vaga}',
                usuario=request.user
            )
            
            messages.success(request, f'Vaga "{cargo.nome}" cadastrada com sucesso!')
            return redirect('vagas:admin_formularios_detail', id=id)
            
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar vaga: {str(e)}')
    
    # Buscar empresas e cargos similares no sistema
    empresas_similares = Empresa.objects.filter(
        Q(nome__icontains=requisicao.nome_da_empresa) |
        Q(cnpj=requisicao.cnpj_da_empresa)
    ).distinct()[:5]
    
    cargos_similares = Cargo.objects.filter(
        nome__icontains=requisicao.cargo_ofertado
    ).distinct()[:5]
    
    # Dados para o autocomplete JavaScript
    import json
    todas_empresas = list(Empresa.objects.values('id', 'nome', 'cnpj')[:100])  # Limitar para performance
    todos_cargos = list(Cargo.objects.values('id', 'nome'))
    
    context = {
        'requisicao': requisicao,
        'empresas_similares': empresas_similares,
        'cargos_similares': cargos_similares,
        'todas_empresas_json': json.dumps(todas_empresas),
        'todos_cargos_json': json.dumps(todos_cargos),
        'escolaridades': Escolaridade.objects.all(),
    }
    
    return render(request, 'vagas/cadastrar_vaga_aprovada.html', context)


@login_required
def candidatos_vaga(request, vaga_id):
    """Detalhes completos da vaga e seus candidatos"""
    try:
        vaga = Vaga_Emprego.objects.get(pk=vaga_id)
    except Vaga_Emprego.DoesNotExist:
        messages.error(request, 'Vaga não encontrada.')
        return redirect('vagas:painel_administrativo')
    
    # Buscar candidatos desta vaga
    candidatos = Candidato.objects.filter(vaga=vaga).order_by('-dt_inclusao')
    
    # Estatísticas dos candidatos
    total_candidatos = candidatos.count()
    candidatos_ativos = candidatos.filter(candidato_ativo=True).count()
    candidatos_contratados = candidatos.filter(conseguiu_vaga=True).count()
    candidatos_online = candidatos.filter(candidato_online=True).count()
    candidatos_balcao = candidatos.filter(candidato_online=False).count()
    
    # Estatísticas da vaga
    dias_publicada = (timezone.now().date() - vaga.dt_inclusao.date()).days if vaga.dt_inclusao else 0
    posicoes_preenchidas = candidatos_contratados
    posicoes_restantes = max(0, vaga.quantidadeVagas - posicoes_preenchidas)
    
    # Buscar requisições relacionadas
    try:
        requisicoes = RequisicaoVaga.objects.filter(vaga=vaga).order_by('-dt_inclusao')
        total_requisicoes = requisicoes.count()
        requisicoes_aprovadas = requisicoes.filter(status='APROVADO').count()
        requisicoes_pendentes = requisicoes.filter(status='PENDENTE').count()
    except:
        requisicoes = []
        total_requisicoes = 0
        requisicoes_aprovadas = 0
        requisicoes_pendentes = 0
    
    # Determinar origem da navegação
    origem = request.GET.get('origem', '')  # 'empresa' ou 'formulario'
    empresa_id = request.GET.get('empresa_id', '')
    
    context = {
        'vaga': vaga,
        'candidatos': candidatos,
        'total_candidatos': total_candidatos,
        'candidatos_ativos': candidatos_ativos,
        'candidatos_contratados': candidatos_contratados,
        'candidatos_online': candidatos_online,
        'candidatos_balcao': candidatos_balcao,
        'dias_publicada': dias_publicada,
        'posicoes_preenchidas': posicoes_preenchidas,
        'posicoes_restantes': posicoes_restantes,
        'requisicoes': requisicoes,
        'total_requisicoes': total_requisicoes,
        'requisicoes_aprovadas': requisicoes_aprovadas,
        'requisicoes_pendentes': requisicoes_pendentes,
        'origem': origem,
        'empresa_id': empresa_id,
    }
    
    return render(request, 'vagas/detalhes_vaga.html', context)


def selecionar_candidato(request, hash_id):
    """Selecionar candidato para requisição via interface externa"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'})
    
    try:
        # Verificar se a requisição existe
        requisicao = RequisicaoVaga.objects.get(hash_id=hash_id)
    except RequisicaoVaga.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Requisição não encontrada'})
    
    # Verificar autenticação via cookie
    auth_cookie = request.COOKIES.get('formulario_auth')
    if not auth_cookie or auth_cookie != requisicao.auth_hash_temp:
        return JsonResponse({'success': False, 'message': 'Acesso não autorizado'})
    
    # Verificar se existe vaga vinculada
    try:
        vaga_vinculada = Vaga_Emprego.objects.get(requisicao_vaga=requisicao)
    except Vaga_Emprego.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vaga não encontrada'})
    
    import json
    data = json.loads(request.body)
    cpf = data.get('cpf')
    
    if not cpf:
        return JsonResponse({'success': False, 'message': 'CPF não informado'})
    
    # Verificar se o candidato existe na vaga
    try:
        from autenticacao.models import Pessoa
        candidato = Pessoa.objects.get(cpf=cpf)
        if not candidato.vagas.filter(id=vaga_vinculada.id).exists():
            return JsonResponse({'success': False, 'message': 'Candidato não está inscrito nesta vaga'})
    except Pessoa.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Candidato não encontrado'})
    
    # Verificar se já foi selecionado
    if CandidatoSelecionado.objects.filter(requisicao_vaga=requisicao, cpf=cpf).exists():
        return JsonResponse({'success': False, 'message': 'Candidato já foi selecionado'})
    
    # Criar seleção
    try:
        candidato_selecionado = CandidatoSelecionado.objects.create(
            requisicao_vaga=requisicao,
            cpf=cpf,
            nome=candidato.nome,
            status='PE',  # Pendente
            usuario_selecao=request.user if request.user.is_authenticated else None
        )
        return JsonResponse({'success': True, 'message': 'Candidato selecionado com sucesso'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao selecionar candidato: {str(e)}'})


def atualizar_status_candidato(request, hash_id):
    """Atualizar status de candidato selecionado via interface externa"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'})
    
    try:
        # Verificar se a requisição existe
        requisicao = RequisicaoVaga.objects.get(hash_id=hash_id)
    except RequisicaoVaga.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Requisição não encontrada'})
    
    # Verificar autenticação via cookie
    auth_cookie = request.COOKIES.get('formulario_auth')
    if not auth_cookie or auth_cookie != requisicao.auth_hash_temp:
        return JsonResponse({'success': False, 'message': 'Acesso não autorizado'})
    
    import json
    data = json.loads(request.body)
    candidato_id = data.get('candidato_id')
    novo_status = data.get('status')
    
    if not candidato_id or not novo_status:
        return JsonResponse({'success': False, 'message': 'Dados incompletos'})
    
    # Verificar se o status é válido
    status_validos = ['PE', 'AP', 'RE', 'CO']
    if novo_status not in status_validos:
        return JsonResponse({'success': False, 'message': 'Status inválido'})
    
    try:
        candidato_selecionado = CandidatoSelecionado.objects.get(
            id=candidato_id, 
            requisicao_vaga=requisicao
        )
        
        # Verificar se a mudança é válida
        if candidato_selecionado.status_selecao == 'CO':
            return JsonResponse({'success': False, 'message': 'Candidato já foi contratado'})
        
        # Atualizar status
        status_anterior = candidato_selecionado.status_selecao
        candidato_selecionado.status_selecao = novo_status
        candidato_selecionado.dt_atualizacao = timezone.now()
        candidato_selecionado.save()
        
        # Se contratado, reduzir vagas disponíveis
        if novo_status == 'CO':
            vaga_vinculada = Vaga_Emprego.objects.get(requisicao_vaga=requisicao)
            if vaga_vinculada.quantidadeVagas > 0:
                vaga_vinculada.quantidadeVagas -= 1
                vaga_vinculada.save()
        
        # Se mudou de contratado para outro status, aumentar vagas disponíveis
        elif status_anterior == 'CO' and novo_status != 'CO':
            vaga_vinculada = Vaga_Emprego.objects.get(requisicao_vaga=requisicao)
            vaga_vinculada.quantidadeVagas += 1
            vaga_vinculada.save()
        
        return JsonResponse({'success': True, 'message': 'Status atualizado com sucesso'})
        
    except CandidatoSelecionado.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Candidato selecionado não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao atualizar status: {str(e)}'})


def solicitar_encerramento_vaga(request, hash_id):
    """Solicitar encerramento de vaga via interface externa"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'})
    
    try:
        # Verificar se a requisição existe
        requisicao = RequisicaoVaga.objects.get(hash_id=hash_id)
    except RequisicaoVaga.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Requisição não encontrada'})
    
    # Verificar autenticação via cookie
    auth_cookie = request.COOKIES.get('formulario_auth')
    if not auth_cookie or auth_cookie != requisicao.auth_hash_temp:
        return JsonResponse({'success': False, 'message': 'Acesso não autorizado'})
    
    # Verificar se existe vaga vinculada
    try:
        vaga_vinculada = Vaga_Emprego.objects.get(requisicao_vaga=requisicao)
    except Vaga_Emprego.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vaga não encontrada'})
    
    # Verificar se já existe uma solicitação de desativação pendente
    from .models import SolicitacaoDesativacao
    solicitacao_existente = SolicitacaoDesativacao.objects.filter(
        vaga=vaga_vinculada,
        status='pendente'
    ).exists()
    
    if solicitacao_existente:
        return JsonResponse({'success': False, 'message': 'Já existe uma solicitação de desativação pendente para esta vaga.'})
    
    import json
    from django.utils import timezone
    data = json.loads(request.body)
    motivo = data.get('motivo', 'outro')
    observacoes = data.get('observacoes', 'Solicitação via interface externa')
    
    try:
        # Buscar ou criar um ResponsavelEmpresa para a empresa da vaga
        # Se não existir, vamos criar um temporário ou usar informações da requisição
        from .models import ResponsavelEmpresa
        try:
            responsavel = ResponsavelEmpresa.objects.filter(
                empresa=vaga_vinculada.empresa,
                ativo=True
            ).first()
            
            if not responsavel:
                # Se não há responsável, criar uma entrada temporária ou usar o sistema existente
                # Por enquanto, vamos usar None e ajustar o modelo para aceitar isso
                responsavel = None
        except:
            responsavel = None
        
        # Criar a solicitação de desativação
        solicitacao = SolicitacaoDesativacao.objects.create(
            vaga=vaga_vinculada,
            formulario=requisicao,
            empresa_responsavel=responsavel,
            motivo=motivo,
            observacoes=observacoes
        )
        
        # Registrar no histórico
        HistoricoRequisicao.objects.create(
            requisicao=requisicao,
            acao='OB',  # Observação/Ação
            observacao=f'Solicitação de desativação criada - {solicitacao.get_motivo_display()}' + 
                      (f': {observacoes}' if observacoes else ''),
            usuario=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Solicitação de desativação enviada com sucesso! O administrador irá analisar a solicitação.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao registrar solicitação: {str(e)}'})


@login_required
def editar_vaga(request, vaga_id):
    """Editar uma vaga existente no painel administrativo"""
    try:
        vaga = Vaga_Emprego.objects.get(pk=vaga_id)
    except Vaga_Emprego.DoesNotExist:
        messages.error(request, 'Vaga não encontrada.')
        return redirect('vagas:admin_vagas_list')
    
    if request.method == 'POST':
        try:
            # Atualizar dados da vaga
            vaga.quantidadeVagas = int(request.POST.get('quantidadeVagas', vaga.quantidadeVagas))
            vaga.observacao = request.POST.get('observacao', vaga.observacao)
            vaga.atribuicoes = request.POST.get('atribuicoes', vaga.atribuicoes)
            vaga.salario = request.POST.get('salario', vaga.salario)
            vaga.carga_horaria = request.POST.get('carga_horaria', vaga.carga_horaria)
            vaga.regime = request.POST.get('regime', vaga.regime)
            vaga.experiencia = request.POST.get('experiencia', vaga.experiencia)
            vaga.tipo_de_vaga = request.POST.get('tipo_de_vaga', vaga.tipo_de_vaga)
            vaga.email = request.POST.get('email', vaga.email)
            vaga.ativo = request.POST.get('ativo') == 'on'
            vaga.destaque = request.POST.get('destaque') == 'on'
            
            # Atualizar cargo se fornecido
            cargo_id = request.POST.get('cargo_id')
            if cargo_id:
                try:
                    cargo = Cargo.objects.get(pk=cargo_id)
                    vaga.cargo = cargo
                except Cargo.DoesNotExist:
                    pass
            
            # Atualizar escolaridade se fornecido
            escolaridade_id = request.POST.get('escolaridade')
            if escolaridade_id:
                try:
                    escolaridade = Escolaridade.objects.get(pk=escolaridade_id)
                    vaga.escolaridade = escolaridade
                except Escolaridade.DoesNotExist:
                    pass
            
            vaga.dt_atualizacao = timezone.now()
            vaga.save()
            
            messages.success(request, 'Vaga atualizada com sucesso!')
            return redirect('vagas:candidatos_vaga', vaga_id=vaga.id)
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar vaga: {str(e)}')
    
    # Buscar todos os cargos e escolaridades para os dropdowns
    cargos = Cargo.objects.all().order_by('nome')
    escolaridades = Escolaridade.objects.all().order_by('nome')
    
    # Estatísticas da vaga para o contexto
    candidatos = Candidato.objects.filter(vaga=vaga)
    total_candidatos = candidatos.count()
    candidatos_contratados = candidatos.filter(conseguiu_vaga=True).count()

    context = {
        'vaga': vaga,
        'cargos': cargos,
        'escolaridades': escolaridades,
        'total_candidatos': total_candidatos,
        'candidatos_contratados': candidatos_contratados,
    }
    
    return render(request, 'vagas/editar_vaga.html', context)


# ============================================================================
# VIEWS PARA GERENCIAMENTO DE RESPONSÁVEIS DAS EMPRESAS
# ============================================================================

@staff_required
def gerenciar_responsaveis_empresa(request, empresa_id):
    """View para gerenciar responsáveis de uma empresa específica"""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    if request.method == 'POST':
        try:
            nome = request.POST.get('nome', '').strip()
            cpf = request.POST.get('cpf', '').strip()
            email = request.POST.get('email', '').strip()
            cargo = request.POST.get('cargo', '').strip()
            telefone = request.POST.get('telefone', '').strip()
            
            if not nome or not cpf or not email:
                messages.error(request, 'Nome, CPF e email são obrigatórios.')
                return redirect('vagas:gerenciar_responsaveis_empresa', empresa_id=empresa_id)
            
            # Limpar CPF (remover pontos e traços)
            cpf_numeros = ''.join(filter(str.isdigit, cpf))
            
            if len(cpf_numeros) != 11:
                messages.error(request, 'CPF deve ter 11 dígitos.')
                return redirect('vagas:gerenciar_responsaveis_empresa', empresa_id=empresa_id)
            
            # Verificar se CPF já é responsável desta mesma empresa
            if ResponsavelEmpresa.objects.filter(cpf=cpf_numeros, empresa=empresa).exists():
                messages.error(request, f'O CPF {cpf} já é responsável desta empresa.')
                return redirect('vagas:gerenciar_responsaveis_empresa', empresa_id=empresa_id)
            
            # Informativo se CPF já é responsável de outra empresa
            if ResponsavelEmpresa.objects.filter(cpf=cpf_numeros).exists():
                outras_empresas = ResponsavelEmpresa.objects.filter(cpf=cpf_numeros)
                empresas_nomes = ", ".join([resp.empresa.nome for resp in outras_empresas])
                messages.warning(request, f'O CPF {cpf} já é responsável da(s) empresa(s): {empresas_nomes}, mas será adicionado também a esta empresa.')
            
            # Verificar o nível de responsável (principal ou auxiliar)
            nivel = request.POST.get('nivel', 'RESP')  # Default para Responsável Principal
            
            # Criar ResponsavelEmpresa
            responsavel = ResponsavelEmpresa.objects.create(
                empresa=empresa,
                nome=nome,
                cpf=cpf_numeros,
                email=email,
                cargo=cargo,
                telefone=telefone,
                nivel=nivel,
                criado_por=request.user
            )
            
            # Tentar vincular a usuário existente
            if responsavel.vincular_usuario_existente():
                # Se conseguiu vincular, adicionar ao grupo empresa_user
                from django.contrib.auth.models import Group
                grupo_empresa, created = Group.objects.get_or_create(name='empresa_user')
                responsavel.user.groups.add(grupo_empresa)
                responsavel.save()
                
                messages.success(request, f'Responsável {nome} adicionado e vinculado ao usuário existente!')
            else:
                # Se não existe usuário, criar um novo
                from autenticacao.models import Pessoa
                from django.contrib.auth.models import Group
                
                # Verificar se já existe usuário com esse email
                if User.objects.filter(email=email).exists():
                    user = User.objects.get(email=email)
                else:
                    # Criar novo usuário
                    username = email
                    contador = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{email}_{contador}"
                        contador += 1
                    
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=nome,
                        is_active=True
                    )
                    
                    # Gerar senha temporária
                    import random
                    import string
                    senha_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    user.set_password(senha_temp)
                    user.save()
                    
                    messages.info(request, f'Usuário criado com senha temporária: {senha_temp}')
                
                # Vincular usuário ao responsável
                responsavel.user = user
                responsavel.save()
                
                # Adicionar ao grupo empresa_user
                grupo_empresa, created = Group.objects.get_or_create(name='empresa_user')
                user.groups.add(grupo_empresa)
                
                messages.success(request, f'Responsável {nome} adicionado com sucesso!')
            
        except Exception as e:
            messages.error(request, f'Erro ao adicionar responsável: {str(e)}')
    
    # Buscar responsáveis existentes
    responsaveis = ResponsavelEmpresa.objects.filter(empresa=empresa).order_by('nome')
    
    context = {
        'empresa': empresa,
        'responsaveis': responsaveis,
    }
    
    return render(request, 'vagas/gerenciar_responsaveis.html', context)


@staff_required
def remover_responsavel_empresa(request, responsavel_id):
    """Remove um responsável da empresa"""
    responsavel = get_object_or_404(ResponsavelEmpresa, id=responsavel_id)
    empresa_id = responsavel.empresa.id
    
    if request.method == 'POST':
        try:
            # Remover do grupo empresa_user se não for responsável de outras empresas
            user = responsavel.user
            responsavel.delete()
            
            # Verificar se ainda é responsável de outras empresas
            if not ResponsavelEmpresa.objects.filter(user=user).exists():
                from django.contrib.auth.models import Group
                try:
                    grupo_empresa = Group.objects.get(name='empresa_user')
                    user.groups.remove(grupo_empresa)
                except Group.DoesNotExist:
                    pass
            
            messages.success(request, 'Responsável removido com sucesso!')
            
        except Exception as e:
            messages.error(request, f'Erro ao remover responsável: {str(e)}')
    
    return redirect('vagas:gerenciar_responsaveis_empresa', empresa_id=empresa_id)


@staff_required
def editar_responsavel_empresa(request, responsavel_id):
    """View para editar detalhes de um responsável da empresa"""
    responsavel = get_object_or_404(ResponsavelEmpresa, id=responsavel_id)
    empresa_id = responsavel.empresa.id
    
    if request.method == 'POST':
        try:
            # Dados básicos
            nome = request.POST.get('nome', '').strip()
            email = request.POST.get('email', '').strip()
            cargo = request.POST.get('cargo', '').strip()
            telefone = request.POST.get('telefone', '').strip()
            nivel = request.POST.get('nivel', responsavel.nivel)
            ativo = request.POST.get('ativo') == 'on'
            observacoes = request.POST.get('observacoes', '').strip()
            
            # Atualizar os dados
            responsavel.nome = nome
            responsavel.email = email
            responsavel.cargo = cargo
            responsavel.telefone = telefone
            responsavel.nivel = nivel
            responsavel.ativo = ativo
            responsavel.observacoes = observacoes
            responsavel.save()
            
            # Atualizar email do usuário também se necessário
            if responsavel.user and responsavel.user.email != email:
                responsavel.user.email = email
                responsavel.user.save()
            
            messages.success(request, f'Dados do responsável {nome} atualizados com sucesso!')
            return redirect('vagas:gerenciar_responsaveis_empresa', empresa_id=empresa_id)
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar responsável: {str(e)}')
            
    # Se for GET ou se houver erro no POST, exibir o formulário
    empresa = responsavel.empresa
    context = {
        'empresa': empresa,
        'responsavel': responsavel,
    }
    
    return render(request, 'vagas/editar_responsavel.html', context)


@staff_required
def toggle_responsavel_ativo(request, responsavel_id):
    """Ativa/Desativa um responsável da empresa"""
    responsavel = get_object_or_404(ResponsavelEmpresa, id=responsavel_id)
    empresa_id = responsavel.empresa.id
    
    if request.method == 'POST':
        try:
            responsavel.ativo = not responsavel.ativo
            responsavel.save()
            
            status = 'ativado' if responsavel.ativo else 'desativado'
            messages.success(request, f'Responsável {status} com sucesso!')
            
        except Exception as e:
            messages.error(request, f'Erro ao alterar status: {str(e)}')
    
    return redirect('vagas:gerenciar_responsaveis_empresa', empresa_id=empresa_id)


# ============================================================================
# PAINEL EMPRESARIAL - VIEWS PARA RESPONSÁVEIS DAS EMPRESAS
# ============================================================================

from balcao_de_emprego.decorators import empresa_user_required

def get_empresa_selecionada(request):
    """Função auxiliar para obter a empresa selecionada pelo responsável"""
    # Buscar todas as empresas do responsável
    responsaveis = ResponsavelEmpresa.objects.filter(user=request.user, ativo=True)
    print(responsaveis)
    if not responsaveis.exists():
        return None, None, None
    
    # Verificar se há empresa selecionada via POST ou session
    empresa_id = None
    if request.POST.get('empresa_id'):
        empresa_id = request.POST.get('empresa_id')
    elif request.session.get('empresa_selecionada'):
        empresa_id = request.session.get('empresa_selecionada')
    
    # Se há empresa específica selecionada
    if empresa_id:
        try:
            responsavel = responsaveis.get(empresa_id=empresa_id)
            # Salvar na session
            request.session['empresa_selecionada'] = str(empresa_id)
        except ResponsavelEmpresa.DoesNotExist:
            # Se a empresa não existe para este responsável, usar a primeira
            responsavel = responsaveis.first()
            if responsavel:
                request.session['empresa_selecionada'] = str(responsavel.empresa.id)
            else:
                return None, None, responsaveis
    else:
        # Se não há empresa selecionada, usar a primeira
        responsavel = responsaveis.first()
        if responsavel:
            request.session['empresa_selecionada'] = str(responsavel.empresa.id)
        else:
            return None, None, responsaveis
    
    return responsavel, responsavel.empresa, responsaveis

@empresa_user_required
def dashboard_empresa(request):
    """Dashboard principal para responsáveis das empresas"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Estatísticas da empresa
        total_vagas = Vaga_Emprego.objects.filter(empresa=empresa).count()
        vagas_ativas = Vaga_Emprego.objects.filter(empresa=empresa, ativo=True).count()
        
        # Candidatos da empresa
        candidatos_total = Candidato.objects.filter(vaga__empresa=empresa).count()
        candidatos_unicos = Candidato.objects.filter(vaga__empresa=empresa).values('cpf').distinct().count()
        candidatos_contratados = Candidato.objects.filter(vaga__empresa=empresa, conseguiu_vaga=True).count()
        
        # Formulários da empresa (por CNPJ)
        formularios = RequisicaoVaga.objects.filter(cnpj_da_empresa=empresa.cnpj).order_by('-dt_inclusao')
        formularios_pendentes = formularios.filter(status_requisicao='PE').count()
        formularios_aprovados = formularios.filter(status_requisicao='AP').count()
        formularios_rejeitados = formularios.filter(status_requisicao='RE').count()
        
        # Últimas atividades
        ultimos_formularios = formularios[:5]
        ultimas_vagas = Vaga_Emprego.objects.filter(empresa=empresa).order_by('-dt_inclusao')[:5]
        
        # Candidatos recentes
        candidatos_recentes = Candidato.objects.filter(
            vaga__empresa=empresa
        ).order_by('-dt_inclusao')[:10]
        
        # Taxa de conversão
        taxa_conversao = 0
        if candidatos_total > 0:
            taxa_conversao = round((candidatos_contratados / candidatos_total) * 100, 1)
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'total_vagas': total_vagas,
            'vagas_ativas': vagas_ativas,
            'candidatos_total': candidatos_total,
            'candidatos_unicos': candidatos_unicos,
            'candidatos_contratados': candidatos_contratados,
            'taxa_conversao': taxa_conversao,
            'formularios': formularios,
            'formularios_pendentes': formularios_pendentes,
            'formularios_aprovados': formularios_aprovados,
            'formularios_rejeitados': formularios_rejeitados,
            'ultimos_formularios': ultimos_formularios,
            'ultimas_vagas': ultimas_vagas,
            'candidatos_recentes': candidatos_recentes,
        }
        
        return render(request, 'vagas/dashboard_empresa.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar dashboard: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_formularios(request):
    """Lista todos os formulários da empresa do responsável"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        formularios = RequisicaoVaga.objects.filter(
            cnpj_da_empresa=empresa.cnpj
        ).order_by('-dt_inclusao')
        
        # Filtros
        status_filter = request.GET.get('status', '')
        if status_filter:
            formularios = formularios.filter(status_requisicao=status_filter)
        
        # Calcular estatísticas
        formularios_pendentes = formularios.filter(status_requisicao='PE').count()
        formularios_aprovados = formularios.filter(status_requisicao='AP').count()
        formularios_rejeitados = formularios.filter(status_requisicao='RE').count()
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'formularios': formularios,
            'status_filter': status_filter,
            'formularios_pendentes': formularios_pendentes,
            'formularios_aprovados': formularios_aprovados,
            'formularios_rejeitados': formularios_rejeitados,
        }
        
        return render(request, 'vagas/empresa_formularios.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar formulários: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_formulario_criar(request):
    """Criar novo formulário de requisição pelo painel da empresa"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Buscar escolaridades para o formulário
        escolaridades = Escolaridade.objects.all().order_by('id')
        
        if request.method == 'POST':
            # Dados da vaga
            cargo_ofertado = request.POST.get('cargo_ofertado', '').strip()
            quantidade_de_vagas = request.POST.get('quantidade_de_vagas', 1)
            salario = request.POST.get('salario', 0)
            escolaridade_id = request.POST.get('escolaridade_id', 1)
            turno = request.POST.get('turno', 'IN')
            regime = request.POST.get('regime', 'CLT')
            tipo_vaga = request.POST.get('tipo_vaga', 'NML')
            experiencia = request.POST.get('experiencia', 'Des')
            local_de_trabalho = request.POST.get('local_de_trabalho', '').strip()
            descricao_cargo = request.POST.get('descricao_cargo', '').strip()
            beneficios = request.POST.get('beneficios', '').strip()
            
            # Verificações básicas
            if not cargo_ofertado or not descricao_cargo:
                messages.error(request, 'Por favor, preencha todos os campos obrigatórios.')
                return redirect('vagas:empresa_formulario_criar')
            
            # Criar chave de acesso a partir da hash da sessão
            session_key = request.session.session_key or request.session.create()
            chave_acesso = f"{empresa.cnpj[:8]}_{session_key[:8]}_{timezone.now().strftime('%y%m%d%H%M%S')}"
            
            # Criar nova requisição com dados completos
            requisicao = RequisicaoVaga.objects.create(
                # Dados do responsável (preenchidos automaticamente)
                nome_do_responsavel_pela_divulgacao_da_vaga=responsavel.nome,
                cpf_do_responsavel=responsavel.cpf,
                contato_do_responsavel=responsavel.telefone or '',
                
                # Dados da empresa (preenchidos automaticamente)
                nome_da_empresa=empresa.nome,
                cnpj_da_empresa=empresa.cnpj,
                email_da_empresa=empresa.email or '',
                endereco_da_empresa=empresa.endereco or '',
                telefone_da_empresa=empresa.telefone or '',
                whatsapp_da_empresa=empresa.whatsapp or '',
                segmento_da_empresa='', # Poderia ser adicionado ao modelo Empresa
                
                # Dados da vaga (fornecidos no formulário)
                quantidade_de_vagas=quantidade_de_vagas,
                cargo_ofertado=cargo_ofertado,
                escolaridade_id=escolaridade_id,
                tipo_de_vaga=tipo_vaga,
                regime=regime,
                experiencia=experiencia,
                faixa_salarial='VALOR', # Usando o valor informado
                valor_salario=salario,
                
                # Benefícios
                vale_transporte='vale_transporte' in request.POST,
                vale_alimentacao='vale_alimentacao' in request.POST,
                outros_beneficios=beneficios,
                
                # Informações adicionais
                observacao=descricao_cargo,
                
                # Status e controle
                status_requisicao='PE',  # Pendente por padrão
                chave_de_acesso=chave_acesso,
            )
            
            messages.success(request, 'Solicitação de vaga enviada com sucesso! Aguarde a análise da nossa equipe.')
            return redirect('vagas:empresa_formulario_detalhes', formulario_id=requisicao.pk)
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'escolaridades': escolaridades,
        }
        
        return render(request, 'vagas/empresa_formulario_criar.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao criar formulário: {str(e)}')
        return redirect('vagas:empresa_formularios')


@empresa_user_required
def empresa_formulario_detalhes(request, formulario_id):
    """Detalhes de um formulário específico da empresa"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        formulario = get_object_or_404(
            RequisicaoVaga, 
            id=formulario_id,
            cnpj_da_empresa=empresa.cnpj
        )
        
        # Verificar se existe vaga vinculada usando o método get_vaga()
        vaga_vinculada = formulario.get_vaga()
        candidatos_da_vaga = []
        
        # Flag para indicar que devemos usar os dados da vaga vinculada em vez dos dados do formulário
        usar_dados_vaga = formulario.status_requisicao == 'AP' and vaga_vinculada is not None
        
        if vaga_vinculada:
            # Buscar pessoas que se candidataram a esta vaga
            # Primeiro, buscar os candidatos do modelo Candidato
            candidatos_modelo = Candidato.objects.filter(vaga=vaga_vinculada)
            
            # Depois buscar as pessoas correspondentes no modelo Pessoa
            from autenticacao.models import Pessoa
            cpfs_candidatos = candidatos_modelo.values_list('cpf', flat=True)
            candidatos_da_vaga = Pessoa.objects.filter(cpf__in=cpfs_candidatos)
        
        # Garantir que sempre temos um "cargo" disponível para o template, independente do status
        from types import SimpleNamespace
        
        # Se houver uma vaga vinculada, não precisamos adicionar o cargo manualmente, pois será usado vaga_vinculada.cargo
        if not vaga_vinculada:
            # Tentar encontrar o cargo pelo nome no campo cargo_ofertado
            try:
                cargo = Cargo.objects.get(nome__iexact=formulario.cargo_ofertado)
                formulario.cargo = cargo
            except Cargo.DoesNotExist:
                # Se não encontrar cargo, criar um objeto virtual apenas para o template
                formulario.cargo = SimpleNamespace(nome=formulario.cargo_ofertado)
                
            # Buscar a escolaridade
            try:
                escolaridade = Escolaridade.objects.get(pk=formulario.escolaridade_id)
                # Já deve estar carregado pelo foreign key, mas vamos garantir
            except Exception:
                # Se não conseguir carregar, criar um placeholder
                formulario.escolaridade = SimpleNamespace(nome="Não especificada")
                
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'formulario': formulario,
            'vaga_vinculada': vaga_vinculada,
            'candidatos_da_vaga': candidatos_da_vaga,
            'usar_dados_vaga': formulario.status_requisicao == 'AP' and vaga_vinculada is not None,
        }
        
        return render(request, 'vagas/empresa_formulario_detalhes.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar detalhes do formulário: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_formulario_editar(request, formulario_id):
    """Editar formulário de requisição pelo painel da empresa"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Buscar o formulário específico
        formulario = get_object_or_404(
            RequisicaoVaga, 
            id=formulario_id,
            cnpj_da_empresa=empresa.cnpj
        )
        
        # Verificar se o formulário pode ser editado
        if formulario.status_requisicao not in ['PE', 'AG']:
            messages.error(request, 'Este formulário não pode ser editado no status atual.')
            return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario_id)
        
        # Buscar escolaridades para o formulário
        escolaridades = Escolaridade.objects.all().order_by('id')
        
        if request.method == 'POST':
            # Dados da vaga
            cargo_ofertado = request.POST.get('cargo_ofertado', '').strip()
            quantidade_de_vagas = request.POST.get('quantidade_de_vagas', 1)
            salario = request.POST.get('salario', 0)
            escolaridade_id = request.POST.get('escolaridade_id', 1)
            turno = request.POST.get('turno', 'IN')
            regime = request.POST.get('regime', 'CLT')
            tipo_vaga = request.POST.get('tipo_vaga', 'NML')
            experiencia = request.POST.get('experiencia', 'Des')
            local_de_trabalho = request.POST.get('local_de_trabalho', '').strip()
            descricao_cargo = request.POST.get('descricao_cargo', '').strip()
            beneficios = request.POST.get('beneficios', '').strip()
            
            # Verificações básicas
            if not cargo_ofertado or not descricao_cargo:
                messages.error(request, 'Por favor, preencha todos os campos obrigatórios.')
                return redirect('vagas:empresa_formulario_editar', formulario_id=formulario_id)
            
            # Atualizar a requisição
            formulario.cargo_ofertado = cargo_ofertado
            formulario.quantidade_de_vagas = quantidade_de_vagas
            formulario.valor_salario = salario
            formulario.escolaridade_id = escolaridade_id
            formulario.turno = turno
            formulario.regime = regime
            formulario.tipo_de_vaga = tipo_vaga
            formulario.experiencia = experiencia
            formulario.local_de_trabalho = local_de_trabalho
            formulario.observacao = descricao_cargo
            formulario.outros_beneficios = beneficios
            
            # Benefícios
            formulario.vale_transporte = 'vale_transporte' in request.POST
            formulario.vale_alimentacao = 'vale_alimentacao' in request.POST
            
            # Se o formulário estava "Aguardando" (AG), muda para "Pendente" (PE) após edição
            status_anterior = formulario.status_requisicao
            if formulario.status_requisicao == 'AG':
                formulario.status_requisicao = 'PE'
            
            formulario.save()
            
            # Registrar no histórico
            HistoricoRequisicao.objects.create(
                requisicao=formulario,
                acao='ED',  # Edição
                observacao=f'Formulário editado pela empresa: {cargo_ofertado}',
                usuario=request.user
            )
            
            # Se houve mudança de status, registrar também
            if status_anterior == 'AG' and formulario.status_requisicao == 'PE':
                HistoricoRequisicao.objects.create(
                    requisicao=formulario,
                    acao='ST',  # Status change
                    status_anterior='AG',
                    status_novo='PE',
                    observacao='Status alterado para "Pendente" após edição do formulário - requer nova análise',
                    usuario=request.user
                )
            
            if status_anterior == 'AG' and formulario.status_requisicao == 'PE':
                messages.success(request, 'Formulário atualizado com sucesso! O status foi alterado para "Pendente" e aguarda nova análise.')
            else:
                messages.success(request, 'Formulário atualizado com sucesso!')
            return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario.pk)
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'escolaridades': escolaridades,
            'formulario': formulario,
        }
        
        return render(request, 'vagas/empresa_formulario_editar.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao editar formulário: {str(e)}')
        return redirect('vagas:empresa_formularios')


@empresa_user_required
def empresa_vagas(request):
    """Lista todas as vagas da empresa"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        vagas = Vaga_Emprego.objects.filter(empresa=empresa).order_by('-dt_inclusao')
        
        # Filtros
        status_filter = request.GET.get('status', '')
        if status_filter == 'ativas':
            vagas = vagas.filter(ativo=True)
        elif status_filter == 'inativas':
            vagas = vagas.filter(ativo=False)
        
        # Adicionar estatísticas de candidatos para cada vaga (após filtros)
        for vaga in vagas:
            vaga.total_candidatos = vaga.candidato_set.count()
            vaga.candidatos_contratados = vaga.candidato_set.filter(conseguiu_vaga=True).count()
            vaga.candidatos_online = vaga.candidato_set.filter(candidato_online=True).count()
            vaga.candidatos_balcao = vaga.candidato_set.filter(candidato_online=False).count()
        
        # Calcular estatísticas gerais (sobre todas as vagas da empresa, não filtradas)
        total_vagas = Vaga_Emprego.objects.filter(empresa=empresa).count()
        vagas_ativas = Vaga_Emprego.objects.filter(empresa=empresa, ativo=True).count()
        vagas_inativas = Vaga_Emprego.objects.filter(empresa=empresa, ativo=False).count()
        total_candidatos_empresa = Candidato.objects.filter(vaga__empresa=empresa).count()
        total_contratados_empresa = Candidato.objects.filter(vaga__empresa=empresa, conseguiu_vaga=True).count()
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vagas': vagas,
            'status_filter': status_filter,
            'total_vagas': total_vagas,
            'vagas_ativas': vagas_ativas,
            'vagas_inativas': vagas_inativas,
            'total_candidatos_empresa': total_candidatos_empresa,
            'total_contratados_empresa': total_contratados_empresa,
        }
        
        return render(request, 'vagas/empresa_vagas.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar vagas: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_perfil(request):
    """Perfil e dados da empresa"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Processar mudança de empresa, se solicitado
        if request.method == 'POST' and 'empresa_id' in request.POST:
            empresa_id = request.POST.get('empresa_id')
            # Verificar se o usuário tem acesso a essa empresa
            if ResponsavelEmpresa.objects.filter(user=request.user, empresa_id=empresa_id, ativo=True).exists():
                request.session['empresa_selecionada'] = empresa_id
                messages.success(request, 'Empresa alterada com sucesso!')
                return redirect('vagas:empresa_perfil')
            else:
                messages.error(request, 'Você não tem permissão para acessar esta empresa.')
                return redirect('vagas:empresa_perfil')
        
        # Dados da empresa
        total_vagas = Vaga_Emprego.objects.filter(empresa=empresa).count()
        vagas_ativas = Vaga_Emprego.objects.filter(empresa=empresa, ativo=True).count()
        
        # Candidatos da empresa
        candidatos_total = Candidato.objects.filter(vaga__empresa=empresa).count()
        candidatos_unicos = Candidato.objects.filter(vaga__empresa=empresa).values('cpf').distinct().count()
        candidatos_contratados = Candidato.objects.filter(vaga__empresa=empresa, conseguiu_vaga=True).count()
        
        # Todos os responsáveis da empresa
        responsaveis = ResponsavelEmpresa.objects.filter(empresa=empresa, ativo=True)
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'responsaveis': responsaveis,
            'total_vagas': total_vagas,
            'vagas_ativas': vagas_ativas,
            'candidatos_total': candidatos_total,
            'candidatos_unicos': candidatos_unicos,
            'candidatos_contratados': candidatos_contratados,
        }
        
        return render(request, 'vagas/empresa_perfil.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar perfil: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_candidatos(request):
    """Lista de candidatos da empresa (todas as vagas)"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')

        # Obter todas as vagas da empresa para o filtro
        vagas = Vaga_Emprego.objects.filter(empresa=empresa).order_by('cargo__nome')

        # Obter todos os candidatos das vagas da empresa
        candidatos = Candidato.objects.filter(vaga__empresa=empresa).order_by('-dt_inclusao')

        # Aplicar filtros
        vaga_filter = request.GET.get('vaga', '')
        status_filter = request.GET.get('status', '')
        search_query = request.GET.get('search', '')

        if vaga_filter:
            candidatos = candidatos.filter(vaga_id=vaga_filter)

        if status_filter == 'contratados':
            candidatos = candidatos.filter(conseguiu_vaga=True)
        elif status_filter == 'pendentes':
            candidatos = candidatos.filter(conseguiu_vaga=False)

        if search_query:
            candidatos = candidatos.filter(
                Q(nome__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(cpf__icontains=search_query)
            )

        # Estatísticas
        total_candidatos = Candidato.objects.filter(vaga__empresa=empresa).count()
        candidatos_contratados = Candidato.objects.filter(vaga__empresa=empresa, conseguiu_vaga=True).count()
        candidatos_pendentes = total_candidatos - candidatos_contratados
        total_vagas = Vaga_Emprego.objects.filter(empresa=empresa, ativo=True).count()
        candidatos_online = Candidato.objects.filter(vaga__empresa=empresa, candidato_online=True).count()
        candidatos_balcao = total_candidatos - candidatos_online

        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vagas': vagas,
            'candidatos': candidatos,
            'vaga_filter': vaga_filter,
            'status_filter': status_filter,
            'search_query': search_query,
            'total_candidatos': total_candidatos,
            'candidatos_contratados': candidatos_contratados,
            'candidatos_pendentes': candidatos_pendentes,
            'total_vagas': total_vagas,
            'candidatos_online': candidatos_online,
            'candidatos_balcao': candidatos_balcao,
        }
        return render(request, 'vagas/empresa_candidatos.html', context)
    except Exception as e:
        messages.error(request, f'Erro ao carregar candidatos: {str(e)}')
        return redirect('vagas:home')
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Todos os responsáveis da empresa
        responsaveis = ResponsavelEmpresa.objects.filter(empresa=empresa, ativo=True)
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'responsaveis': responsaveis,
        }
        
        return render(request, 'vagas/empresa_perfil.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar perfil: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_vaga_detalhes(request, vaga_id):
    """Detalhes de uma vaga específica com gestão de candidatos"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        vaga = get_object_or_404(Vaga_Emprego, id=vaga_id, empresa=empresa)
        
        # Candidatos da vaga - filtrar por status da vaga
        if vaga.ativo:
            # Vaga ativa: mostrar todos os candidatos
            candidatos = Candidato.objects.filter(vaga=vaga).order_by('-dt_inclusao')
        else:
            # Vaga encerrada: mostrar apenas candidatos selecionados
            candidatos = Candidato.objects.filter(vaga=vaga, conseguiu_vaga=True).order_by('-dt_inclusao')
        
        # Estatísticas da vaga
        total_candidatos = Candidato.objects.filter(vaga=vaga).count()
        candidatos_contratados = Candidato.objects.filter(vaga=vaga, conseguiu_vaga=True).count()
        candidatos_online = Candidato.objects.filter(vaga=vaga, candidato_online=True).count()
        candidatos_balcao = Candidato.objects.filter(vaga=vaga, candidato_online=False).count()
        
        # Buscar formulário relacionado (se houver)
        formulario = None
        try:
            formulario = RequisicaoVaga.objects.filter(
                cnpj_da_empresa=empresa.cnpj,
                cargo=vaga.cargo,
                status_requisicao='AP'
            ).first()
        except:
            pass
        
        # Verificar se há um parâmetro de tab na URL
        active_tab = request.GET.get('tab', 'detalhes')
        show_candidatos_section = active_tab == 'candidatos'
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vaga': vaga,
            'candidatos': candidatos,
            'total_candidatos': total_candidatos,
            'candidatos_contratados': candidatos_contratados,
            'candidatos_online': candidatos_online,
            'candidatos_balcao': candidatos_balcao,
            'formulario': formulario,
            'active_tab': active_tab,
            'show_candidatos_section': show_candidatos_section,
        }
        
        return render(request, 'vagas/empresa_vaga_detalhes.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar detalhes da vaga: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_selecionar_candidato(request, vaga_id, candidato_id):
    """Selecionar candidato para uma vaga"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        vaga = get_object_or_404(Vaga_Emprego, id=vaga_id, empresa=empresa)
        candidato = get_object_or_404(Candidato, id=candidato_id, vaga=vaga)
        
        if request.method == 'POST':
            # Marcar candidato como contratado
            candidato.conseguiu_vaga = True
            candidato.save()
            
            # Atualizar vaga como inativa se necessário
            candidatos_contratados = Candidato.objects.filter(vaga=vaga, conseguiu_vaga=True).count()
            vagas_restantes = vaga.quantidadeVagas - candidatos_contratados
            
            if vagas_restantes <= 0:
                vaga.ativo = False
                vaga.dt_desativacao = timezone.now()
                vaga.save()
                messages.success(request, f'Candidato {candidato.nome} selecionado com sucesso! A vaga foi inativada pois todas as posições foram preenchidas.')
            else:
                vaga.save()
                messages.success(request, f'Candidato {candidato.nome} selecionado com sucesso! Restam {vagas_restantes} vaga{"s" if vagas_restantes > 1 else ""} disponíve{"is" if vagas_restantes > 1 else "l"}.')
            return redirect('vagas:empresa_vaga_detalhes', vaga_id=vaga.id)
        
        # Calcular informações das vagas
        candidatos_contratados = Candidato.objects.filter(vaga=vaga, conseguiu_vaga=True).count()
        vagas_restantes = vaga.quantidadeVagas - candidatos_contratados
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vaga': vaga,
            'candidato': candidato,
            'candidatos_contratados': candidatos_contratados,
            'vagas_restantes': vagas_restantes,
        }
        
        return render(request, 'vagas/empresa_selecionar_candidato.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao selecionar candidato: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_encerrar_vaga(request, vaga_id):
    """Solicitar encerramento de vaga"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        vaga = get_object_or_404(Vaga_Emprego, id=vaga_id, empresa=empresa)
        
        # Buscar formulário relacionado (se houver)
        formulario = None
        try:
            formulario = RequisicaoVaga.objects.filter(
                cnpj_da_empresa=empresa.cnpj,
                cargo=vaga.cargo,
                status_requisicao='AP'
            ).first()
        except:
            pass
        
        if request.method == 'POST':
            observacao = request.POST.get('observacao', '')
            
            # Se há formulário, criar solicitação de encerramento
            if formulario:
                # Adicionar observação ao formulário
                data_atual = timezone.now().strftime('%d/%m/%Y %H:%M')
                observacao_completa = f"Solicitação de encerramento em {data_atual} por {responsavel.user.get_full_name() or responsavel.user.username}:\n{observacao}"
                
                if formulario.observacoes_aprovacao:
                    formulario.observacoes_aprovacao += f"\n\n{observacao_completa}"
                else:
                    formulario.observacoes_aprovacao = observacao_completa
                formulario.save()
                
                messages.success(request, 'Solicitação de encerramento enviada com sucesso!')
            else:
                # Para vagas sem formulário, apenas inativar
                vaga.ativo = False
                vaga.observacao = f"{vaga.observacao}\n\nEncerrada em {timezone.now().strftime('%d/%m/%Y %H:%M')}: {observacao}".strip()
                vaga.dt_desativacao = timezone.now()
                vaga.save()
                
                messages.success(request, 'Vaga encerrada com sucesso!')
            
            return redirect('vagas:empresa_vagas')
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vaga': vaga,
            'formulario': formulario,
        }
        
        return render(request, 'vagas/empresa_encerrar_vaga.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao encerrar vaga: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def trocar_empresa(request):
    """View para trocar empresa ativa (via AJAX ou redirecionamento)"""
    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        
        if empresa_id:
            # Verificar se o usuário tem permissão para essa empresa
            try:
                ResponsavelEmpresa.objects.get(
                    user=request.user, 
                    empresa_id=empresa_id, 
                    ativo=True
                )
                # Salvar na session
                request.session['empresa_selecionada'] = empresa_id
                messages.success(request, 'Empresa alterada com sucesso!')
            except ResponsavelEmpresa.DoesNotExist:
                messages.error(request, 'Você não tem permissão para acessar esta empresa.')
    
    # Redirecionar para o dashboard
    return redirect('vagas:dashboard_empresa')


@empresa_user_required
def empresa_candidato_perfil(request, candidato_id):
    """Visualizar perfil de candidato específico para empresas"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Verificar se o candidato pertence a uma vaga da empresa
        candidato = get_object_or_404(Candidato, id=candidato_id, vaga__empresa=empresa)
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'candidato': candidato,
        }
        
        return render(request, 'vagas/empresa_candidato_perfil.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar perfil do candidato: {str(e)}')
        return redirect('vagas:dashboard_empresa')


@empresa_user_required
def empresa_form_add_auxiliar(request):
    """Exibe o formulário para adicionar um novo usuário auxiliar"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        # Verificar se o usuário é responsável principal
        if not responsavel or not responsavel.eh_responsavel_principal():
            messages.error(request, 'Apenas responsáveis principais podem adicionar auxiliares.')
            return redirect('vagas:empresa_perfil')
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
        }
        
        return render(request, 'vagas/empresa_form_add_auxiliar.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao carregar formulário: {str(e)}')
        return redirect('vagas:empresa_perfil')


@empresa_user_required
def empresa_add_auxiliar(request):
    """Adiciona um novo usuário auxiliar à empresa"""
    if request.method != 'POST':
        return redirect('vagas:empresa_form_add_auxiliar')
    
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        # Verificar se o usuário é responsável principal
        if not responsavel or not responsavel.eh_responsavel_principal():
            messages.error(request, 'Apenas responsáveis principais podem adicionar auxiliares.')
            return redirect('vagas:empresa_perfil')
        
        # Obter dados do formulário
        nome = request.POST.get('nome')
        cpf = request.POST.get('cpf')
        email = request.POST.get('email')
        cargo = request.POST.get('cargo')
        telefone = request.POST.get('telefone')
        observacoes = request.POST.get('observacoes', '')
        
        # Limpar CPF (remover pontuação)
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Verificar se já existe um auxiliar com este CPF para esta empresa
        auxiliar_existente = ResponsavelEmpresa.objects.filter(empresa=empresa, cpf=cpf).first()
        
        if auxiliar_existente:
            if auxiliar_existente.ativo:
                messages.warning(request, f'Já existe um auxiliar com este CPF ({cpf}) para esta empresa.')
            else:
                # Se existe mas está inativo, reativar
                auxiliar_existente.ativo = True
                auxiliar_existente.save()
                messages.success(request, 'Auxiliar reativado com sucesso.')
            
            return redirect('vagas:empresa_perfil')
        
        # Criar novo auxiliar
        from django.contrib.auth.models import User, Group
        
        # Verificar se já existe um usuário com este email
        user = User.objects.filter(email=email).first()
        
        if not user:
            # Gerar um nome de usuário único baseado no email
            username = email.split('@')[0]
            base_username = username
            count = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{count}"
                count += 1
            
            # Gerar senha aleatória
            import random
            import string
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            
            # Criar usuário
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=nome.split(' ')[0] if ' ' in nome else nome,
                last_name=' '.join(nome.split(' ')[1:]) if ' ' in nome else '',
            )
            
            # Adicionar ao grupo empresa_user
            try:
                grupo_empresa = Group.objects.get(name='empresa_user')
                user.groups.add(grupo_empresa)
            except Group.DoesNotExist:
                messages.warning(request, 'Grupo empresa_user não encontrado. O usuário foi criado mas não está no grupo correto.')
            
            # Enviar email com as credenciais
            # TODO: Implementar envio de email
        
        # Criar registro de ResponsavelEmpresa
        novo_auxiliar = ResponsavelEmpresa.objects.create(
            empresa=empresa,
            user=user,
            nome=nome,
            cpf=cpf,
            email=email,
            cargo=cargo,
            telefone=telefone,
            nivel='AUX',  # Auxiliar
            ativo=True,
            criado_por=request.user,
            observacoes=observacoes
        )
        
        messages.success(request, f'Auxiliar {nome} adicionado com sucesso!')
        
        return redirect('vagas:empresa_perfil')
        
    except Exception as e:
        messages.error(request, f'Erro ao adicionar auxiliar: {str(e)}')
        return redirect('vagas:empresa_form_add_auxiliar')


@empresa_user_required
def empresa_desativar_auxiliar(request):
    """Desativa um usuário auxiliar da empresa"""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('vagas:empresa_perfil')
    
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        # Verificar se o usuário é responsável principal
        if not responsavel or not responsavel.eh_responsavel_principal():
            messages.error(request, 'Apenas responsáveis principais podem desativar auxiliares.')
            return redirect('vagas:empresa_perfil')
        
        # Obter ID do auxiliar a ser desativado
        auxiliar_id = request.POST.get('responsavel_id')
        
        # Buscar o auxiliar
        auxiliar = get_object_or_404(ResponsavelEmpresa, id=auxiliar_id, empresa=empresa, nivel='AUX')
        
        # Desativar
        auxiliar.ativo = False
        auxiliar.save()
        
        messages.success(request, f'Auxiliar {auxiliar.nome} desativado com sucesso.')
        
        return redirect('vagas:empresa_perfil')
        
    except Exception as e:
        messages.error(request, f'Erro ao desativar auxiliar: {str(e)}')
        return redirect('vagas:empresa_perfil')


@empresa_user_required
def empresa_reativar_auxiliar(request):
    """Reativa um usuário auxiliar da empresa"""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('vagas:empresa_perfil')
    
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        # Verificar se o usuário é responsável principal
        if not responsavel or not responsavel.eh_responsavel_principal():
            messages.error(request, 'Apenas responsáveis principais podem reativar auxiliares.')
            return redirect('vagas:empresa_perfil')
        
        # Obter ID do auxiliar a ser reativado
        auxiliar_id = request.POST.get('responsavel_id')
        
        # Buscar o auxiliar
        auxiliar = get_object_or_404(ResponsavelEmpresa, id=auxiliar_id, empresa=empresa, nivel='AUX')
        
        # Reativar
        auxiliar.ativo = True
        auxiliar.save()
        
        messages.success(request, f'Auxiliar {auxiliar.nome} reativado com sucesso.')
        
        return redirect('vagas:empresa_perfil')
        
    except Exception as e:
        messages.error(request, f'Erro ao reativar auxiliar: {str(e)}')
        return redirect('vagas:empresa_perfil')


@empresa_user_required
def empresa_solicitar_desativacao(request):
    """Solicita desativação de uma vaga"""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('vagas:empresa_formularios')
    
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        # Obter dados do formulário
        vaga_id = request.POST.get('vaga_id')
        formulario_id = request.POST.get('formulario_id')
        motivo = request.POST.get('motivo_desativacao')
        observacoes = request.POST.get('observacoes_desativacao', '')
        
        # Buscar a vaga
        vaga = get_object_or_404(Vaga_Emprego, id=vaga_id, empresa=empresa)
        
        # Criar um novo objeto para registrar a solicitação de desativação
        from django.utils import timezone
        
        # Criar um histórico para a vaga
        # Aqui você pode criar um modelo específico para solicitações de desativação
        # Por enquanto, apenas marcar a vaga como solicitada para desativação
        vaga.solicitacao_desativacao = True
        vaga.motivo_solicitacao_desativacao = motivo
        vaga.observacoes_solicitacao_desativacao = observacoes
        vaga.dt_solicitacao_desativacao = timezone.now()
        vaga.usuario_solicitacao_desativacao = request.user
        vaga.save()
        
        # Enviar notificação para os administradores
        # TODO: Implementar notificação
        
        messages.success(request, 'Solicitação de desativação enviada com sucesso! A equipe da Casa do Trabalhador irá analisar sua solicitação em breve.')
        
        # Redirecionar de volta para os detalhes do formulário
        return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario_id)
        
    except Exception as e:
        messages.error(request, f'Erro ao solicitar desativação: {str(e)}')
        return redirect('vagas:empresa_formularios')


@login_required
@staff_required
def install_demo(request):
    """
    View para popular o banco de dados com dados de demonstração
    """
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    import random
    from django.db import transaction
    
    try:
        with transaction.atomic():
            # Verificar se já existem dados
            if Cargo.objects.count() > 5 or Escolaridade.objects.count() > 5:
                messages.warning(request, 'Sistema já possui dados. Para reinstalar a demo, limpe o banco primeiro.')
                return redirect('vagas:painel_administrativo')
            
            # Criar usuários de demonstração
            demo_users = []
            user_data = [
                {'username': 'admin_demo', 'first_name': 'João', 'last_name': 'Silva', 'email': 'admin@demo.com'},
                {'username': 'rh_demo', 'first_name': 'Maria', 'last_name': 'Santos', 'email': 'rh@demo.com'},
                {'username': 'funcionario_demo', 'first_name': 'Pedro', 'last_name': 'Oliveira', 'email': 'func@demo.com'},
            ]
            
            for user_info in user_data:
                user, created = User.objects.get_or_create(
                    username=user_info['username'],
                    defaults={
                        'first_name': user_info['first_name'],
                        'last_name': user_info['last_name'],
                        'email': user_info['email'],
                        'is_staff': True,
                        'is_active': True
                    }
                )
                if created:
                    user.set_password('demo123')
                    user.save()
                demo_users.append(user)
            
            # Criar escolaridades de demonstração
            escolaridades_demo = [
                'Ensino Fundamental Incompleto',
                'Ensino Fundamental Completo', 
                'Ensino Médio Incompleto',
                'Ensino Médio Completo',
                'Ensino Superior Incompleto',
                'Ensino Superior Completo',
                'Pós-Graduação',
                'Mestrado',
                'Doutorado'
            ]
            
            escolaridades_criadas = []
            for nome in escolaridades_demo:
                escolaridade, created = Escolaridade.objects.get_or_create(
                    nome=nome,
                    defaults={
                        'user': random.choice(demo_users)
                    }
                )
                escolaridades_criadas.append(escolaridade)
            
            # Criar cargos de demonstração
            cargos_demo = [
                'Vendedor',
                'Atendente',
                'Caixa',
                'Auxiliar Administrativo',
                'Recepcionista',
                'Motorista',
                'Auxiliar de Limpeza',
                'Garçom/Garçonete',
                'Cozinheiro(a)',
                'Operador de Telemarketing',
                'Auxiliar de Produção',
                'Estoquista',
                'Técnico em Informática',
                'Auxiliar Contábil',
                'Porteiro',
                'Vigilante',
                'Mecânico',
                'Eletricista',
                'Pedreiro',
                'Soldador'
            ]
            
            cargos_criados = []
            for nome in cargos_demo:
                cargo, created = Cargo.objects.get_or_create(
                    nome=nome,
                    defaults={
                        'user': random.choice(demo_users)
                    }
                )
                cargos_criados.append(cargo)
            
            # Criar empresas de demonstração
            empresas_demo = [
                {
                    'nome': 'Supermercado Central LTDA',
                    'cnpj': '12345678000199',
                    'endereco': 'Rua das Flores, 123',
                    'bairro': 'Centro',
                    'telefone': '11987654321',
                    'email': 'rh@supercentral.com.br'
                },
                {
                    'nome': 'Restaurante Bom Sabor',
                    'cnpj': '98765432000155',
                    'endereco': 'Av. Principal, 456',
                    'bairro': 'Jardim Europa',
                    'telefone': '11876543210',
                    'email': 'contato@bomsabor.com.br'
                },
                {
                    'nome': 'Loja de Roupas Fashion',
                    'cnpj': '45678912000177',
                    'endereco': 'Rua do Comércio, 789',
                    'bairro': 'Vila Nova',
                    'telefone': '11765432109',
                    'email': 'rh@fashion.com.br'
                },
                {
                    'nome': 'Oficina Mecânica São José',
                    'cnpj': '78912345000133',
                    'endereco': 'Rua das Oficinas, 321',
                    'bairro': 'Industrial',
                    'telefone': '11654321098',
                    'email': 'vagas@oficinasjose.com.br'
                },
                {
                    'nome': 'Construtora Edilar',
                    'cnpj': '32165498000111',
                    'endereco': 'Av. dos Engenheiros, 654',
                    'bairro': 'Alphaville',
                    'telefone': '11543210987',
                    'email': 'rh@edilar.com.br'
                }
            ]
            
            empresas_criadas = []
            for empresa_data in empresas_demo:
                empresa, created = Empresa.objects.get_or_create(
                    cnpj=empresa_data['cnpj'],
                    defaults={
                        'nome': empresa_data['nome'],
                        'endereco': empresa_data['endereco'],
                        'bairro': empresa_data['bairro'],
                        'telefone': empresa_data['telefone'],
                        'email': empresa_data['email'],
                        'user': random.choice(demo_users),
                        'contato_email': True,
                        'contato_telefone': True,
                        'ocultar': False
                    }
                )
                empresas_criadas.append(empresa)
            
            # Criar vagas de demonstração
            vagas_demo = [
                {
                    'titulo': 'Vendedor Experiente',
                    'descricao': 'Buscamos vendedor com experiência em varejo para atuar em supermercado. Requisitos: ensino médio completo, experiência mínima de 6 meses.',
                    'salario': 1800.00,
                    'cargo_idx': 0,  # Vendedor
                    'empresa_idx': 0,  # Supermercado
                    'escolaridade_idx': 3  # Ensino Médio Completo
                },
                {
                    'titulo': 'Garçom/Garçonete',
                    'descricao': 'Vaga para garçom/garçonete em restaurante. Experiência desejável mas não obrigatória. Disponibilidade para trabalhar finais de semana.',
                    'salario': 1600.00,
                    'cargo_idx': 7,  # Garçom
                    'empresa_idx': 1,  # Restaurante
                    'escolaridade_idx': 2  # Ensino Médio Incompleto
                },
                {
                    'titulo': 'Atendente de Loja',
                    'descricao': 'Atendente para loja de roupas femininas. Necessário boa comunicação e disponibilidade de horário.',
                    'salario': 1500.00,
                    'cargo_idx': 1,  # Atendente
                    'empresa_idx': 2,  # Loja Fashion
                    'escolaridade_idx': 3  # Ensino Médio Completo
                },
                {
                    'titulo': 'Mecânico Automotivo',
                    'descricao': 'Mecânico com experiência em manutenção preventiva e corretiva de veículos. Conhecimento em sistemas de injeção eletrônica.',
                    'salario': 2500.00,
                    'cargo_idx': 16,  # Mecânico
                    'empresa_idx': 3,  # Oficina
                    'escolaridade_idx': 3  # Ensino Médio Completo
                },
                {
                    'titulo': 'Pedreiro',
                    'descricao': 'Pedreiro experiente para obras residenciais e comerciais. Experiência mínima de 2 anos comprovada.',
                    'salario': 2200.00,
                    'cargo_idx': 18,  # Pedreiro  
                    'empresa_idx': 4,  # Construtora
                    'escolaridade_idx': 1  # Ensino Fundamental Completo
                },
                {
                    'titulo': 'Caixa de Supermercado',
                    'descricao': 'Operador de caixa para supermercado. Experiência com sistemas PDV. Disponibilidade para trabalhar em escalas.',
                    'salario': 1650.00,
                    'cargo_idx': 2,  # Caixa
                    'empresa_idx': 0,  # Supermercado
                    'escolaridade_idx': 3  # Ensino Médio Completo
                },
                {
                    'titulo': 'Auxiliar de Cozinha',
                    'descricao': 'Auxiliar de cozinha para restaurante. Responsável por preparo de alimentos e organização da cozinha.',
                    'salario': 1400.00,
                    'cargo_idx': 8,  # Cozinheiro
                    'empresa_idx': 1,  # Restaurante
                    'escolaridade_idx': 1  # Ensino Fundamental Completo
                }
            ]
            
            for vaga_data in vagas_demo:
                # Calcular data aleatória nos últimos 30 dias
                dias_atras = random.randint(1, 30)
                data_inclusao = timezone.now() - timedelta(days=dias_atras)
                
                vaga = Vaga_Emprego.objects.create(
                    empresa=empresas_criadas[vaga_data['empresa_idx']],
                    cargo=cargos_criados[vaga_data['cargo_idx']],
                    quantidadeVagas=random.randint(1, 3),
                    tipo_de_vaga='NML',  # Padrão
                    escolaridade=escolaridades_criadas[vaga_data['escolaridade_idx']],
                    salario=f"R$ {vaga_data['salario']:.2f}".replace('.', ','),
                    carga_horaria='40 horas semanais',
                    regime='CLT',
                    experiencia=random.choice(['Sim', 'Não', 'Des']),
                    observacao=vaga_data['descricao'],
                    atribuicoes=f"Atribuições para {vaga_data['titulo']}: " + vaga_data['descricao'][:100] + "...",
                    user=random.choice(demo_users),
                    ativo=True,
                    destaque=random.choice([True, False])
                )
                
                # Definir data de inclusão manualmente após a criação
                vaga.dt_inclusao = data_inclusao
                vaga.save()
                
                # Criar alguns candidatos para algumas vagas
                if random.choice([True, False, False]):  # 33% chance
                    nomes_demo = ['Ana Silva', 'Carlos Santos', 'Maria Oliveira', 'João Pereira', 'Fernanda Costa']
                    for i in range(random.randint(1, 3)):
                        nome = random.choice(nomes_demo)
                        cpf_base = f"{random.randint(100, 999)}{random.randint(100, 999)}{random.randint(100, 999)}"
                        
                        candidato = Candidato.objects.create(
                            vaga=vaga,
                            nome=nome + f" {i+1}",
                            cpf=cpf_base + f"{random.randint(10, 99)}",
                            data_nascimento=timezone.now().date() - timedelta(days=random.randint(18*365, 50*365)),
                            sexo=random.choice(['M', 'F']),
                            email=f"{nome.lower().replace(' ', '.')}{i+1}@email.com",
                            celular=f"11{random.randint(900000000, 999999999)}",
                            bairro=random.choice(['Centro', 'Vila Nova', 'Jardim Europa', 'Industrial']),
                            escolaridade=random.choice(escolaridades_criadas),
                            candidato_online=True,
                            dt_inclusao=data_inclusao + timedelta(hours=random.randint(1, 48))
                        )
            
            messages.success(request, f'''
                Demo instalada com sucesso! 📊<br><br>
                <strong>Dados criados:</strong><br>
                • {len(demo_users)} usuários de demonstração<br>
                • {len(escolaridades_criadas)} níveis de escolaridade<br>
                • {len(cargos_criados)} tipos de cargo<br>
                • {len(empresas_criadas)} empresas<br>
                • {len(vagas_demo)} vagas de emprego<br>
                • Candidatos distribuídos aleatoriamente<br><br>
                
                <strong>Usuários criados:</strong><br>
                • admin_demo / demo123<br>
                • rh_demo / demo123<br>
                • funcionario_demo / demo123
            ''')
            
    except Exception as e:
        messages.error(request, f'Erro ao instalar demo: {str(e)}')
    
    return redirect('vagas:painel_administrativo')


@login_required
@user_passes_test(lambda u: u.is_staff)
def buscar_candidato_por_cpf(request):
    """API para buscar dados do último candidato por CPF (apenas para staff)"""
    if request.method == 'GET':
        cpf = request.GET.get('cpf', '').strip()
        
        if not cpf:
            return JsonResponse({'success': False, 'message': 'CPF não fornecido'})
        
        # Limpar CPF (remover pontos, traços, etc.)
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_limpo) != 11:
            return JsonResponse({'success': False, 'message': 'CPF inválido'})
        
        try:
            # Buscar o último candidato com este CPF
            candidato = Candidato.objects.filter(
                cpf__icontains=cpf_limpo
            ).order_by('-dt_inclusao').first()
            
            if candidato:
                # Formatar data de nascimento
                data_nascimento = candidato.data_nascimento.strftime('%Y-%m-%d') if candidato.data_nascimento else ''
                
                data = {
                    'success': True,
                    'candidato': {
                        'nome': candidato.nome,
                        'cpf': candidato.cpf,
                        'data_nascimento': data_nascimento,
                        'sexo': candidato.sexo,
                        'email': candidato.email,
                        'celular': candidato.celular,
                        'bairro': candidato.bairro,
                        'escolaridade': candidato.escolaridade.id if candidato.escolaridade else ''
                    }
                }
                return JsonResponse(data)
            else:
                return JsonResponse({'success': False, 'message': 'Nenhum candidato encontrado com este CPF'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})


# ============================
# SOLICITAÇÕES DE DESATIVAÇÃO
# ============================

@empresa_user_required
def empresa_solicitar_desativacao_vaga(request, vaga_id):
    """Solicitar desativação de uma vaga específica"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        vaga = get_object_or_404(Vaga_Emprego, id=vaga_id, empresa=empresa)
        
        # Verificar se a vaga está ativa
        if not vaga.ativo:
            messages.warning(request, 'Esta vaga já está inativa.')
            return redirect('vagas:empresa_vaga_detalhes', vaga_id=vaga.id)
        
        # Verificar se já existe uma solicitação pendente
        from .models import SolicitacaoDesativacao
        solicitacao_existente = SolicitacaoDesativacao.objects.filter(
            vaga=vaga, 
            status='pendente'
        ).first()
        
        if solicitacao_existente:
            messages.warning(request, 'Já existe uma solicitação de desativação pendente para esta vaga.')
            return redirect('vagas:empresa_vaga_detalhes', vaga_id=vaga.id)
        
        if request.method == 'POST':
            motivo = request.POST.get('motivo')
            observacoes = request.POST.get('observacoes', '')
            
            if not motivo:
                messages.error(request, 'Por favor, selecione um motivo para a solicitação.')
                return render(request, 'vagas/empresa_solicitar_desativacao.html', {
                    'responsavel': responsavel,
                    'empresa': empresa,
                    'empresas_disponiveis': empresas_disponiveis,
                    'vaga': vaga,
                    'tipo': 'vaga'
                })
            
            # Criar a solicitação
            solicitacao = SolicitacaoDesativacao.objects.create(
                vaga=vaga,
                empresa_responsavel=responsavel,
                motivo=motivo,
                observacoes=observacoes
            )
            
            messages.success(request, 'Solicitação de desativação enviada com sucesso!')
            return redirect('vagas:solicitacao_desativacao_sucesso')
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vaga': vaga,
            'tipo': 'vaga'
        }
        
        return render(request, 'vagas/empresa_solicitar_desativacao.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao processar solicitação: {str(e)}')
        return redirect('vagas:home')


@empresa_user_required
def empresa_solicitar_desativacao_formulario(request, formulario_id):
    """Solicitar desativação via formulário"""
    try:
        responsavel, empresa, empresas_disponiveis = get_empresa_selecionada(request)
        
        if not responsavel:
            messages.error(request, 'Você não é responsável por nenhuma empresa.')
            return redirect('vagas:home')
        
        formulario = get_object_or_404(
            RequisicaoVaga, 
            id=formulario_id,
            cnpj_da_empresa=empresa.cnpj
        )
        
        # Verificar se existe vaga vinculada
        vaga_vinculada = formulario.get_vaga()
        if not vaga_vinculada:
            messages.error(request, 'Não há vaga vinculada a este formulário.')
            return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario.id)
        
        # Verificar se a vaga está ativa
        if not vaga_vinculada.ativo:
            messages.warning(request, 'A vaga vinculada a este formulário já está inativa.')
            return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario.id)
        
        # Verificar se já existe uma solicitação pendente
        from .models import SolicitacaoDesativacao
        solicitacao_existente = SolicitacaoDesativacao.objects.filter(
            vaga=vaga_vinculada, 
            status='pendente'
        ).first()
     
        if solicitacao_existente:
            messages.warning(request, 'Já existe uma solicitação de desativação pendente para esta vaga.')
            return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario.id)
        
        if request.method == 'POST':
            motivo = request.POST.get('motivo')
            observacoes = request.POST.get('observacoes', '')
            
            if not motivo:
                messages.error(request, 'Por favor, selecione um motivo para a solicitação.')
                return render(request, 'vagas/empresa_solicitar_desativacao.html', {
                    'responsavel': responsavel,
                    'empresa': empresa,
                    'empresas_disponiveis': empresas_disponiveis,
                    'vaga': vaga_vinculada,
                    'formulario': formulario,
                    'tipo': 'formulario'
                })
            
            # Criar a solicitação
            solicitacao = SolicitacaoDesativacao.objects.create(
                vaga=vaga_vinculada,
                formulario=formulario,
                empresa_responsavel=responsavel,
                motivo=motivo,
                observacoes=observacoes
            )
            
            # Registrar no histórico
            HistoricoRequisicao.objects.create(
                requisicao=formulario,
                acao='OB',  # Observação/Ação
                observacao=f'Solicitação de desativação criada - {solicitacao.get_motivo_display()}' + 
                          (f': {observacoes}' if observacoes else ''),
                usuario=request.user
            )
            
            try:
                vaga_vinculada.status_requisicao = 'AE'            
                vaga_vinculada.save()
            
                formulario.status_requisicao = 'AE'
                formulario.save()
                
                # Registrar mudança de status no histórico
                HistoricoRequisicao.objects.create(
                    requisicao=formulario,
                    acao='ST',  # Status change
                    status_anterior='AP',
                    status_novo='AE',
                    observacao='Status alterado para "Aguardando Encerramento" devido à solicitação de desativação',
                    usuario=request.user
                )

            except:
                pass
     
            messages.success(request, 'Solicitação de desativação enviada com sucesso!')
            return redirect('vagas:solicitacao_desativacao_sucesso')
        
        context = {
            'responsavel': responsavel,
            'empresa': empresa,
            'empresas_disponiveis': empresas_disponiveis,
            'vaga': vaga_vinculada,
            'formulario': formulario,
            'tipo': 'formulario'
        }
        
        return render(request, 'vagas/empresa_solicitar_desativacao.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao processar solicitação: {str(e)}')
        return redirect('vagas:home')


def solicitacao_desativacao_sucesso(request):
    """Página de sucesso após solicitar desativação"""
    return render(request, 'vagas/solicitacao_desativacao_sucesso.html')


@login_required
def admin_solicitacoes_desativacao(request):
    """Lista todas as solicitações de desativação para o admin"""
    if not request.user.is_staff:
        messages.error(request, 'Acesso negado.')
        return redirect('vagas:home')
    
    from .models import SolicitacaoDesativacao
    
    # Filtros
    status_filter = request.GET.get('status', 'pendente')
    
    solicitacoes = SolicitacaoDesativacao.objects.select_related(
        'vaga', 'vaga__cargo', 'vaga__empresa', 'empresa_responsavel', 'formulario'
    ).order_by('-dt_criacao')
    
    if status_filter and status_filter != 'todas':
        solicitacoes = solicitacoes.filter(status=status_filter)
    
    # Estatísticas
    stats = {
        'total': SolicitacaoDesativacao.objects.count(),
        'pendentes': SolicitacaoDesativacao.objects.filter(status='pendente').count(),
        'aprovadas': SolicitacaoDesativacao.objects.filter(status='aprovada').count(),
        'rejeitadas': SolicitacaoDesativacao.objects.filter(status='rejeitada').count(),
    }
    
    context = {
        'solicitacoes': solicitacoes,
        'status_filter': status_filter,
        'stats': stats,
    }
    
    return render(request, 'vagas/admin_solicitacoes_desativacao.html', context)


@login_required
def admin_processar_solicitacao_desativacao(request, solicitacao_id):
    """Processar uma solicitação de desativação específica"""
    if not request.user.is_staff:
        messages.error(request, 'Acesso negado.')
        return redirect('vagas:home')
    
    from .models import SolicitacaoDesativacao
    
    solicitacao = get_object_or_404(SolicitacaoDesativacao, id=solicitacao_id)
    
    if request.method == 'POST':
        acao = request.POST.get('acao')
        observacoes_admin = request.POST.get('observacoes_admin', '')
        
        if acao in ['aprovada', 'rejeitada']:
            try:
                solicitacao.processar(request.user, acao, observacoes_admin)
                
                if acao == 'aprovada':                    
                    messages.success(request, f'Solicitação aprovada! A vaga "{solicitacao.vaga.cargo.nome}" foi desativada.')
                else:
                    messages.success(request, f'Solicitação rejeitada.')
                
                # Redirecionar para a página do formulário se existir, senão para lista de vagas
                if solicitacao.formulario:
                    return redirect('vagas:admin_formularios_detail', id=solicitacao.formulario.pk)
                else:
                    return redirect('vagas:admin_vagas_list')
                
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Ação inválida.')
    
    context = {
        'solicitacao': solicitacao,
    }
    
    return render(request, 'vagas/admin_processar_solicitacao_desativacao.html', context)
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})


@login_required
def admin_toggle_vaga_status(request, vaga_id):
    """Toggle do status ativo/inativo de uma vaga pelo admin"""
    if not request.user.is_staff:
        messages.error(request, 'Acesso negado.')
        return redirect('vagas:home')
    
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('vagas:candidatos_vaga', vaga_id=vaga_id)
    
    vaga = get_object_or_404(Vaga_Emprego, id=vaga_id)
    
    # Alternar o status
    vaga.ativo = not vaga.ativo
    vaga.save()
    
    # Mensagem de sucesso
    if vaga.ativo:
        messages.success(request, f'Vaga "{vaga.cargo.nome}" foi reativada com sucesso.')
    else:
        messages.success(request, f'Vaga "{vaga.cargo.nome}" foi desativada com sucesso.')
    
    # Redirecionar de volta para a página de candidatos
    return redirect('vagas:candidatos_vaga', vaga_id) + '?origem=vagas'


@login_required
@staff_required
def relatorio_anual_excel(request):
    """
    Gera relatório anual em Excel com dados mensais de:
    - Empregados (candidatos que conseguiram vaga)
    - Atendimentos totais
    - Atendimentos por balcão/whatsapp/telefone
    - Empresas cadastradas e novas empresas
    - Vagas disponíveis e entrada de vagas
    """
    from datetime import datetime
    from django.db.models import Count, Q
    from urllib.parse import quote
    
    # Obter ano atual ou do parâmetro
    ano_atual = request.GET.get('ano', datetime.now().year)
    try:
        ano = int(ano_atual)
    except (ValueError, TypeError):
        ano = datetime.now().year
    
    # Criar workbook e planilha
    wb = Workbook()
    ws = wb.active
    ws.title = f"Relatório Anual {ano}"
    
    # Configurar cabeçalhos
    meses = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 
             'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
    
    # Linha 1: Cabeçalhos dos meses
    cabecalho = ['CATEGORIA'] + meses + ['TOTAL TRIMESTRE 1', 'TOTAL TRIMESTRE 2', 
                 'TOTAL TRIMESTRE 3', 'TOTAL TRIMESTRE 4', 'TOTAL ANUAL']
    ws.append(cabecalho)
    
    # Função para calcular dados mensais
    def calcular_dados_mes(mes_num):
        """Calcula todos os dados para um mês específico usando range de datas"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        # Definir range do mês
        inicio_mes = date(ano, mes_num, 1)
        if mes_num == 12:
            fim_mes = date(ano + 1, 1, 1)
        else:
            fim_mes = date(ano, mes_num + 1, 1)
        
        # Para empresas e vagas disponíveis - acumulado até o final do mês
        fim_mes_acumulado = fim_mes
        
        # Candidatos empregados (conseguiu_vaga=True)
        empregados = Candidato.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes],
            conseguiu_vaga=True
        ).count()
        
        # Total de atendimentos (todos os candidatos)
        atendimentos_total = Candidato.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes]
        ).count()
        
        # Atendimentos por balcão (candidato_online=False)
        balcao = Candidato.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes],
            candidato_online=False
        ).count()
        
        # Atendimentos online (candidato_online=True)
        # Dividindo proporcionalmente entre WhatsApp e Telefone
        online = Candidato.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes],
            candidato_online=True
        ).count()
        
        # Estimativa: 70% WhatsApp, 30% Telefone (baseado no padrão dos dados fornecidos)
        whatsapp = int(online * 0.7)
        telefone = online - whatsapp
        
        # Total de empresas no final do mês (acumulado)
        empresas_total = Empresa.objects.filter(
            dt_inclusao__lt=fim_mes_acumulado
        ).count()
        
        # Novas empresas no mês
        novas_empresas = Empresa.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes]
        ).count()
        
        # Entrada de registros no mês
        entrada_registros = Vaga_Emprego.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes]
        ).count()

        #Entrada de vagas no mês
        entrada_vagas = Vaga_Emprego.objects.filter(
            dt_inclusao__range=[inicio_mes, fim_mes]
        ).aggregate(
            total=Sum('quantidadeVagas')
        )['total'] or 0

        # Vagas disponíveis no final do mês (criadas até o final do mês e que estão ativas)
        vagas_disponiveis = Vaga_Emprego.objects.filter(
            dt_inclusao__lt=fim_mes,
            ativo=True
        ).count()
        
        return {
            'empregados': empregados,
            'atendimentos': atendimentos_total,
            'balcao': balcao,
            'whatsapp': 0,
            'telefone': 0,
            'empresas_total': empresas_total,
            'novas_empresas': novas_empresas,
            'entrada_registros': entrada_registros,
            'entrada_vagas': entrada_vagas,
            'vagas_disponiveis': vagas_disponiveis
        }
    
    # Calcular dados para todos os meses
    dados_anuais = {}
    for mes in range(1, 13):
        dados_anuais[mes] = calcular_dados_mes(mes)
    
    # Função para calcular total trimestral
    def total_trimestre(trimestre_num, campo):
        if trimestre_num == 1:
            meses_trim = [1, 2, 3]
        elif trimestre_num == 2:
            meses_trim = [4, 5, 6]
        elif trimestre_num == 3:
            meses_trim = [7, 8, 9]
        else:  # trimestre 4
            meses_trim = [10, 11, 12]
        
        return sum(dados_anuais[m][campo] for m in meses_trim)
    
    # Função para calcular total anual
    def total_anual(campo):
        return sum(dados_anuais[m][campo] for m in range(1, 13))
    
    # Adicionar linhas de dados
    categorias = [
        ('EMPREGADOS', 'empregados'),
        ('ATENDIMENTOS', 'atendimentos'),
        ('BALCÃO', 'balcao'),
        ('WHATSAPP', 'whatsapp'),
        ('TELEFONE', 'telefone'),
        ('EMPRESAS', 'empresas_total'),
        ('NOVAS EMPRESAS', 'novas_empresas'),
        ('ENTRADA DE REGISTROS', 'entrada_registros'),
        ('ENTRADA DE VAGAS', 'entrada_vagas'),
        ('VAGAS DISPONÍVEIS', 'vagas_disponiveis')
    ]
    
    for categoria_nome, campo in categorias:
        linha = [categoria_nome]
        
        # Dados mensais
        for mes in range(1, 13):
            linha.append(dados_anuais[mes][campo])
        
        # Totais trimestrais
        for trimestre in range(1, 5):
            linha.append(total_trimestre(trimestre, campo))
        
        # Total anual
        linha.append(total_anual(campo))
        
        ws.append(linha)
    
    # Ajustar largura das colunas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 15)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Configurar resposta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={quote(f"relatorio_anual_{ano}.xlsx")}'
    
    # Salvar workbook na resposta
    wb.save(response)
    
    return response
