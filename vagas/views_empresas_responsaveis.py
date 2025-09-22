@login_required
@staff_required
def empresas_responsaveis(request):
    """View para listar empresas e seus respectivos responsáveis."""
    empresas = Empresa.objects.all().prefetch_related('responsaveis').order_by('nome')
    
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