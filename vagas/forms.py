from django import forms
from django.forms import ModelForm, ValidationError
from .models import *
from .validations import validate_CNPJ

class CadastroInternoVagasForm(ModelForm):    
    class Meta:
        model = Vaga_Emprego
        widgets = {'user': forms.HiddenInput()}
        exclude = ['banner_img','dt_inclusao', 'dt_desativacao']

class CadastroVagasForm(ModelForm):    
    class Meta:
        model = Vaga_Emprego
        widgets = {'user': forms.HiddenInput()}
        exclude = ['banner_img','dt_inclusao', 'dt_desativacao', 'observacao', 'email']

# class Form_Candidato(ModelForm):
#     class Meta:
#         model = Candidato
#         exclude = ['dt_inclusao', 'funcionario_encaminhamento']

class Form_Empresa(ModelForm):  
    cnpj = forms.CharField(label='CNPJ', max_length=18, widget = forms.TextInput(attrs={'onkeydown':"mascara(this,icnpj)"}))  
    telefone = forms.CharField(label='Telefone p/ encaminhamento', max_length=15, required=False, widget = forms.TextInput(attrs={'onkeydown':"mascara(this,itel)"}))  
    whatsapp = forms.CharField(label='Whatsapp p/ encaminhamento', max_length=15, required=False, widget = forms.TextInput(attrs={'onkeydown':"mascara(this,itel)"}))  

    class Meta:
        model = Empresa
        widgets = {
        'user': forms.HiddenInput(),
        }
        exclude = ['dt_inclusao']

    def clean_cnpj(self):
        cnpj = validate_CNPJ(self.cleaned_data["cnpj"])
        cnpj = cnpj.replace('.', '')
        cnpj = cnpj.replace('-', '')
        return cnpj

    def clean_telefone(self):
        telefone = validate_TELEFONE(self.cleaned_data["telefone"])        
        return telefone

    def clean_whatsapp(self):
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
            'nome': forms.TextInput(attrs={'class': 'form-control mb-2', 'type':'text','onkeydown':'mascara(this, inome)'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control mb-2', 'onkeydown':'mascara(this, icpf)', 'required': True}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control mb-2', 'type':'date'}),
            'sexo': forms.Select(attrs={'class': 'form-control mb-2'}),
            'email': forms.EmailInput(attrs={'class': 'form-control mb-2'}),
            'celular': forms.TextInput(attrs={'class': 'form-control mb-2', 'onkeydown':'mascara(this, icelular)'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control mb-2'}),
            'escolaridade': forms.Select(attrs={'class': 'form-control mb-2'}),
            'candidato_online': forms.HiddenInput(),            
        }
        exclude = ['dt_inclusao', 'candidato_ativo', 'conseguiu_vaga','dt_aquisicao', 'funcionario_encaminhamento', 'dt_atualizacao']

    def clean_cpf(self):
        cpf = validate_CPF(self.cleaned_data["cpf"])
        cpf = cpf.replace('.', '')
        cpf = cpf.replace('-', '')
        return cpf