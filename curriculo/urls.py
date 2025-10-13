from django.urls import path
from . import views
app_name='cv'
urlpatterns = [
    path('curriculo', views.index, name='index'),
    path('curriculo/dados-pessoais', views.cadastrar_ou_aletarar_foto_e_objetivo, name='editar_dados'),
    path('curriculo/educacao', views.cadastrar_educacao, name='educacao'),
    path('curriculo/educacao/<id>/excluir', views.excluir_educacao, name='excluir_educacao'),
    path('curriculo/experiencia', views.cadastrar_experiencia, name='experiencia'),
     path('curriculo/experiencia/<id>/excluir', views.excluir_experiencia, name='excluir_experiencia'),
    path('curriculo/visualizar/<id>/', views.curriculo, name='curriculo'),
    path('curriculo/cpf/<str:cpf>/', views.curriculo_por_cpf, name='curriculo_por_cpf'),

]