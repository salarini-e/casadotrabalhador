from django.db import models
from django.contrib.auth.models import User
from .validations import validate_CNPJ, validate_CPF, validate_TELEFONE
from django.utils import timezone
# Create your models here.

# class Candidato(models.Model):
#     nome=models.CharField(max_length=150, verbose_name='Nome:', unique=True)
#     cpf=models.CharField(max_length=14, verbose_name='CPF:', validators=[validate_CPF], unique=True)
#     data_nascimento = models.DateField(verbose_name='Data Nascimento')
#     email=models.EmailField(verbose_name='Email:', unique=True)
#     bairro=models.CharField(max_length=40, verbose_name='Bairro:')
#     dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')
#     telefone=models.CharField(max_length=11, validators=[validate_TELEFONE], blank=True, verbose_name='Telefone:')

class Escolaridade(models.Model):
    nome=models.CharField(max_length=150, verbose_name='Nome da escolaridade', unique=True)
    user=models.ForeignKey(User, on_delete=models.PROTECT)                    
    dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')

    def __str__(self):
        return '%s' % (self.nome)

class Empresa(models.Model):

    OCULTAR_CHOICES=(
                            (True, 'Ocultar informações da empresa ao encaminhar'),
                            (False, 'Exibir informações da empresa ao encaminhar')
    )

    FORMA_CONTATO_CHOICES=(
                            ('T', 'TELEFONE'),
                            ('E', 'EMAIL'),
                            ('P', 'PRESENCIAL'),
    )

    nome=models.CharField(max_length=150, verbose_name='NOME', unique=True)
    cnpj=models.CharField(max_length=14, validators=[validate_CNPJ], verbose_name='CNPJ', unique=True)
    endereco=models.CharField(max_length=100, blank=True, verbose_name='Endereço p/ encaminhamento')
    bairro=models.CharField(max_length=60, blank=True, default='', verbose_name='Bairro')
    telefone=models.CharField(max_length=11, validators=[validate_TELEFONE], blank=True, verbose_name='Telefone p/ encaminhamento')
    whatsapp=models.CharField(max_length=11, validators=[validate_TELEFONE], blank=True, verbose_name='Whatsapp p/ encaminhamento')
    email=models.CharField(max_length=254, verbose_name="Email p/ encaminhamento", blank=True)    
    link=models.CharField(max_length=254, verbose_name="Link p/ encaminhamento", blank=True)  
    ocultar=models.BooleanField(default=True, verbose_name='Informações da empresa', choices=OCULTAR_CHOICES)
    contato_presencial=models.BooleanField(default=False, verbose_name='Contato presencial')
    contato_email=models.BooleanField(default=False, verbose_name='Contato por email')    
    contato_telefone=models.BooleanField(default=False, verbose_name='Contato por telefone')
    contato_whatsapp=models.BooleanField(default=False, verbose_name='Contato por whatsapp')
    contato_link=models.BooleanField(default=False, verbose_name='Contato via link')
    observacao=models.TextField(default='', blank=True, verbose_name='Observações internas')
    # formaDeContato=models.CharField(max_length=1, choices=FORMA_CONTATO_CHOICES, verbose_name='Forma de contato')    
    user=models.ForeignKey(User, on_delete=models.PROTECT)                    
    dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')
    
    def __str__(self):
        return '%s' % (self.nome)

class Cargo(models.Model):

    nome=models.CharField(max_length=100, verbose_name='Nome do cargo', unique=True)
    user=models.ForeignKey(User, on_delete=models.PROTECT)                    
    dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')

    def __str__(self):
        return '%s' % (self.nome)

