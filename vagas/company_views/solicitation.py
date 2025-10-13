from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from vagas.models import SolicitacaoDesativacao, Vaga_Emprego, ResponsavelEmpresa, RequisicaoVaga
from vagas.forms_backup.solicitation import SolicitarDesativacaoForm

def empresa_solicitar_desativacao_vaga(request, vaga_id):
    """View for companies to request deactivation of a job posting"""
    vaga = get_object_or_404(Vaga_Emprego, pk=vaga_id)

    # Check if user is responsible for the company
    try:
        responsavel = ResponsavelEmpresa.objects.get(
            user=request.user,
            empresa=vaga.empresa,
            ativo=True
        )
    except ResponsavelEmpresa.DoesNotExist:
        messages.error(request, "Você não tem permissão para solicitar a desativação desta vaga.")
        return redirect('vagas:empresa_vagas')

    # Check if there's already a pending deactivation request
    solicitacao_existente = SolicitacaoDesativacao.objects.filter(
        vaga=vaga,
        status='pendente'
    ).exists()

    if solicitacao_existente:
        messages.warning(request, "Já existe uma solicitação de desativação pendente para esta vaga.")
        return redirect('vagas:empresa_vaga_detalhes', vaga_id=vaga.id)

    if request.method == 'POST':
        form = SolicitarDesativacaoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.vaga = vaga
            solicitacao.empresa_responsavel = responsavel
            solicitacao.save()

            messages.success(request, "Solicitação de desativação enviada com sucesso!")
            return redirect('vagas:solicitacao_desativacao_sucesso')
    else:
        form = SolicitarDesativacaoForm()

    context = {
        'vaga': vaga,
        'form': form,
    }
    return render(request, 'solicitation/empresa_solicitar_desativacao.html', context)

def empresa_solicitar_desativacao_formulario(request, formulario_id):
    """View for companies to request deactivation of a job form"""
    formulario = get_object_or_404(RequisicaoVaga, pk=formulario_id)

    # Get linked job posting if it exists
    vaga = formulario.get_vaga()
    if not vaga:
        messages.error(request, "Não foi encontrada uma vaga ativa vinculada a este formulário.")
        return redirect('vagas:empresa_formularios')

    # Check if user is responsible for the company
    try:
        responsavel = ResponsavelEmpresa.objects.get(
            user=request.user,
            empresa=vaga.empresa,
            ativo=True
        )
    except ResponsavelEmpresa.DoesNotExist:
        messages.error(request, "Você não tem permissão para solicitar a desativação desta vaga.")
        return redirect('vagas:empresa_formularios')

    # Check if there's already a pending deactivation request
    solicitacao_existente = SolicitacaoDesativacao.objects.filter(
        vaga=vaga,
        status='pendente'
    ).exists()

    if solicitacao_existente:
        messages.warning(request, "Já existe uma solicitação de desativação pendente para esta vaga.")
        return redirect('vagas:empresa_formulario_detalhes', formulario_id=formulario.id)

    if request.method == 'POST':
        form = SolicitarDesativacaoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.vaga = vaga
            solicitacao.formulario = formulario
            solicitacao.empresa_responsavel = responsavel
            solicitacao.save()

            # Alterar o status do formulário para "Aguardando Encerramento"
            formulario.status_requisicao = 'AE'
            formulario.save()

            # Adicionar entrada no histórico
            from ..models import HistoricoFormulario
            HistoricoFormulario.objects.create(
                formulario=formulario,
                acao='ST',  # Status change
                status_anterior=formulario.status_requisicao if formulario.status_requisicao != 'AE' else 'AP',
                status_novo='AE',
                observacao=f'Solicitação de desativação criada: {solicitacao.get_motivo_display()}',
                usuario=request.user
            )

            messages.success(request, "Solicitação de desativação enviada com sucesso!")
            return redirect('vagas:solicitacao_desativacao_sucesso')
    else:
        form = SolicitarDesativacaoForm()

    context = {
        'formulario': formulario,
        'vaga': vaga,
        'form': form,
    }
    return render(request, 'solicitation/empresa_solicitar_desativacao.html', context)

def empresa_solicitacoes_desativacao(request):
    """View for companies to list their deactivation requests"""
    # Get all requests for companies where user is responsible
    responsaveis = ResponsavelEmpresa.objects.filter(user=request.user, ativo=True)
    empresas = [r.empresa for r in responsaveis]
    
    solicitacoes = SolicitacaoDesativacao.objects.filter(
        vaga__empresa__in=empresas
    ).select_related(
        'vaga', 'vaga__empresa', 'empresa_responsavel', 'processado_por'
    ).order_by('-dt_criacao')

    # Filter by status if specified
    status = request.GET.get('status')
    if status:
        solicitacoes = solicitacoes.filter(status=status)

    context = {
        'solicitacoes': solicitacoes,
        'status_atual': status,
    }
    
    return render(request, 'solicitation/empresa_solicitacoes_list.html', context)

def solicitacao_desativacao_sucesso(request):
    """Simple success view after submitting a deactivation request"""
    return render(request, 'solicitation/solicitacao_sucesso.html')