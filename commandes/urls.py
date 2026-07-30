"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
URLs du module Commandes.

==========================================================
"""

from django.urls import path

from . import views


urlpatterns = [

    # ======================================================
    # Liste
    # ======================================================

    path(

        "",

        views.liste_commandes,

        name="liste_commandes"

    ),

    # ======================================================
    # VALIDATION DES COMMANDES GERANT
    # ======================================================

    path(

        "validation/",

        views.liste_validation_commandes,

        name="liste_validation_commandes"

    ),

    # ======================================================
    # Ajout
    # ======================================================

    path(

        "ajouter/",

        views.ajouter_commande,

        name="ajouter_commande"

    ),

    # ======================================================
    # Modification
    # ======================================================

    path(

        "modifier/<int:pk>/",

        views.modifier_commande_view,

        name="modifier_commande"

    ),

    path(

        "en-attente/",

        views.commandes_en_attente_view,

        name="commandes_en_attente"

    ),

    path(

        "gerant/ajouter/",

        views.ajouter_commande_gerant,

        name="ajouter_commande_gerant"

    ),

    path(

        "stock-tampon/",

        views.ajouter_commande_stock_tampon,

        name="ajouter_commande_stock_tampon"

    ),

    path(

        "stock-tampon/liste/",

        views.liste_commandes_stock_tampon,

        name="liste_commandes_stock_tampon"

    ),
    # ======================================================
    # COMMANDES CAUTION BANCAIRE
    # ======================================================

    path(

        "caution/liste/",

        views.liste_commandes_caution,

        name="liste_commandes_caution"

    ),

    path(

        "caution/ajouter/",

        views.ajouter_commande_caution,

        name="ajouter_commande_caution"

    ),


    # ======================================================
    # REGLEMENT STOCK TAMPON
    # ======================================================

    path(

        "reglement-stock/liste/",

        views.liste_reglement_stock,

        name="liste_reglement_stock"

    ),

    path(

        "reglement-stock/ajouter/",

        views.ajouter_reglement_stock,

        name="ajouter_reglement_stock"

    ),

    path(
        "stock-tampon/modifier/<int:pk>/",
        views.modifier_commande_stock_tampon_view,
        name="modifier_commande_stock_tampon"
    ),

    path(
        "commandes/caution/<int:pk>/modifier/",
        views.modifier_commande_caution_view,
        name="modifier_commande_caution",
    ),

    path(

        "reglement-stock/<int:pk>/modifier/",

        views.modifier_reglement_stock_tampon_view,

        name="modifier_reglement_stock_tampon"

    ),

    path(
        "validation/<int:pk>/valider/",
        views.valider_commande_gerant_view,
        name="valider_commande_gerant",
    ),

    path(
        "validation/<int:pk>/rejeter/",
        views.rejeter_commande_gerant_view,
        name="rejeter_commande_gerant",
    ),


    path(
        "<int:commande_id>/valider/",
        views.valider_commande_directeur,
        name="valider_commande_directeur",
    ),

]