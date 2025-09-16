from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class Pessoa(models.Model):

    def __str__(self):
        return '%s - Email: %s' % (self.nome, self.email)
    
    foto = models.ImageField(upload_to='fotos', verbose_name='Foto', null=True, blank=True)
    objetivo = models.CharField(max_length=380, verbose_name='Objetivo', null=True, blank=True)
    user=models.OneToOneField(User, on_delete=models.CASCADE)
    nome=models.CharField(max_length=64, verbose_name='Nome')
    email=models.EmailField()
    cpf=models.CharField(max_length=14, verbose_name='CPF', unique=True, null=True)
    telefone=models.CharField(max_length=15, verbose_name='Telefone', null=True)
    dt_nascimento=models.DateField(verbose_name='Data de nascimento', null=True)
    bairro=models.CharField(max_length=64, verbose_name='Bairro', null=True)
    endereco=models.CharField(max_length=128, verbose_name='Endereco', null=True)
    complemento=models.CharField(max_length=128, verbose_name='Complemento', blank=True, null=True)
    cep = models.CharField(max_length=9, verbose_name='CEP', null=True)
    dt_inclusao=models.DateField(auto_now_add=True, verbose_name='Data de inclusão')

    __original_email = None
    __original_nome = None

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        if self.user is not None:
            if self.email != self.__original_email:
                self.user.username = self.email
                self.user.email = self.email
                self.user.save()
            if self.nome != self.__original_nome:
                self.user.first_name = self.nome
                self.user.save()

        super().save(force_insert, force_update, *args, **kwargs)
        self.__original_email = self.email
        self.__original_nome = self.nome
    
    def idade(self):
        """Calcula a idade baseada na data de nascimento"""
        if self.dt_nascimento:
            from datetime import date
            today = date.today()
            return today.year - self.dt_nascimento.year - ((today.month, today.day) < (self.dt_nascimento.month, self.dt_nascimento.day))
        return None
    
    def get_sexo_display(self):
        """Método para compatibilidade com o template que espera sexo"""
        # Como o modelo Pessoa não tem campo sexo, retorna "Não informado"
        return "Não informado"
    
    @property
    def escolaridade(self):
        """Propriedade para compatibilidade - pode ser implementada futuramente"""
        # Como não há relação com escolaridade no modelo Pessoa atual,
        # retorna um objeto mock para evitar erros no template
        class MockEscolaridade:
            nome = "Não informado"
        return MockEscolaridade()
# class Contribuinte(models.Model):
#     cnpj
#     nome_da_empresa
#     porte
#     atividade
#     ramo
#     outro_ramo
#     Deseja receber notificações sobre compras da prefeitura?