from django import forms
from django.forms import ModelForm, ValidationError
from .models import *
from .validations import validate_CNPJ
class CadastroVagasForm(ModelForm):    
    class Meta:
        model = Vaga_Emprego
        widgets = {'user': forms.HiddenInput()}
        exclude = ['dt_inclusao']

class Form_Empresa(ModelForm):  
    cnpj = forms.CharField(label='CNPJ', max_length=18, widget = forms.TextInput(attrs={'onkeydown':"mascara(this,icnpj)"}))  
    telefone = forms.CharField(label='Telefone p/ encaminhamento', max_length=15, required=False, widget = forms.TextInput(attrs={'onkeydown':"mascara(this,itel)"}))  
    whatsapp = forms.CharField(label='Whatsapp p/ encaminhamento', max_length=15, required=False, widget = forms.TextInput(attrs={'onkeydown':"mascara(this,itel)"}))  

    class Meta:
        model = Empresa
        widgets = {'user': forms.HiddenInput()}
        exclude = ['dt_inclusao']

    def clean_cnpj(self):
        print(self.cleaned_data["cnpj"])
        cnpj = validate_CNPJ(self.cleaned_data["cnpj"])
        cnpj = cnpj.replace('.', '')
        cnpj = cnpj.replace('-', '')
        return cnpj

    def clean_telefone(self):
        print(self.cleaned_data["telefone"])
        telefone = validate_TELEFONE(self.cleaned_data["telefone"])        
        return telefone

    def clean_whatsapp(self):
        print(self.cleaned_data["whatsapp"])
        whatsapp = validate_TELEFONE(self.cleaned_data["whatsapp"])        
        return whatsapp

class Form_Cargo(ModelForm):    
    class Meta:
        model = Cargo
        widgets = {'user': forms.HiddenInput()}
        exclude = ['dt_inclusao']

class Form_Escolaridade(ModelForm):    
    class Meta:
        model = Escolaridade
        widgets = {'user': forms.HiddenInput()}
        exclude = ['dt_inclusao']

class Form_Candidato(ModelForm):    
    class Meta:
        model = Candidato
        widgets = {
            'vaga': forms.HiddenInput(),
            'nome': forms.TextInput(attrs={'class': 'form-control mb-2'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control mb-2'}),
            'sexo': forms.Select(attrs={'class': 'form-control mb-2'}),
            'email': forms.EmailInput(attrs={'class': 'form-control mb-2'}),
            'celular': forms.TextInput(attrs={'class': 'form-control mb-2'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control mb-2'}),
            'escolaridade': forms.Select(attrs={'class': 'form-control mb-2'}),
            'candidato_online': forms.HiddenInput(),
        }
        exclude = ['dt_inclusao', 'candidato_ativo']
