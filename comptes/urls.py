from django.urls import path
from . import views

urlpatterns = [

    path(
        'login/',
        views.connexion,
        name='login'
    ),

    path(
        'logout/',
        views.deconnexion,
        name='logout'
    ),

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

]