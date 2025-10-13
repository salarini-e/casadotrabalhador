from django import template
from django.db.models import Q

register = template.Library()

@register.simple_tag
def pending_solicitacoes_count():
    try:
        from vagas.models import SolicitacaoDesativacao
        return SolicitacaoDesativacao.objects.filter(status='pendente').count()
    except Exception:
        return 0
