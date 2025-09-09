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

    )
    list_filter = (
        'empresa',
        'cargo',
        'tipo_de_vaga',
        'escolaridade',
        'experiencia',
        'ativo',
        'destaque',
    )
    search_fields = (
        'empresa__nome',
        'cargo__nome',
        'email',
        'observacao',
        'atribuicoes',
    )

    list_editable = ('ativo', 'destaque')

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
            )
        }),
    )


admin.site.register(Empresa)
admin.site.register(Escolaridade)
admin.site.register(Cargo)
admin.site.register(Candidato)
admin.site.register(Slide)