from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from vagas.models import SolicitacaoDesativacao
from vagas.forms.solicitation import ProcessarSolicitacaoForm

@login_required
def admin_solicitacoes_desativacao(request):
    """View to list deactivation requests"""
    # Get all solicitations, ordered by creation date descending
    solicitacoes = SolicitacaoDesativacao.objects.select_related(
        'vaga', 'vaga__empresa', 'empresa_responsavel'
    ).order_by('-dt_criacao')

    # Filter by status if specified
    status = request.GET.get('status', 'pendente')
    if status:
        solicitacoes = solicitacoes.filter(status=status)

    context = {
        'solicitacoes': solicitacoes,
        'status_atual': status,
        'total_pendentes': SolicitacaoDesativacao.objects.filter(status='pendente').count()
    }
    
    return render(request, 'solicitation/admin_solicitacoes_list.html', context)

@login_required
def admin_processar_solicitacao_desativacao(request, solicitacao_id):
    """Process a deactivation request"""
    solicitacao = get_object_or_404(SolicitacaoDesativacao, pk=solicitacao_id)
    
    # Check if solicitation can be processed
    if not solicitacao.pode_ser_processada():
        messages.error(request, "Essa solicitação não pode ser processada.")
        # Redirecionar para detalhes do formulário se existir, senão para lista de vagas
        if solicitacao.formulario:
            return redirect('vagas:admin_formularios_detail', id=solicitacao.formulario.id)
        else:
            return redirect('vagas:admin_vagas_list')

    if request.method == 'POST':
        form = ProcessarSolicitacaoForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']
            observacoes = form.cleaned_data['observacoes']

            try:
                # Process the solicitation
                solicitacao.processar(request.user, status, observacoes)
                
                action = 'aprovada' if status == 'aprovada' else 'rejeitada'
                messages.success(request, f"Solicitação {action} com sucesso!")
                
            except Exception as e:
                messages.error(request, f"Erro ao processar solicitação: {str(e)}")
            
            # Redirecionar para detalhes do formulário se existir, senão para lista de vagas
            if solicitacao.formulario:
                return redirect('vagas:admin_formularios_detail', id=solicitacao.formulario.id)
            else:
                return redirect('vagas:admin_vagas_list')
    else:
        # Se for GET, redirecionar para o local apropriado
        if solicitacao.formulario:
            return redirect('vagas:admin_formularios_detail', id=solicitacao.formulario.id)
        else:
            return redirect('vagas:admin_vagas_list')