from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('edit-select', views.edit_selection, name='edit-selection'),
    path('edit', views.edit, name='edit'),
    path('persons', views.persons_api, name='persons'),
    path('graph', views.graph_api, name='graph'),
    path('approve', views.approve, name='approve'),
    path('shorten', views.shorten, name='share'),
]
