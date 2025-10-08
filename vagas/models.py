from django.db import models
from django.contrib.auth.models import User
from .validations import validate_CNPJ, validate_CPF, validate_TELEFONE
from django.utils import timezone
import hashlib
import secrets
import uuid
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

    def get_cnpj(self):
        cnpj_formated = f"{self.cnpj[:2]}.{self.cnpj[2:5]}.{self.cnpj[5:8]}/{self.cnpj[8:12]}-{self.cnpj[12:]}"
        return cnpj_formated
    
    def get_total_vagas_count(self):
        """Retorna o número total de vagas oferecidas pela empresa"""
        return self.vaga_emprego_set.count()
    
    def get_active_vagas_count(self):
        """Retorna o número de vagas ativas da empresa"""
        return self.vaga_emprego_set.filter(ativo=True).count()
    
    def get_total_candidatos_count(self):
        """Retorna o número total de candidatos únicos (por CPF) da empresa"""
        from django.db.models import Count
        return Candidato.objects.filter(
            vaga__empresa=self
        ).values('cpf').distinct().count()
    
    def get_total_formularios_count(self):
        """Retorna o número total de formulários criados para a empresa (por CNPJ)"""
        return RequisicaoVaga.objects.filter(cnpj_da_empresa=self.cnpj).count()
    
    def get_approved_formularios_count(self):
        """Retorna o número de formulários aprovados da empresa"""
        return RequisicaoVaga.objects.filter(
            cnpj_da_empresa=self.cnpj, 
            status_requisicao='AP'
        ).count()                                                                                                                                                                            

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
    requisicao_vaga=models.ForeignKey('RequisicaoVaga', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Requisição de Vaga', help_text='Requisição que originou esta vaga')
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

    # Campos para solicitação de desativação
    solicitacao_desativacao = models.BooleanField(default=False, verbose_name='Solicitação de desativação')
    motivo_solicitacao_desativacao = models.CharField(max_length=255, blank=True, null=True, verbose_name='Motivo da solicitação de desativação')
    observacoes_solicitacao_desativacao = models.TextField(blank=True, null=True, verbose_name='Observações da solicitação de desativação')
    dt_solicitacao_desativacao = models.DateTimeField(verbose_name='Data de solicitação de desativação', null=True, blank=True)
    usuario_solicitacao_desativacao = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitacoes_desativacao', verbose_name='Usuário que solicitou a desativação')

    dt_atualizacao = models.DateTimeField(verbose_name='Dt. Atualização', null=True, blank=True)
    
    def __str__(self):
        return '%s - %s' % (self.empresa, self.cargo)
    
    def get_email_encaminhamento(self):
        """Retorna email para encaminhamento: prioriza email da vaga, depois da empresa"""
        return self.email if self.email else self.empresa.email
    
    def save(self, *args, **kwargs):
        if self.dt_inclusao:
            self.dt_atualizacao = timezone.now()
        super(Vaga_Emprego, self).save(*args, **kwargs)

#ENCAMINHAMENTOS
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

    def idade(self):
        from datetime import date
        today = date.today()
        return today.year - self.data_nascimento.year - ((today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day))

    def n_encaminhamentos(self):
        qnt = Candidato.objects.filter(cpf=self.cpf).count()
        return qnt

    def contato(self):
        return self.celular
    
    def get_cpf(self):
        cpf_formated = f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"
        return cpf_formated

    def get_encaminhamentos(self):
        return Candidato.objects.filter(cpf = self.cpf)
    
    def curriculo(self):
        url_curriculo = False
        return url_curriculo
        


class Slide(models.Model):

    titulo = models.CharField(max_length=64)    
    banner_img = models.ImageField(upload_to='banner_evento', verbose_name='Arte do evento')    

    def __str__(self):
        return '%s' % (self.titulo)

class RequisicaoVaga(models.Model):

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

    REGIME_CHOICES=(
                            ('CLT', 'CLT'),
                            ('PJ', 'Pessoa Jurídica'),
                            ('TEMP', 'Temporário'),
                            ('EST', 'Estágio')
    )
    FAIXA_SALARIAL_CHOICES=(
        ('ACB', 'À combinar'),
        ('MIN', 'Mínimo'),
        ('VALOR', 'Entrar com valor')
    )

    CARGA_HORARIA_CHOICES=(
        ('40', '40 horas semanais'),
        ('44', '44 horas semanais'),
        ('OUT', 'Outra escala')
    )
    STATUS_CHOICES = (
        ('AG', 'Aguardando'),
        ('PE', 'Pendente'),
        ('AP', 'Aprovada'),
        ('RE', 'Rejeitada'),
        ('AE', 'Aguardando Encerramento'),
        ('EN', 'Encerrada')
    )

    hash_id = models.CharField(max_length=64, unique=True, editable=False)
    chave_de_acesso = models.CharField(max_length=64, editable=False)
    auth_hash_temp = models.CharField(max_length=64, blank=True, null=True, editable=False)  # Hash temporário para autenticação

    nome_do_responsavel_pela_divulgacao_da_vaga = models.CharField(max_length=150, verbose_name='Nome do responsável pela divulgação da vaga')
    cpf_do_responsavel = models.CharField(max_length=14, validators=[validate_CPF], verbose_name='CPF do responsável')
    contato_do_responsavel = models.CharField(max_length=15, validators=[validate_TELEFONE], blank=True, verbose_name='Contato do responsável')

    #DA EMPRESA
    nome_da_empresa = models.CharField(max_length=150, verbose_name='Nome da empresa')
    endereco_da_empresa = models.CharField(max_length=100, blank=True, verbose_name='Endereço da empresa')
    cnpj_da_empresa = models.CharField(max_length=14, validators=[validate_CNPJ], verbose_name='CNPJ da empresa')
    telefone_da_empresa = models.CharField(max_length=15, validators=[validate_TELEFONE], blank=True, verbose_name='Telefone da empresa')
    email_da_empresa = models.EmailField(max_length=254, blank=True, verbose_name='Email da empresa')
    segmento_da_empresa = models.CharField(max_length=100, blank=True, verbose_name='Segmento da empresa')
    whatsapp_da_empresa = models.CharField(max_length=15, validators=[validate_TELEFONE], blank=True, verbose_name='Whatsapp da empresa')

    #DA VAGA
    quantidade_de_vagas = models.IntegerField(blank=False, null=False, verbose_name='Quantidade de vagas')
    cargo_ofertado = models.CharField(max_length=100, verbose_name='Cargo ofertado')
    tipo_de_vaga = models.CharField(max_length=3, choices=TIPO_DE_VAGA_CHOICES, default='NML')
    regime = models.CharField(max_length=100, default='', blank=True)
    faixa_salarial = models.CharField(max_length=6, choices=FAIXA_SALARIAL_CHOICES, default='ACB', verbose_name='Faixa salarial')
    valor_salario = models.CharField(max_length=50, default='', blank=True, verbose_name='Valor do salário')
    
    #BENEFICIOS
    vale_transporte = models.BooleanField(default=False, verbose_name='Vale transporte')
    vale_alimentacao = models.BooleanField(default=False, verbose_name='Vale alimentação')
    outros_beneficios = models.TextField(default='', blank=True, verbose_name='Outros benefícios')
    carga_horaria = models.CharField(max_length=3, choices=CARGA_HORARIA_CHOICES, default='40', verbose_name='Carga horária')
    outra_carga_horaria = models.CharField(max_length=50, default='', blank=True, verbose_name='Informe a carga horária')

    #REQUISITOS
    escolaridade = models.ForeignKey(Escolaridade, on_delete=models.CASCADE)
    experiencia = models.CharField(max_length=3, choices=EXPERIENCIA_CHOICES, verbose_name='Experiência')        
    observacao = models.TextField(default='', blank=True, verbose_name='Descreva as demais competências e outras observações que forem pertinentes à vaga')

    enviar_curriculo_para_email = models.BooleanField(default=False, verbose_name='Enviar currículos para o email da empresa')
    email_para_envio = models.EmailField(max_length=254, verbose_name="Email p/ envio dos currículos", blank=True, null=True)
    levar_curriculo_direto_ao_local = models.BooleanField(default=False, verbose_name='Levar currículo direto ao local da vaga')
    endereco_para_levar_curriculo = models.CharField(max_length=100, blank=True, verbose_name='Endereço para levar currículo')
    via_telefone_ou_whatsapp = models.BooleanField(default=False, verbose_name='Via telefone ou whatsapp')  
    telefone_ou_whatsapp = models.CharField(max_length=15, validators=[validate_TELEFONE], blank=True, verbose_name='Telefone ou whatsapp')
    outra_forma_de_contato = models.BooleanField(default=False, verbose_name='Outra forma de contato')  
    outra_forma_de_contato_descricao = models.CharField(max_length=100, blank=True, verbose_name='Descreva a outra forma de contato')
    dt_inclusao = models.DateTimeField(auto_now_add=True, verbose_name='Dt. Inclusão')
    dt_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Dt. Atualização')
    
    status_requisicao = models.CharField(max_length=2, choices=STATUS_CHOICES, default='AG', verbose_name='Status da requisição')
    observacao_interna = models.TextField(blank=True, null=True, verbose_name='Observação interna')
    
    class Meta:
        verbose_name = "Requisição de Vaga"
        verbose_name_plural = "Requisições de Vagas"
        ordering = ['-dt_inclusao']
    
    def __str__(self):
        return f"{self.cargo_ofertado} - {self.nome_da_empresa}"
    
    def save(self, *args, **kwargs):
        # Gerar hash_id único se não existir
        if not self.hash_id:
            self.hash_id = hashlib.sha256(f"{uuid.uuid4()}{timezone.now()}".encode()).hexdigest()
        
        # Gerar chave de acesso única se não existir
        if not self.chave_de_acesso:
            self.chave_de_acesso = secrets.token_urlsafe(32)
        
        # Limpar campos de telefone (remover máscaras)
        if self.contato_do_responsavel:
            self.contato_do_responsavel = ''.join(filter(str.isdigit, self.contato_do_responsavel))
        
        if self.telefone_da_empresa:
            self.telefone_da_empresa = ''.join(filter(str.isdigit, self.telefone_da_empresa))
        
        if self.whatsapp_da_empresa:
            self.whatsapp_da_empresa = ''.join(filter(str.isdigit, self.whatsapp_da_empresa))
            
        if self.telefone_ou_whatsapp:
            self.telefone_ou_whatsapp = ''.join(filter(str.isdigit, self.telefone_ou_whatsapp))
        
        # Limpar campos de CPF e CNPJ (remover máscaras)
        if self.cpf_do_responsavel:
            self.cpf_do_responsavel = ''.join(filter(str.isdigit, self.cpf_do_responsavel))
            
        if self.cnpj_da_empresa:
            self.cnpj_da_empresa = ''.join(filter(str.isdigit, self.cnpj_da_empresa))
        
        super().save(*args, **kwargs)
    
    def get_public_url(self):
        """Retorna a URL pública do formulário (página de autenticação com hash)"""
        from django.urls import reverse
        return reverse('vagas:formulario_autenticacao', kwargs={'hash_id': self.hash_id})
    
    def get_admin_url(self):
        """Retorna a URL do admin para esta requisição"""
        from django.urls import reverse
        return reverse('vagas:admin_requisicao_detail', kwargs={'pk': self.pk})

    def get_vaga(self):
        return Vaga_Emprego.objects.filter(requisicao_vaga=self).last()

class HistoricoRequisicao(models.Model):
    """
    Modelo para rastrear mudanças de status e observações das requisições
    """
    
    ACAO_CHOICES = (
        ('CR', 'Criação'),
        ('ST', 'Mudança de Status'),
        ('OB', 'Observação'),
        ('ED', 'Edição'),
    )
    
    requisicao = models.ForeignKey(RequisicaoVaga, on_delete=models.CASCADE, related_name='historico')
    acao = models.CharField(max_length=2, choices=ACAO_CHOICES, verbose_name='Ação')
    status_anterior = models.CharField(max_length=2, choices=RequisicaoVaga.STATUS_CHOICES, blank=True, null=True)
    status_novo = models.CharField(max_length=2, choices=RequisicaoVaga.STATUS_CHOICES, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Usuário')
    dt_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora')
    
    class Meta:
        verbose_name = "Histórico de Requisição"
        verbose_name_plural = "Históricos de Requisições"
        ordering = ['-dt_criacao']
    
    def __str__(self):
        return f"{self.requisicao} - {self.get_acao_display()} em {self.dt_criacao.strftime('%d/%m/%Y %H:%M')}"


class CandidatoSelecionado(models.Model):
    """
    Modelo para rastrear candidatos selecionados/aprovados para vagas específicas
    através do sistema de formulários externos
    """
    
    STATUS_CHOICES = (
        ('PE', 'Pendente'),
        ('AP', 'Aprovado'), 
        ('RE', 'Rejeitado'),
        ('CO', 'Contratado'),
    )
    
    requisicao_vaga = models.ForeignKey(RequisicaoVaga, on_delete=models.CASCADE, related_name='candidatos_selecionados')
    vaga = models.ForeignKey('Vaga_Emprego', on_delete=models.CASCADE, null=True, blank=True, related_name='candidatos_selecionados')
    
    # Dados do candidato (copiados no momento da seleção)
    nome = models.CharField(max_length=100, verbose_name='Nome do candidato')
    cpf = models.CharField(max_length=14, verbose_name='CPF do candidato')
    data_nascimento = models.DateField(verbose_name='Data de nascimento')
    sexo = models.CharField(max_length=1, choices=Candidato.SEXO_CHOICES, verbose_name='Sexo')
    email = models.EmailField(max_length=254, verbose_name='Email', blank=True)
    celular = models.CharField(max_length=15, verbose_name='Celular')
    bairro = models.CharField(max_length=100, verbose_name='Bairro', blank=True)
    escolaridade = models.ForeignKey(Escolaridade, on_delete=models.CASCADE)
    
    # Controle de seleção
    status_selecao = models.CharField(max_length=2, choices=STATUS_CHOICES, default='PE', verbose_name='Status da Seleção')
    observacao_selecao = models.TextField(blank=True, null=True, verbose_name='Observação da Seleção')
    
    # Metadados
    dt_selecao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Seleção')
    dt_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')
    usuario_selecao = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Usuário que Selecionou')
    
    class Meta:
        verbose_name = "Candidato Selecionado"
        verbose_name_plural = "Candidatos Selecionados"
        ordering = ['-dt_selecao']
        unique_together = ['requisicao_vaga', 'cpf']  # Um candidato por requisição
    
    def __str__(self):
        return f"{self.nome} - {self.requisicao_vaga.cargo_ofertado}"
    
    def idade(self):
        from datetime import date
        today = date.today()
        return today.year - self.data_nascimento.year - ((today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day))
    
    def get_cpf_formatado(self):
        return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"


class ResponsavelEmpresa(models.Model):
    """Modelo para gerenciar usuários responsáveis pelas empresas"""
    
    NIVEL_CHOICES = (
        ('RESP', 'Responsável Principal'),
        ('AUX', 'Auxiliar')
    )
    
    class Meta:
        verbose_name = "Responsável da Empresa"
        verbose_name_plural = "Responsáveis das Empresas"
        ordering = ['nome']
        # Um usuário pode ser responsável por várias empresas
        # Removemos a restrição OneToOneField para permitir isso
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='responsaveis', verbose_name='Empresa')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário', null=True, blank=True, related_name='empresas_responsavel')
    nome = models.CharField(max_length=100, verbose_name='Nome completo', null=True, blank=True)
    cpf = models.CharField(max_length=14, verbose_name='CPF', validators=[validate_CPF], null=True)
    email = models.EmailField(verbose_name='Email', null=True, blank=True)
    cargo = models.CharField(max_length=100, verbose_name='Cargo na empresa')
    nivel = models.CharField(max_length=4, choices=NIVEL_CHOICES, default='RESP', verbose_name='Nível de acesso')
    telefone = models.CharField(max_length=15, verbose_name='Telefone para contato', validators=[validate_TELEFONE])
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    dt_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')
    criado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='responsaveis_criados', 
                                 verbose_name='Criado por')
    observacoes = models.TextField(blank=True, verbose_name='Observações internas')
    
    def __str__(self):
        cpf_info = f"({self.get_cpf_formatado()})" if self.cpf else ""
        nome = self.nome or "Nome não informado"
        return f"{nome} {cpf_info} - {self.empresa.nome}"
    
    def get_cpf_formatado(self):
        """Retorna CPF formatado"""
        if not self.cpf:
            return "CPF não informado"
        if len(self.cpf) == 11:
            return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"
        return self.cpf
    
    def get_cpf_numeros(self):
        """Retorna apenas os números do CPF"""
        if not self.cpf:
            return ""
        return ''.join(filter(str.isdigit, self.cpf))
    
    def pode_acessar_empresa(self, empresa_id):
        """Verifica se o responsável pode acessar os dados da empresa"""
        return self.ativo and self.empresa.id == empresa_id
    
    def eh_responsavel_principal(self):
        """Verifica se o usuário é responsável principal (não auxiliar)"""
        return self.nivel == 'RESP'
    
    def vincular_usuario_existente(self):
        """Tenta vincular a um usuário existente com base no CPF ou email"""
        from autenticacao.models import Pessoa
        
        # Primeiro tenta encontrar por CPF na tabela Pessoa
        if self.cpf:
            try:
                pessoa = Pessoa.objects.get(cpf=self.get_cpf_numeros())
                self.user = pessoa.user
                return True
            except Pessoa.DoesNotExist:
                pass
        
        # Se não encontrou por CPF, tenta por email
        if self.email:
            try:
                user = User.objects.get(email=self.email)
                self.user = user
                return True
            except User.DoesNotExist:
                pass
            
        return False