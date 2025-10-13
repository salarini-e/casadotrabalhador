from django.contrib import admin
from .models import *


# Register your models here.

@admin.register(Vaga_Emprego)
class VagaEmpregoAdmin(admin.ModelAdmin):
    list_display = (
        'cargo',
        'empresa',
        'tipo_de_vaga',
        'escolaridade',
        'quantidadeVagas',
        'salario',
        'experiencia',
        'ativo',
        'destaque',
        'dt_inclusao',
        'dt_atualizacao',
    )
    list_filter = (
        'empresa',
        'cargo',
        'tipo_de_vaga',
        'escolaridade',
        'experiencia',
        'ativo',
        'destaque',
        'dt_inclusao',
        'dt_atualizacao',
    )
    search_fields = (
        'empresa__nome',
        'cargo__nome',
        'email',
        'observacao',
        'atribuicoes',
    )

    list_editable = ('ativo', 'destaque')
    
    # Ordenação padrão: mais recentemente atualizadas primeiro, depois por data de inclusão
    ordering = ('-dt_atualizacao', '-dt_inclusao')
    
    readonly_fields = ('dt_inclusao', 'dt_atualizacao')

    fieldsets = (
        ('Informações da vaga', {
            'fields': (
                'empresa',
                'cargo',
                'quantidadeVagas',
                'tipo_de_vaga',
                'escolaridade',
                'salario',
                'carga_horaria',
                'regime',
                'experiencia',
            )
        }),
        ('Detalhes adicionais', {
            'fields': (
                'observacao',
                'atribuicoes',
                'email',
                'banner_img',
                'destaque',
                'ativo',
            )
        }),
        ('Controle de datas e usuário', {
            'fields': (
                'user',
                'dt_inclusao',
                'dt_atualizacao',
                'dt_desativacao',
                'requisicao_vaga',
            )
        }),
    )


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'telefone', 'email', 'ocultar')
    list_filter = ('ocultar', 'contato_presencial', 'contato_email', 'contato_telefone', 'contato_whatsapp', 'contato_link')
    search_fields = ('nome', 'cnpj', 'email', 'observacao')
    
    fieldsets = (
        ('Informações da Empresa', {
            'fields': (
                'nome',
                'cnpj',
                'endereco',
                'bairro',
            )
        }),
        ('Contatos', {
            'fields': (
                'telefone',
                'whatsapp',
                'email',
                'link',
            )
        }),
        ('Opções de Contato', {
            'fields': (
                'ocultar',
                'contato_presencial',
                'contato_email',
                'contato_telefone',
                'contato_whatsapp',
                'contato_link',
            )
        }),
        ('Observações', {
            'fields': (
                'observacao',
            )
        }),
        ('Controle', {
            'fields': (
                'user',
                'dt_inclusao',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('dt_inclusao',)

@admin.register(ResponsavelEmpresa)
class ResponsavelEmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'cpf', 'cargo', 'telefone', 'ativo')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome', 'cpf', 'email', 'cargo')
    
    fieldsets = (
        ('Vínculo', {
            'fields': (
                'empresa',
                'user',
            )
        }),
        ('Informações do Responsável', {
            'fields': (
                'nome',
                'cpf',
                'cargo',
                'telefone',
                'email',
            )
        }),
        ('Status', {
            'fields': (
                'ativo',
                'observacoes',
            )
        }),
        ('Controle', {
            'fields': (
                'criado_por',
                'dt_criacao',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('dt_criacao',)

admin.site.register(Escolaridade)
admin.site.register(Cargo)

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'vaga', 'escolaridade', 'candidato_online', 'dt_inclusao', 'dt_atualizacao')
    list_filter = ('candidato_online', 'escolaridade', 'vaga__cargo', 'dt_inclusao', 'dt_atualizacao')
    search_fields = ('nome', 'cpf', 'email', 'celular', 'vaga__cargo__nome', 'vaga__empresa__nome')
    date_hierarchy = 'dt_inclusao'
    
    # Ordenação padrão: mais recentemente atualizados primeiro
    ordering = ('-dt_atualizacao', '-dt_inclusao')
    
    readonly_fields = ('dt_inclusao', 'dt_atualizacao')

admin.site.register(Slide)
@admin.register(RequisicaoVaga)
class RequisicaoVagaAdmin(admin.ModelAdmin):
    list_display = ('cargo_ofertado', 'nome_da_empresa', 'cnpj_da_empresa', 'quantidade_de_vagas', 'status_requisicao', 'dt_inclusao', 'dt_atualizacao')
    list_filter = ('status_requisicao', 'escolaridade', 'tipo_de_vaga', 'dt_inclusao', 'dt_atualizacao')
    search_fields = ('cargo_ofertado', 'nome_da_empresa', 'cnpj_da_empresa', 'nome_do_responsavel_pela_divulgacao_da_vaga')
    date_hierarchy = 'dt_inclusao'
    
    # Ordenação padrão: mais recentemente atualizadas primeiro, depois por data de inclusão
    ordering = ('-dt_atualizacao', '-dt_inclusao')
    
    readonly_fields = ('hash_id', 'chave_de_acesso', 'auth_hash_temp', 'dt_inclusao', 'dt_atualizacao')
    
    fieldsets = (
        ('Identificação do Formulário', {
            'fields': (
                'hash_id', 
                'chave_de_acesso',
                'status_requisicao',
            )
        }),
        ('Dados do Responsável', {
            'fields': (
                'nome_do_responsavel_pela_divulgacao_da_vaga',
                'cpf_do_responsavel',
                'contato_do_responsavel',
            )
        }),
        ('Dados da Empresa', {
            'fields': (
                'nome_da_empresa',
                'cnpj_da_empresa',
                'endereco_da_empresa',
                'telefone_da_empresa',
                'whatsapp_da_empresa',
                'email_da_empresa',
                'segmento_da_empresa',
            )
        }),
        ('Dados da Vaga', {
            'fields': (
                'cargo_ofertado',
                'quantidade_de_vagas',
                'tipo_de_vaga',
                'regime',
                'escolaridade',
                'experiencia',
                'faixa_salarial',
                'valor_salario',
                'carga_horaria',
                'outra_carga_horaria',
            )
        }),
        ('Benefícios', {
            'fields': (
                'vale_transporte',
                'vale_alimentacao',
                'outros_beneficios',
            )
        }),
        ('Descrições e Observações', {
            'fields': (
                'observacao',
                'observacao_interna',
            )
        }),
        ('Formas de Contato para Candidatura', {
            'fields': (
                'enviar_curriculo_para_email',
                'email_para_envio',
                'levar_curriculo_direto_ao_local',
                'endereco_para_levar_curriculo',
                'via_telefone_ou_whatsapp',
                'telefone_ou_whatsapp',
                'outra_forma_de_contato',
                'outra_forma_de_contato_descricao',
            )
        }),
        ('Controle e Datas', {
            'fields': (
                'dt_inclusao',
                'dt_atualizacao',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('hash_id', 'chave_de_acesso')
        return self.readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        # Não permitir exclusão de requisições aprovadas com vagas associadas
        if obj and obj.status_requisicao == 'AP' and obj.get_vaga():
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        # Registrar histórico ao mudar status
        if change and 'status_requisicao' in form.changed_data:
            old_status = RequisicaoVaga.objects.get(pk=obj.pk).status_requisicao
            HistoricoRequisicao.objects.create(
                requisicao=obj,
                acao='ST',  # Status change
                status_anterior=old_status,
                status_novo=obj.status_requisicao,
                usuario=request.user,
                observacao=f"Status alterado de {dict(RequisicaoVaga.STATUS_CHOICES).get(old_status)} para {dict(RequisicaoVaga.STATUS_CHOICES).get(obj.status_requisicao)}"
            )
        super().save_model(request, obj, form, change)

@admin.register(CandidatoSelecionado)
class CandidatoSelecionadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'requisicao_vaga', 'status_selecao', 'dt_selecao', 'dt_atualizacao')
    list_filter = ('status_selecao', 'escolaridade', 'dt_selecao', 'dt_atualizacao')
    search_fields = ('nome', 'cpf', 'email', 'celular', 'requisicao_vaga__cargo_ofertado')
    date_hierarchy = 'dt_selecao'
    
    # Ordenação padrão: mais recentemente atualizados primeiro
    ordering = ('-dt_atualizacao', '-dt_selecao')
    
    readonly_fields = ('dt_selecao', 'dt_atualizacao')
    
    fieldsets = (
        ('Vínculo', {
            'fields': (
                'requisicao_vaga',
                'vaga',
            )
        }),
        ('Dados do Candidato', {
            'fields': (
                'nome',
                'cpf',
                'data_nascimento',
                'sexo',
                'email',
                'celular',
                'bairro',
                'escolaridade',
            )
        }),
        ('Status da Seleção', {
            'fields': (
                'status_selecao',
                'observacao_selecao',
            )
        }),
        ('Controle', {
            'fields': (
                'dt_selecao',
                'dt_atualizacao',
                'usuario_selecao',
            ),
            'classes': ('collapse',),
        }),
    )

@admin.register(HistoricoRequisicao)
class HistoricoRequisicaoAdmin(admin.ModelAdmin):
    list_display = ('requisicao', 'get_acao_display', 'status_anterior', 'status_novo', 'usuario', 'dt_criacao')
    list_filter = ('acao', 'dt_criacao', 'usuario')
    search_fields = ('requisicao__cargo_ofertado', 'requisicao__nome_da_empresa', 'observacao')
    date_hierarchy = 'dt_criacao'
    
    # Ordenação padrão: mais recentes primeiro
    ordering = ('-dt_criacao',)
    
    readonly_fields = ('dt_criacao',)