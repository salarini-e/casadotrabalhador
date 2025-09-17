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
from django.db.models import Sum, Count
from django.utils import timezone
from django.conf import settings

from openpyxl import Workbook
from openpyxl.styles import Alignment
from urllib.parse import quote

from .models import Slide, Vaga_Emprego, CandidatoSelecionado
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
        ws.append([vaga.id, vaga.empresa.nome, vaga.cargo.nome, vaga.quantidadeVagas, str(vaga.dt_inclusao), vaga.empresa.telefone, vaga.empresa.whatsapp, vaga.empresa.email])

    # Criar uma resposta HTTP
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename={quote("vagas_ativas.xlsx")}'

    # Salvar o conteúdo do arquivo Excel na resposta
    wb.save(response)

    return response


def visualizar_vaga(request, id):
    if request.method == 'POST':
        if request.user.is_staff:
            gambiarra = {}
            for item in request.POST:
                if item == 'vaga':
                    gambiarra[item] = Cargo.objects.get(nome=request.POST[item]).id
                elif item == 'empresa':
                    gambiarra[item] = Empresa.objects.get(
                        nome=request.POST[item]).id
                else:
                    gambiarra[item] = request.POST[item]
            form = CadastroVagasForm(gambiarra)
            vaga = Vaga_Emprego.objects.get(id=id)
            if form.is_valid():

                form = CadastroVagasForm(gambiarra, instance=vaga)
                form.save()
                return redirect('vagas:vagas')
    else:
        vaga = Vaga_Emprego.objects.get(id=id)
        form = CadastroVagasForm(instance=vaga)

    if request.user.is_staff:
        import datetime
        data_atual = datetime.datetime.now()        
        context = {
            'visualizar': True,
            'mes': data_atual.month,
            'ano': data_atual.year,
            'id': id,
            'tipo_cadastro': '',
            'form': form,
            'hidden': ['user', 'ativo', 'destaque', 'dt_atualizacao'],
            'cargo': vaga.cargo.nome,
            'empresa': vaga.empresa.nome
        }
    else:
        context = {
            'visualizar': True,
            'id': id,
            'tipo_cadastro': '',
            'form': form,
            'hidden': ['user', 'ativo', 'destaque', 'empresa', 'dt_atualizacao'],
            'cargo': vaga.cargo.nome,
            'empresa': vaga.empresa.nome
        }

    return render(request, 'vagas/cadastrar_vagaOfertada.html', context)

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
        form = Form_Empresa(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            context = {
                'tipo_cadastro': 'Alterar',
                'form': Form_Empresa(initial={'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Vaga alterada com sucesso!']
            }
            return redirect('vagas:empresas')
    else:

        form = Form_Empresa(instance=empresa)
    context = {
        'form': form,
        'tipo_cadastro': 'Alterar',
    }
    return render(request, 'vagas/cadastrar_empresa.html', context)


@login_required
@staff_required
def cadastrar_cargo(request):
    if request.method == 'POST':
        form = Form_Cargo(request.POST)
        if form.is_valid():
            form.save()
            context = {
                'tipo_cadastro': 'Cadastrar',
                'form': Form_Cargo(initial={'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Vaga cadastrada com sucesso!']
            }
            return render(request, 'vagas/cadastrar_cargo.html', context)
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
            context = {
                'tipo_cadastro': 'Alterar',
                'form': Form_Cargo(initial={'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Vaga alterada com sucesso!']
            }
            return redirect('vagas:listar_cargos')
    else:

        form = Form_Cargo(instance=cargo)
    context = {
        'form': form,
        'tipo_cadastro': 'Alterar',
    }
    return render(request, 'vagas/cadastrar_escolaridade.html', context)


@login_required
@staff_required
def cadastrar_escolaridade(request):
    if request.method == 'POST':
        form = Form_Escolaridade(request.POST)
        if form.is_valid():
            form.save()
            context = {
                'tipo_cadastro': 'Cadastrar',
                'form': Form_Escolaridade(initial={'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Vaga cadastrada com sucesso!']
            }
            return render(request, 'vagas/cadastrar_escolaridade.html', context)
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
            context = {
                'tipo_cadastro': 'Alterar',
                'form': Form_Escolaridade(initial={'user': request.user}),
                'hidden': ['user', 'ativo'],
                'success': [True, 'Vaga alterada com sucesso!']
            }
            return redirect('vagas:escolaridades')
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
        'vagas': Cargo.objects.all()
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
    context = {
        'vaga': candidato.vaga,
        'date': today,
        'candidato': candidato,
        'sistema': True,
        'user': user
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
    if request.user.is_staff:
        form = Form_Candidato(initial={'vaga': id, 'candidato_online': False})
        pessoa = {'nome': '', 'cpf': '', 'email': '', 'celular': ''}
        print('usuário staff')
    else:
        print('usuário normal')
        if request.user.is_authenticated:
            pessoa = Pessoa.objects.get(user=request.user)
            form = Form_Candidato(initial={'vaga': id, 'candidato_online': True, 'nome': pessoa.nome, 'cpf': pessoa.cpf, 'email': pessoa.email, 'celular': pessoa.telefone})
        elif request.user.is_anonymous:
            form = Form_Candidato(initial={'vaga': id, 'candidato_online': True})

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

        candidatos_interval = Candidato.objects.filter(dt_inclusao__range=(date, end_date))

    else: 
        candidatos_interval = Candidato.objects.all()

    for i in usuarios:
        lista.append([i.first_name, len(
            candidatos_interval.filter(funcionario_encaminhamento=i)), i.id])
        
    context = {
        'lista': lista,
        'mes': month,
        'ano': year
    }

    return render(request, 'vagas/indicadores_candidatos_por_funcionarios.html', context)


@login_required
@staff_required
def funcionario_encaminhados(request, id):
    candidatos = Candidato.objects.filter(funcionario_encaminhamento=id)
    paginator = Paginator(candidatos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_obj.page_range = paginator.page_range

    context = {
        'candidatos': page_obj,
        'fulano': User.objects.get(id=id).first_name,
        'id': id
    }

    return render(request, 'vagas/candidatos_por_funcionarios_detalhe.html', context)


@login_required
def sair(request):
    if request.user.is_authenticated:
        logout(request)
        return redirect('vagas:home')
    else:
        return redirect('/accounts/login')


@login_required
@staff_required
def painel_administrativo(request):
    from django.db.models import Count, Sum, Avg, Q, F, Case, When, IntegerField
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    import calendar
    
    # Estatísticas gerais
    total_vagas_ativas = Vaga_Emprego.objects.filter(ativo=True).count()
    total_posicoes_abertas = Vaga_Emprego.objects.filter(ativo=True).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
    total_empresas_ativas = Empresa.objects.filter(vaga_emprego__ativo=True).distinct().count()
    total_candidatos = Candidato.objects.count()
    candidatos_online = Candidato.objects.filter(candidato_online=True).count()
    candidatos_balcao = Candidato.objects.filter(candidato_online=False).count()
    
    # Estatísticas do mês atual
    hoje = datetime.now()
    inicio_mes = datetime(hoje.year, hoje.month, 1)
    candidatos_mes = Candidato.objects.filter(dt_inclusao__gte=inicio_mes).count()
    vagas_mes = Vaga_Emprego.objects.filter(dt_inclusao__gte=inicio_mes).count()
    
    # Data para últimos 31 dias
    ultimos_31_dias = hoje - timedelta(days=31)
    
    # === NOVAS MÉTRICAS AVANÇADAS ===
    
    # 1. TEMPO MÉDIO DE APROVAÇÃO DE FORMULÁRIOS
    formularios_aprovados = RequisicaoVaga.objects.filter(
        status_requisicao='AP'
    ).exclude(dt_atualizacao__isnull=True)
    
    tempo_medio_aprovacao = 0
    if formularios_aprovados.exists():
        total_tempo = sum([
            (f.dt_atualizacao - f.dt_inclusao).total_seconds() / 3600  # em horas
            for f in formularios_aprovados 
            if f.dt_atualizacao and f.dt_inclusao
        ])
        tempo_medio_aprovacao = total_tempo / formularios_aprovados.count() if formularios_aprovados.count() > 0 else 0
    
    # 2. FUNIL DE CONVERSÃO: Vagas → Candidatos → Contratações
    total_vagas_criadas = Vaga_Emprego.objects.count()
    total_candidatos_sistema = Candidato.objects.count()
    total_contratacoes = Candidato.objects.filter(conseguiu_vaga=True).count()
    
    # Taxa de candidatos por vaga
    taxa_candidatos_por_vaga = total_candidatos_sistema / total_vagas_criadas if total_vagas_criadas > 0 else 0
    
    # Taxa de contratação
    taxa_contratacao = (total_contratacoes / total_candidatos_sistema * 100) if total_candidatos_sistema > 0 else 0
    
    # 3. QUALIDADE DOS SERVIÇOS
    
    # Taxa de preenchimento de vagas (vagas que têm pelo menos 1 candidato contratado)
    vagas_com_contratacao = Vaga_Emprego.objects.filter(candidato__conseguiu_vaga=True).distinct().count()
    taxa_preenchimento_vagas = (vagas_com_contratacao / total_vagas_criadas * 100) if total_vagas_criadas > 0 else 0
    
    # Satisfação das empresas (baseado em renovações/novos formulários)
    empresas_com_multiplos_formularios = RequisicaoVaga.objects.values('cnpj_da_empresa').annotate(
        total_formularios=Count('id')
    ).filter(total_formularios__gt=1).count()
    
    total_empresas_formularios = RequisicaoVaga.objects.values('cnpj_da_empresa').distinct().count()
    taxa_renovacao_empresas = (empresas_com_multiplos_formularios / total_empresas_formularios * 100) if total_empresas_formularios > 0 else 0
    
    # Percentual de candidatos que conseguiram vaga
    percentual_candidatos_contratados = taxa_contratacao
    
    # 4. ANÁLISES TEMPORAIS
    
    # Sazonalidade de vagas por setor (últimos 12 meses)
    doze_meses_atras = hoje - timedelta(days=365)
    vagas_por_cargo_mes = []
    
    top_cargos = Cargo.objects.annotate(
        total_vagas=Count('vaga_emprego')
    ).order_by('-total_vagas')[:5]
    
    for cargo in top_cargos:
        vagas_mes_cargo = []
        for i in range(12):
            mes_inicio = hoje.replace(day=1) - relativedelta(months=i)
            mes_fim = mes_inicio + relativedelta(months=1)
            total_mes = Vaga_Emprego.objects.filter(
                cargo=cargo,
                dt_inclusao__gte=mes_inicio,
                dt_inclusao__lt=mes_fim
            ).count()
            vagas_mes_cargo.append({
                'mes': mes_inicio.strftime('%m/%Y'),
                'total': total_mes
            })
        vagas_por_cargo_mes.append({
            'cargo': cargo.nome,
            'dados': list(reversed(vagas_mes_cargo))
        })
    
    # Picos de demanda por mês (candidatos)
    picos_demanda_candidatos = []
    for i in range(12):
        mes_inicio = hoje.replace(day=1) - relativedelta(months=i)
        mes_fim = mes_inicio + relativedelta(months=1)
        total_candidatos_mes = Candidato.objects.filter(
            dt_inclusao__gte=mes_inicio,
            dt_inclusao__lt=mes_fim
        ).count()
        picos_demanda_candidatos.append({
            'mes': mes_inicio.strftime('%m/%Y'),
            'total': total_candidatos_mes
        })
    picos_demanda_candidatos.reverse()
    
    # Ciclo de vida médio das vagas (tempo entre criação e desativação)
    vagas_desativadas = Vaga_Emprego.objects.filter(
        ativo=False,
        dt_desativacao__isnull=False
    )
    
    ciclo_vida_medio = 0
    if vagas_desativadas.exists():
        total_dias = sum([
            (v.dt_desativacao - v.dt_inclusao).days 
            for v in vagas_desativadas
            if v.dt_desativacao and v.dt_inclusao
        ])
        ciclo_vida_medio = total_dias / vagas_desativadas.count() if vagas_desativadas.count() > 0 else 0
    
    # 5. MAPA DE CALOR GEOGRÁFICO (por bairros)
    candidatos_por_bairro = Candidato.objects.exclude(
        Q(bairro__isnull=True) | Q(bairro__exact='')
    ).values('bairro').annotate(
        total=Count('id')
    ).order_by('-total')[:20]  # Top 20 bairros
    
    # Estatísticas dos últimos 31 dias
    vagas_ativas_31_dias = Vaga_Emprego.objects.filter(ativo=True, dt_inclusao__gte=ultimos_31_dias).count()
    posicoes_abertas_31_dias = Vaga_Emprego.objects.filter(ativo=True, dt_inclusao__gte=ultimos_31_dias).aggregate(Sum('quantidadeVagas'))['quantidadeVagas__sum'] or 0
    empresas_ativas_31_dias = Empresa.objects.filter(vaga_emprego__ativo=True, vaga_emprego__dt_inclusao__gte=ultimos_31_dias).distinct().count()
    candidatos_31_dias = Candidato.objects.filter(dt_inclusao__gte=ultimos_31_dias).count()
    
    # Top 5 cargos mais procurados (total)
    top_cargos_total = Candidato.objects.values('vaga__cargo__nome').annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    # Top 5 cargos mais procurados (últimos 31 dias)
    top_cargos_31_dias = Candidato.objects.filter(
        dt_inclusao__gte=ultimos_31_dias
    ).values('vaga__cargo__nome').annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    # Top 10 empresas com mais vagas (total)
    top_empresas_total = Vaga_Emprego.objects.filter(ativo=True).values('empresa__nome').annotate(
        total=Sum('quantidadeVagas')
    ).order_by('-total')[:10]
    
    # Top 10 empresas com mais vagas (últimos 31 dias)
    top_empresas_31_dias = Vaga_Emprego.objects.filter(
        ativo=True, 
        dt_inclusao__gte=ultimos_31_dias
    ).values('empresa__nome').annotate(
        total=Sum('quantidadeVagas')
    ).order_by('-total')[:10]
    
    # Candidatos online vs balcão (total)
    candidatos_online_total = candidatos_online
    candidatos_balcao_total = candidatos_balcao
    
    # Candidatos online vs balcão (últimos 31 dias)
    candidatos_online_31_dias = Candidato.objects.filter(
        candidato_online=True, 
        dt_inclusao__gte=ultimos_31_dias
    ).count()
    candidatos_balcao_31_dias = Candidato.objects.filter(
        candidato_online=False, 
        dt_inclusao__gte=ultimos_31_dias
    ).count()
    
    # Distribuição por escolaridade
    escolaridade_stats = Candidato.objects.values('escolaridade__nome').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Candidatos por mês (últimos 13 meses)
    candidatos_por_mes = []
    data_atual = datetime.now()
    
    for i in range(13):
        # Calcula o mês de referência
        if data_atual.month - i > 0:
            mes = data_atual.month - i
            ano = data_atual.year
        else:
            mes = 12 + (data_atual.month - i)
            ano = data_atual.year - 1
            
        data_inicio = datetime(ano, mes, 1)
        
        # Calcula o fim do mês
        if mes == 12:
            data_fim = datetime(ano + 1, 1, 1)
        else:
            data_fim = datetime(ano, mes + 1, 1)
        
        count = Candidato.objects.filter(dt_inclusao__gte=data_inicio, dt_inclusao__lt=data_fim).count()
        candidatos_por_mes.append({
            'mes': data_inicio.strftime('%m/%Y'),
            'total': count
        })
    
    candidatos_por_mes.reverse()
    
    
    
    context = {
        'total_vagas_ativas': total_vagas_ativas,
        'total_posicoes_abertas': total_posicoes_abertas,
        'total_empresas_ativas': total_empresas_ativas,
        'total_candidatos': total_candidatos,
        'candidatos_online': candidatos_online,
        'candidatos_balcao': candidatos_balcao,
        'candidatos_mes': candidatos_mes,
        'vagas_mes': vagas_mes,
        
        # Dados dos últimos 31 dias
        'vagas_ativas_31_dias': vagas_ativas_31_dias,
        'posicoes_abertas_31_dias': posicoes_abertas_31_dias,
        'empresas_ativas_31_dias': empresas_ativas_31_dias,
        'candidatos_31_dias': candidatos_31_dias,
        
        # Dados para gráficos comparativos
        'top_cargos_total': top_cargos_total,
        'top_cargos_31_dias': top_cargos_31_dias,
        'top_empresas_total': top_empresas_total,
        'top_empresas_31_dias': top_empresas_31_dias,
        'candidatos_online_total': candidatos_online_total,
        'candidatos_balcao_total': candidatos_balcao_total,
        'candidatos_online_31_dias': candidatos_online_31_dias,
        'candidatos_balcao_31_dias': candidatos_balcao_31_dias,
        
        'escolaridade_stats': escolaridade_stats,
        'candidatos_por_mes': candidatos_por_mes,
        
        # === NOVAS MÉTRICAS AVANÇADAS ===
        
        # Métricas de aprovação e funil
        'tempo_medio_aprovacao': round(tempo_medio_aprovacao, 1),
        'taxa_candidatos_por_vaga': round(taxa_candidatos_por_vaga, 1),
        'taxa_contratacao': round(taxa_contratacao, 1),
        'total_contratacoes': total_contratacoes,
        
        # Qualidade dos serviços
        'taxa_preenchimento_vagas': round(taxa_preenchimento_vagas, 1),
        'taxa_renovacao_empresas': round(taxa_renovacao_empresas, 1),
        'percentual_candidatos_contratados': round(percentual_candidatos_contratados, 1),
        'vagas_com_contratacao': vagas_com_contratacao,
        'empresas_com_multiplos_formularios': empresas_com_multiplos_formularios,
        
        # Análises temporais
        'vagas_por_cargo_mes': vagas_por_cargo_mes,
        'picos_demanda_candidatos': picos_demanda_candidatos,
        'ciclo_vida_medio': round(ciclo_vida_medio, 1),
        
        # Mapa de calor geográfico
        'candidatos_por_bairro': candidatos_por_bairro,
        
        # Estatísticas de formulários
        'total_formularios': RequisicaoVaga.objects.count(),
        'formularios_aprovados': RequisicaoVaga.objects.filter(status_requisicao='AP').count(),
        'formularios_pendentes': RequisicaoVaga.objects.filter(status_requisicao__in=['AG', 'PE']).count(),
        'formularios_rejeitados': RequisicaoVaga.objects.filter(status_requisicao='RE').count(),
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

        
    context = {
        'top_x': top_x,
        'top_cargos_ofertados': cargos_ofertados[:top_x],
        'escolaridades': escolaridades_quantidades,
        'candidatos_por_mes': candidatos_por_mes,
        'vagas_por_empresa': vagas_por_empresa[:top_x],
        'vagas_cadastradas_por_mes': vagas_cadastradas_por_mes,
        'relacao_online_balcao': relacao_online_balcao
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
                pass

            candidato = form.save()
            
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
        vagas = Vaga_Emprego.objects.filter(ativo=False).select_related('empresa', 'cargo').order_by('-dt_inclusao')
        page_title = "Vagas Inativas"
    else:
        vagas = Vaga_Emprego.objects.filter(ativo=True).select_related('empresa', 'cargo').order_by('-dt_inclusao')
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
    
    if vaga_vinculada:
        candidatos_selecionados = CandidatoSelecionado.objects.filter(requisicao_vaga=requisicao)
        candidatos_selecionados_cpfs = list(candidatos_selecionados.values_list('cpf', flat=True))
        
        # Buscar pessoas que se candidataram a esta vaga
        # Primeiro, buscar os candidatos do modelo Candidato
        candidatos_modelo = Candidato.objects.filter(vaga=vaga_vinculada)
        
        # Depois buscar as pessoas correspondentes no modelo Pessoa
        from autenticacao.models import Pessoa
        cpfs_candidatos = candidatos_modelo.values_list('cpf', flat=True)
        candidatos_da_vaga = Pessoa.objects.filter(cpf__in=cpfs_candidatos)
    
    context = {
        'requisicao': requisicao,
        'vaga_vinculada': vaga_vinculada,
        'candidatos_selecionados': candidatos_selecionados,
        'candidatos_selecionados_cpfs': candidatos_selecionados_cpfs,
        'candidatos_da_vaga': candidatos_da_vaga,
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
        models.Q(nome__icontains=requisicao.nome_da_empresa) |
        models.Q(cnpj=requisicao.cnpj_da_empresa)
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
    candidatos_online = candidatos.filter(origem_cadastro='online').count()
    candidatos_balcao = candidatos.filter(origem_cadastro='balcao').count()
    
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
    
    import json
    data = json.loads(request.body)
    motivo = data.get('motivo', 'Solicitação de encerramento via interface externa')
    
    try:
        # Mudar status para "Aguardando Encerramento"
        status_anterior = requisicao.status_requisicao
        requisicao.status_requisicao = 'AE'
        
        # Criar entrada no histórico
        from .models import HistoricoRequisicao
        HistoricoRequisicao.objects.create(
            requisicao=requisicao,
            acao='ST',  # Status
            status_anterior=status_anterior,
            status_novo='AE',
            observacao=f'SOLICITAÇÃO DE ENCERRAMENTO: {motivo}',
            usuario=None  # Empresa externa
        )
        
        # Adicionar observação interna na requisição
        observacao_atual = requisicao.observacao_interna or ''
        nova_observacao = f'{observacao_atual}\n\n[{timezone.now().strftime("%d/%m/%Y %H:%M")}] EMPRESA SOLICITOU ENCERRAMENTO: {motivo}'
        requisicao.observacao_interna = nova_observacao.strip()
        requisicao.save()
        
        return JsonResponse({'success': True, 'message': 'Solicitação de encerramento registrada com sucesso'})
        
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
            vaga.quantidadeVagas = int(request.POST.get('quantidade_vagas', vaga.quantidadeVagas))
            vaga.observacao = request.POST.get('observacao', vaga.observacao)
            vaga.ativo = request.POST.get('ativo') == 'on'
            
            # Atualizar cargo se fornecido
            cargo_id = request.POST.get('cargo_id')
            if cargo_id:
                try:
                    from curriculo.models import Cargo
                    cargo = Cargo.objects.get(pk=cargo_id)
                    vaga.cargo = cargo
                except Cargo.DoesNotExist:
                    pass
            
            vaga.dt_atualizacao = timezone.now()
            vaga.save()
            
            messages.success(request, 'Vaga atualizada com sucesso!')
            return redirect('vagas:candidatos_vaga', vaga_id=vaga.id)
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar vaga: {str(e)}')
    
    # Buscar todos os cargos para o dropdown
    from curriculo.models import Cargo
    cargos = Cargo.objects.all().order_by('nome')
    
    # Estatísticas da vaga para o contexto
    candidatos = Candidato.objects.filter(vaga=vaga)
    total_candidatos = candidatos.count()
    candidatos_contratados = candidatos.filter(conseguiu_vaga=True).count()
    
    context = {
        'vaga': vaga,
        'cargos': cargos,
        'total_candidatos': total_candidatos,
        'candidatos_contratados': candidatos_contratados,
    }
    
    return render(request, 'vagas/editar_vaga.html', context)