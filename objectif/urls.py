"""
==========================================================
Projet : EMG MANAGE

Module : Objectif

Description :
URLs du module Objectif.

==========================================================
"""

from django.urls import path

from . import views
#from . import ajax

urlpatterns = [

    # ============================================
    # Liste
    # ============================================

    path(

        "",

        views.liste_objectif,

        name="liste_objectif"

    ),

    # ============================================
    # Ajout
    # ============================================

    path(

        "ajouter/",

        views.ajouter_objectif,

        name="ajouter_objectif"

    ),

    # ============================================
    # Modification
    # ============================================

    path(

        "modifier/<int:pk>/",

        views.modifier_objectif_view,

        name="modifier_objectif"

    ),

    # ============================================
    # Suppression
    # ============================================

    path(

        "supprimer/<int:pk>/",

        views.supprimer_objectif_view,

        name="supprimer_objectif"

    ),

]