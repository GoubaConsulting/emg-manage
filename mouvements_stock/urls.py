"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

URLs du module.
==========================================================
"""

from django.urls import path

from . import views


app_name = "mouvements_stock"


urlpatterns = [

    path(
        "",
        views.liste_mouvements,
        name="liste_mouvements"
    ),

    path(
        "ajouter/",
        views.ajouter_mouvement,
        name="ajouter_mouvement"
    ),

]
