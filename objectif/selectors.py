"""
==========================================================
Projet : EMG MANAGE

Module : Objectif

Description :
Toutes les requêtes de lecture du module Objectif.

==========================================================
"""

from django.conf import settings
from django.core.paginator import Paginator

from comptes.utils import (
    est_administrateur,
    est_directeur
)

from .models import Objectif


# ==========================================================
# Requête de base
# ==========================================================

def objectifs_queryset():
    """
    Requête de base optimisée.
    """

    return (

        Objectif.objects

        .filter(
            actif=True
        )

        .select_related(
            "compagnie",
            "point_vente"
        )

        .prefetch_related(
            "lignes",
            "lignes__produit"
        )

    )


# ==========================================================
# Objectifs visibles par l'utilisateur
# ==========================================================

def objectifs_visibles(utilisateur):
    """
    Retourne les objectifs visibles
    selon le profil de l'utilisateur.
    """

    queryset = objectifs_queryset()

    if (
        est_administrateur(utilisateur)
        or
        est_directeur(utilisateur)
    ):

        return queryset

    return queryset.filter(
        point_vente=utilisateur.profil.point_vente
    )


# ==========================================================
# Recherche
# ==========================================================

def rechercher_objectifs(
    utilisateur,
    designation=None,
    mois=None,
    annee=None,
    point_vente=None
):
    """
    Recherche multicritère.
    """

    queryset = objectifs_visibles(
        utilisateur
    )

    if designation:

        queryset = queryset.filter(
            designation__icontains=designation
        )

    if mois:

        queryset = queryset.filter(
            mois=mois
        )

    if annee:

        queryset = queryset.filter(
            annee=annee
        )

    if (
        point_vente
        and
        (
            est_administrateur(utilisateur)
            or
            est_directeur(utilisateur)
        )
    ):

        queryset = queryset.filter(
            point_vente=point_vente
        )

    return queryset.order_by(

        "-annee",

        "-mois",

        "designation"

    )


# ==========================================================
# Pagination
# ==========================================================

def paginer(queryset, page):
    """
    Pagination des résultats.
    """

    nb = getattr(
        settings,
        "NB_LIGNES_PAR_PAGE",
        20
    )

    paginator = Paginator(

        queryset,

        nb

    )

    return paginator.get_page(
        page
    )

# ==========================================================
# Recherche d'un objectif
# ==========================================================

from django.shortcuts import get_object_or_404


def objectif_par_id(utilisateur, pk):
    """
    Retourne un objectif visible
    par l'utilisateur.
    """

    return get_object_or_404(

        objectifs_visibles(
            utilisateur
        ),

        pk=pk

    )