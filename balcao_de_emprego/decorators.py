from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.models import Group

from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse

def api_user(view_func):    
    def wrap(request, *args, **kwargs):
        if  Group.objects.get(name='api_user') in request.user.groups.all() or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()
    return wrap


def empresa_user_required(view_func):
    """
    Decorador para views que requerem que o usuário seja responsável de empresa
    ou funcionário da Casa do Trabalhador
    """
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Acesso negado. Faça login para continuar.")
            return HttpResponseRedirect(reverse('login'))
        
        # Superuser e staff sempre têm acesso
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Verificar se o usuário está no grupo empresa_user
        try:
            grupo_empresa = Group.objects.get(name='empresa_user')
            if grupo_empresa in request.user.groups.all():
                # Verificar se o usuário é responsável por alguma empresa
                from vagas.models import ResponsavelEmpresa
                if ResponsavelEmpresa.objects.filter(user=request.user, ativo=True).exists():
                    return view_func(request, *args, **kwargs)
                else:
                    messages.warning(request, "Você não é responsável por nenhuma empresa ativa. Entre em contato com o administrador.")
                    return HttpResponseRedirect(reverse('vagas:home'))
            else:
                messages.error(request, "Seu usuário não tem permissão para acessar o Painel Empresarial.")
                return HttpResponseRedirect(reverse('vagas:home'))
        except Group.DoesNotExist:
            messages.error(request, "Grupo de permissão para empresas não está configurado. Entre em contato com o administrador.")
            return HttpResponseRedirect(reverse('vagas:home'))
        except Exception as e:
            messages.error(request, f"Erro ao verificar permissões: {str(e)}. Entre em contato com o administrador.")
            return HttpResponseRedirect(reverse('vagas:home'))
        
        messages.error(request, "Acesso negado. Você não tem permissão para acessar esta página.")
        return HttpResponseRedirect(reverse('vagas:home'))
    
    return wrap


def empresa_user_or_staff_required(view_func):
    """
    Decorador mais específico que verifica se o usuário pode acessar dados de uma empresa específica
    """
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Acesso negado. Faça login para continuar.")
        
        # Superuser e staff sempre têm acesso
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Verificar se é responsável de empresa
        try:
            from vagas.models import ResponsavelEmpresa
            responsavel = ResponsavelEmpresa.objects.get(user=request.user, ativo=True)
            
            # Se há empresa_id nos kwargs, verificar se pode acessar essa empresa específica
            empresa_id = kwargs.get('empresa_id')
            if empresa_id and responsavel.empresa.id != int(empresa_id):
                return HttpResponseForbidden("Acesso negado. Você não pode acessar dados desta empresa.")
            
            return view_func(request, *args, **kwargs)
            
        except ResponsavelEmpresa.DoesNotExist:
            pass
        
        return HttpResponseForbidden("Acesso negado. Você não é responsável por nenhuma empresa.")
    
    return wrap