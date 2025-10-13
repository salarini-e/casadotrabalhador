from django import template
from vagas.models import SolicitacaoDesativacao

register = template.Library()

@register.simple_tag
def get_pending_deactivation_requests():
    """
    Returns the count of pending deactivation requests.
    """
    return SolicitacaoDesativacao.objects.filter(aprovada=False, recusada=False).count()

@register.simple_tag
def get_company_pending_deactivation_requests(responsavel):
    """
    Returns the count of pending deactivation requests for a specific company.
    """
    return SolicitacaoDesativacao.objects.filter(
        vaga__empresa__responsavel=responsavel,
        aprovada=False,
        recusada=False
    ).count()