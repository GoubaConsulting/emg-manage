"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Fonctions de consultation des commandes.

==========================================================
"""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from datetime import date

from comptes.permissions import (
    est_directeur,
    est_gerant,
    point_vente_utilisateur
)

from .models import Commande


def date_iso_ou_none(valeur):
    """
    Convertit une valeur ISO issue des filtres GET.
    """

    if not valeur:

        return None

    if hasattr(
        valeur,
        "year"
    ):

        return valeur

    try:

        return date.fromisoformat(
            str(valeur)
        )

    except ValueError:

        return None


def texte_recherche(valeur):
    """
    Nettoie une valeur texte issue des filtres GET.
    """

    valeur = str(
        valeur or ""
    ).strip()

    if valeur.lower() == "none":

        return ""

    return valeur


# ==========================================================
# QUERYSET PRINCIPAL
# ==========================================================

def commandes_queryset():
    """
    Retourne le queryset principal.
    """

    return (

        Commande.objects

        .select_related(
            "point_vente",
            "utilisateur"
        )

        .prefetch_related(
            "lignes",
            "lignes__produit",
            "lignes__produit__compagnie"
        )

        .filter(
            actif=True
        )

    )


# ==========================================================
# COMMANDES VISIBLES
# ==========================================================

def commandes_visibles(utilisateur):
    """
    Retourne les commandes visibles
    par l'utilisateur connecté.
    """

    queryset = commandes_queryset()

    if est_directeur(utilisateur):

        return queryset.filter(

            point_vente=point_vente_utilisateur(
                utilisateur
            )

        )

    if est_gerant(utilisateur):

        return queryset.filter(

            point_vente=point_vente_utilisateur(
                utilisateur
            )

        )

    return queryset.none()


# ==========================================================
# RECHERCHE
# ==========================================================

def rechercher_commandes(
    utilisateur,
    categorie_commande=None,
    numero=None,
    date_commande=None,
    date_debut=None,
    date_fin=None,
    etat=None
):
    """
    Recherche de commandes.
    """

    queryset = commandes_visibles(
        utilisateur
    )

    numero = texte_recherche(
        numero
    )

    date_commande = date_iso_ou_none(
        date_commande
    )

    date_debut = date_iso_ou_none(
        date_debut
    )

    date_fin = date_iso_ou_none(
        date_fin
    )

    if categorie_commande:

        queryset = queryset.filter(
            categorie_commande=categorie_commande
        )

    if numero:

        queryset = queryset.filter(
            numero__icontains=numero
        )

    if date_commande:

        queryset = queryset.filter(
            date_commande=date_commande
        )

    else:

        if date_debut:

            queryset = queryset.filter(
                date_commande__gte=date_debut
            )

        if date_fin:

            queryset = queryset.filter(
                date_commande__lte=date_fin
            )
    
    if etat:

        queryset = queryset.filter(
            etat=etat
        )

    return queryset.order_by(

        "-date_commande",
        "-idcommande"

    )



# ==========================================================
# RECHERCHE COMMANDES NORMALES
# ==========================================================

def rechercher_commandes_normales(
    utilisateur,
    numero=None,
    date_commande=None,
    date_debut=None,
    date_fin=None
):
    """
    Recherche uniquement les commandes normales.
    """

    queryset = commandes_visibles(
        utilisateur
    ).filter(
        categorie_commande=Commande.CATEGORIE_NORMALE
    )

    numero = texte_recherche(
        numero
    )

    date_commande = date_iso_ou_none(
        date_commande
    )

    date_debut = date_iso_ou_none(
        date_debut
    )

    date_fin = date_iso_ou_none(
        date_fin
    )

    if numero:

        queryset = queryset.filter(
            numero__icontains=numero
        )

    if date_commande:

        queryset = queryset.filter(
            date_commande=date_commande
        )

    else:

        if date_debut:

            queryset = queryset.filter(
                date_commande__gte=date_debut
            )

        if date_fin:

            queryset = queryset.filter(
                date_commande__lte=date_fin
            )

    return queryset.order_by(

        "-date_commande",

        "-idcommande"

    )


# ==========================================================
# COMMANDE PAR ID
# ==========================================================

def commande_par_id(
    utilisateur,
    pk
):
    """
    Retourne une commande
    appartenant à l'utilisateur.
    """

    return get_object_or_404(

        commandes_visibles(
            utilisateur
        ),

        pk=pk

    )


# ==========================================================
# PAGINATION
# ==========================================================

def paginer(
    queryset,
    page,
    taille=20
):
    """
    Pagination des commandes.
    """

    paginator = Paginator(
        queryset,
        taille
    )

    return paginator.get_page(page)

# ==========================================================
# COMMANDES EN ATTENTE
# ==========================================================

def commandes_en_attente(utilisateur):
    """
    Retourne les commandes en attente
    visibles par le Directeur.
    """

    if not est_directeur(utilisateur):

        return Commande.objects.none()

    return (

        commandes_queryset()

        .filter(

            etat=Commande.EN_ATTENTE

        )

        .order_by(

            "date_creation"

        )

    )


# ==========================================================
# NOMBRE DE COMMANDES EN ATTENTE
# ==========================================================

def nombre_commandes_en_attente(utilisateur):
    """
    Nombre de commandes en attente.
    """

    return commandes_en_attente(

        utilisateur

    ).count()
