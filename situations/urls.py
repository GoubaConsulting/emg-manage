"""
==========================================================
Projet : EMG MANAGE

Module : Situations

URLs du module Situations.
==========================================================
"""

from django.urls import path

from . import views


app_name = "situations"


urlpatterns = [

    path(

        "",

        views.liste_situations,

        name="liste_situations"

    ),

    path(

        "ajouter/",

        views.ajouter_situation,

        name="ajouter_situation"

    ),

    path(

        "manquants/",

        views.liste_manquants,

        name="liste_manquants"

    ),

    path(

        "manquants/reglements/",

        views.liste_reglements_manquants,

        name="liste_reglements_manquants"

    ),

    path(

        "manquants/<int:pk>/regler/",

        views.regler_manquant_view,

        name="regler_manquant"

    ),


]
