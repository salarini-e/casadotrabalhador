from django.urls import path
from . import views
app_name='vagas'

urlpatterns = [
    path('', views.vagas, name='home'), 
    path('totem/', views.totem_v1, name='totem_v1'),
    path('totem/candidatar-se/<id>/', views.totem_candidatarse, name='totem_candidatarse'),
    path('totem/candidatura-sucesso/<id>/', views.totem_candidatura_sucesso, name='totem_candidatura_sucesso'),
    path('exportar-vagas/', views.exportar_vagas_excel, name='exportar_vagas'), 
    path('meus-encaminhamentos/', views.meus_encaminhamentos, name='meus_encaminhamentos'),
    path('indicadores', views.indicadores, name='indicadores'),  
    
    path('cadastrar-escolaridade', views.cadastrar_escolaridade, name='cadastrar_escolaridade'),
    path('cadastrar-vaga-ofertada/', views.cadastrar_vagaOfertada, name='cadastrar'),    
    path('cadastrar-empresa/', views.cadastrar_empresa, name='cadastrar_empresa'),    
    path('cadastrar-cargo/', views.cadastrar_cargo, name='cadastrar_cargo'),    
    path('cadastrar-vaga-em-lote/', views.cadastrar_vaga_emLote, name='cadastrar_vaga_emLote'), 

    path('alterar-vaga/alt0x#<id>001', views.alterar_vaga, name='alterar_vaga'),    
    path('alterar-empresa/alt0x#<id>001', views.alterar_empresa, name='alterar_empresa'),    
    path('alterar-escolaridade/alt0x#<id>001', views.alterar_escolaridade, name='alterar_escolaridade'),    
    path('alterar-cargo/alt0x#<id>001', views.alterar_cargo, name='alterar_cargo'),    

    path('visualizar-vaga/<id>', views.visualizar_vaga, name='visualizar_vaga'),    
    path('remover-vaga/alt0x#<id>001', views.remover_vaga, name='remover_vaga'),    
    path('visualizar-vaga/alt0x#<id>/candidatar-se', views.candidatarse, name='candidatarse'),        
    path('visualizar-vaga/alt0x#<id>/encaminhar', views.encaminhar, name='encaminhar'),    
    
    path('visualizar-vaga/alt0x<id>0<user_id>01/encaminhamento', views.encaminhamento, name='encaminhamento'),    
    path('visualizar-vaga/alt0x<id>0<user_id>02/encaminhamento', views.gera_encaminhamento_to_pdf, name='encaminhamento_pdf'),    
    
    path('vagas/', views.vagas, name='vagas'),    
    path('vagas/imprimir', views.imprimir_vagas, name='imprimir'),    
    path('listar-cargos/', views.listar_cargos, name='listar_cargos'),   

    path('empresas/', views.empresas, name='empresas'),    
    path('escolaridades/', views.escolaridades, name='escolaridades'),    
    path('vagas/table/', views.vagas_table, name='vagas_table'),    

    path('get_vaga/', views.get_cargo, name='get_vaga' ),
    path('get_empresa/', views.get_empresa, name='get_empresa' ),
    path('get_candidatos/', views.get_candidatos, name='get_candidatos' ),
    path('visualizar-vaga/alt0x#<id>001/<mes>/<ano>/listar-canditados/', views.candidatosporvaga, name='listar_candidatos'),
    path('vagas-com-candidatos/', views.vagascomcandidatos, name='vagas_com_candidatos'),
    path('empresa/info/', views.infoempresa, name='empresa_info'),
    path('empresa/info/<id>/download/', views.infoempresa_download, name='empresa_info_download'),
    path('candidatos-por-funcionario/', views.candidatosporfuncionario, name='candidatosporfuncionario'),
    path('candidatos-por-funcionario/<id>', views.funcionario_encaminhados, name='funcionarios_encaminhados'), 
    path('pesquisar-candidatos/', views.pesquisar_candidatos, name='pesquisar_candidatos'), 
    path('visualizar-candidatos/<id>', views.visualizar_candidato, name='visualizar_candidato'), 
    path('painel_administrativo/', views.painel_administrativo, name="painel_administrativo"),
    path('painel_administrativo/backup/', views.BackupDatabaseView.as_view(), name="backup_database"),
    path('painel_administrativo/excluir_cpf', views.painel_administrativo_excluir_cpf, name="painel_administrativo_excluir_cpf"),
    path('excluir_cpf', views.excluir_cpf, name="excluir_cpf"),
    path('emails', views.emails, name="emails"),
    path('emails/csv/<month>/<year>', views.download_emails, name='download_emails'),

    # URLs para sistema de formulários
    path('admin/formularios/', views.admin_formularios_list, name='admin_formularios_list'),
    path('admin/formularios/criar/', views.admin_formularios_create, name='admin_formularios_create'),
    path('admin/formularios/<int:id>/', views.admin_formularios_detail, name='admin_formularios_detail'),
    path('admin/formularios/<int:id>/status/', views.admin_formularios_update_status, name='admin_formularios_update_status'),
    path('admin/formularios/<int:id>/cadastrar-vaga/', views.cadastrar_vaga_aprovada, name='cadastrar_vaga_aprovada'),
    path('admin/vagas/<int:vaga_id>/candidatos/', views.candidatos_vaga, name='candidatos_vaga'),
    path('formulario/<str:hash_id>/acesso/', views.formulario_autenticacao, name='formulario_autenticacao'),
    path('formulario/<str:hash_id>/', views.formulario_publico, name='formulario_publico'),
    path('formulario/<str:hash_id>/detalhes/', views.formulario_detalhes_externo, name='formulario_detalhes_externo'),
    path('formulario/<str:hash_id>/selecionar-candidato/', views.selecionar_candidato, name='selecionar_candidato'),
    path('formulario/<str:hash_id>/atualizar-status-candidato/', views.atualizar_status_candidato, name='atualizar_status_candidato'),
    path('formulario/sucesso/', views.formulario_sucesso, name='formulario_sucesso'),
]
