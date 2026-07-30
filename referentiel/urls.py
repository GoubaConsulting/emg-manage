from django.urls import path
from . import views

urlpatterns = [

    path(
        'pointvente/',
        views.liste_pointvente,
        name='liste_pointvente'
    ),

    path(
        'pointvente/ajouter/',
        views.ajouter_pointvente,
        name='ajouter_pointvente'
    ),

    path(
        'pointvente/modifier/<int:pk>/',
        views.modifier_pointvente,
        name='modifier_pointvente'
    ),

    path(
        'pointvente/supprimer/<int:pk>/',
        views.supprimer_pointvente,
        name='supprimer_pointvente'
    ),

    # ==========================================
    # COMPAGNIES
    # ==========================================

    path(
        'compagnies/',
        views.liste_compagnie,
        name='liste_compagnie'
    ),

    path(
        'compagnies/ajouter/',
        views.ajouter_compagnie,
        name='ajouter_compagnie'
    ),

    path(
        'compagnies/modifier/<int:pk>/',
        views.modifier_compagnie,
        name='modifier_compagnie'
    ),

    path(
        'compagnies/supprimer/<int:pk>/',
        views.supprimer_compagnie,
        name='supprimer_compagnie'
    ),

    # ==========================================
    # PRODUITS
    # ==========================================

    path(
        'produits/',
        views.liste_produit,
        name='liste_produit'
    ),

    path(
        'produits/ajouter/',
        views.ajouter_produit,
        name='ajouter_produit'
    ),

    path(
        'produits/modifier/<int:pk>/',
        views.modifier_produit,
        name='modifier_produit'
    ),

    path(
        'produits/supprimer/<int:pk>/',
        views.supprimer_produit,
        name='supprimer_produit'
    ),

    # ==========================================
    # DISTRIBUTEURS
    # ==========================================

    path(
        'distributeurs/',
        views.liste_distributeur,
        name='liste_distributeur'
    ),

    path(
        'distributeurs/ajouter/',
        views.ajouter_distributeur,
        name='ajouter_distributeur'
    ),

    path(
        'distributeurs/modifier/<int:pk>/',
        views.modifier_distributeur,
        name='modifier_distributeur'
    ),

    path(
        'distributeurs/supprimer/<int:pk>/',
        views.supprimer_distributeur,
        name='supprimer_distributeur'
    ),

]


