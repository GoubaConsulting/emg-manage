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

        "gerant/",

        views.liste_situations_gerant,

        name="liste_situations_gerant"

    ),

    path(

        "gerant/versement/",

        views.versement_gerant,

        name="versement_gerant"

    ),

    path(

        "gerant/versement/<int:pk>/valider/",

        views.valider_versement_gerant_view,

        name="valider_versement_gerant"

    ),

    path(

        "gerant/versement/<int:pk>/rejeter/",

        views.rejeter_versement_gerant_view,

        name="rejeter_versement_gerant"

    ),

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

        "modifier/<int:pk>/",

        views.modifier_situation_view,

        name="modifier_situation"

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

        "manquants/reglements/<int:pk>/modifier/",

        views.modifier_reglement_manquant_view,

        name="modifier_reglement_manquant"

    ),

    path(

        "manquants/<int:pk>/regler/",

        views.regler_manquant_view,

        name="regler_manquant"

    ),


]