class Vaga_Emprego(models.Model):

    class Meta:
        verbose_name_plural = "Vagas de Emprego"
        verbose_name = "Vaga de Emprego"
        ordering = ['cargo', 'empresa']

    EXPERIENCIA_CHOICES=(
                            ('Sim', 'Sim'),
                            ('Não', 'Não'),
                            ('Des', 'Desejável')
    )
    
    TIPO_DE_VAGA_CHOICES=(
                            ('NML', 'Padrão'),
                            ('JAP', 'Jovem aprendiz'),
                            ('PED', 'Pessoa com deficiência'),
                            ('EST', 'Estágio')

    )

    empresa=models.ForeignKey(Empresa, on_delete=models.CASCADE) 
    email=models.CharField(max_length=254, verbose_name="Email p/ encaminhamento", blank=True, null=True)     
    cargo=models.ForeignKey(Cargo, on_delete=models.CASCADE)
    quantidadeVagas=models.IntegerField(blank=False, null=False, verbose_name='Quantidade de vagas')
    tipo_de_vaga=models.CharField(max_length=3, choices=TIPO_DE_VAGA_CHOICES, default='NML')
    escolaridade=models.ForeignKey(Escolaridade, on_delete=models.CASCADE)
    salario=models.CharField(max_length=50, default='', blank=True, verbose_name='Salário')
    carga_horaria=models.CharField(max_length=50, default='', blank=True, verbose_name='Carga Horária')
    regime=models.CharField(max_length=100, default='', blank=True)
    experiencia=models.CharField(max_length=3, choices=EXPERIENCIA_CHOICES, verbose_name='Experiência')    
    observacao=models.TextField(default='', blank=True, verbose_name='Observação')
    atribuicoes=models.TextField(default='', blank=True, verbose_name='Atribuições')
    destaque=models.BooleanField(default=False)
    banner_img = models.ImageField(upload_to='banner_vaga', verbose_name='Arte da vaga', null=True, blank=True)
    user=models.ForeignKey(User, on_delete=models.PROTECT)                    
    dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')    
    dt_desativacao = models.DateTimeField(verbose_name='Dt. Desativação', null=True, blank=True)
    ativo=models.BooleanField(default=True)        

    dt_atualizacao = models.DateTimeField(verbose_name='Dt. Atualização', null=True, blank=True)
    
    def __str__(self):
        return '%s - %s' % (self.empresa, self.cargo)
    def save(self, *args, **kwargs):
        if self.dt_inclusao:
            self.dt_atualizacao = timezone.now()
        super(Vaga_Emprego, self).save(*args, **kwargs)

class Candidato(models.Model):

    class Meta:
        verbose_name_plural = "Candidatos"
        verbose_name = "Candidato"
        ordering = ['nome']

    SEXO_CHOICES=[
        ('m', 'Masculino'), 
        ('f', 'Feminino'),
        ('o', 'Outro')
    ]
    
    vaga=models.ForeignKey(Vaga_Emprego, on_delete=models.CASCADE)
    nome=models.CharField(max_length=100, verbose_name='Nome do candidato', blank=False, null=False)        
    cpf=models.CharField(max_length=14, verbose_name='CPF do candidato', blank=False, null=False)        
    data_nascimento=models.DateField(verbose_name='Data de nascimento do candidato', blank=False, null=False)
    sexo=models.CharField(max_length=1, choices=SEXO_CHOICES, verbose_name='Sexo do candidato')
    email=models.EmailField(max_length=254, verbose_name="Email p/ contato com o candidato", blank=True, null=False)    
    celular=models.CharField(max_length=15, validators=[validate_TELEFONE], verbose_name='Celular p/ contato com o candidato', blank=False, null=False)
    bairro=models.CharField(max_length=100, verbose_name='Bairro do candidato', blank=True, null=True)    
    escolaridade=models.ForeignKey(Escolaridade, on_delete=models.CASCADE)
    candidato_online=models.BooleanField(default=False, verbose_name='Candidato online')
    dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')
    funcionario_encaminhamento=models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    candidato_ativo=models.BooleanField(default=True)
    # Talvez seja interessante inserir um campo que informe se o candidato entrou em contato com o RH  da empresa
    conseguiu_vaga=models.BooleanField(default=False)
    dt_aquisicao = models.CharField(max_length=10, default='')
    dt_inclusao=models.DateTimeField(verbose_name='Data de inclusão do candidato', auto_now_add=True)
    dt_atualizacao=models.DateTimeField(verbose_name='Data da última atualização do candidato', blank=True, null=True)
    
    def __str__(self):
        return '%s - %s' % (self.vaga.cargo, self.nome)


class Slide(models.Model):

    titulo = models.CharField(max_length=64)    
    banner_img = models.ImageField(upload_to='banner_evento', verbose_name='Arte do evento')    

    def __str__(self):
        return '%s' % (self.titulo)