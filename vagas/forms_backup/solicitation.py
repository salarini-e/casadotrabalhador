from django import forms
from django.utils.translation import gettext_lazy as _
from vagas.models import SolicitacaoDesativacao

class SolicitarDesativacaoForm(forms.ModelForm):
    """Form for requesting job deactivation"""
    class Meta:
        model = SolicitacaoDesativacao
        fields = ['motivo', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'motivo': _('Motivo da desativação'),
            'observacoes': _('Observações adicionais'),
        }
        help_texts = {
            'observacoes': _('Se necessário, forneça detalhes adicionais sobre o motivo da desativação'),
        }

class ProcessarSolicitacaoForm(forms.Form):
    """Form for processing a deactivation request"""
    STATUS_CHOICES = [
        ('aprovada', 'Aprovar solicitação'),
        ('rejeitada', 'Rejeitar solicitação'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label=_('Decisão'),
        widget=forms.RadioSelect
    )
    
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label=_('Observações'),
        help_text=_('Se necessário, adicione observações sobre a sua decisão')
    )