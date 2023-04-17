from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('edit', views.edit, name='edit'),
    path('persons', views.persons, name='persons'),
    path('graph', views.graph, name='graph'),
]
