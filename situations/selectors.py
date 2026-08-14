"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Sélecteurs permettant de récupérer les données
nécessaires aux situations journalières.

==========================================================
"""

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Sum

from distributions.models import Distribution
from referentiel.models import Distributeur
from comptes.utils import (
    est_administrateur,
    est_directeur,
    est_gerant,
)

from .models import (
    SituationJournaliere,
    Manquant,
)


# ==========================================================
# DISTRIBUTIONS D'UNE JOURNEE
# ==========================================================

def distributions_du_jour(
    distributeur,
    date_situation
):
    """
    Retourne toutes les distributions actives
    d'un distributeur pour une date donnée.
    """

    return (
        Distribution.objects

        .filter(
            distributeur=distributeur,
            date_distribution=date_situation,
            actif=True,
        )

        .select_related(
            "point_vente_source",
            "point_vente_destination",
            "distributeur",
            "utilisateur",
        )

        .prefetch_related(
            "lignes__produit__compagnie",
        )

        .order_by(
            "date_distribution",
            "iddistribution",
        )
    )


# ==========================================================
# TOTAL DES DISTRIBUTIONS
# ==========================================================

def total_distributions_du_jour(
    distributeur,
    date_situation
):
    """
    Retourne le montant net total des distributions
    du distributeur pour la date sélectionnée.
    """

    resultat = (

        Distribution.objects

        .filter(
            distributeur=distributeur,
            date_distribution=date_situation,
            actif=True,
        )

        .aggregate(
            total=Sum("montant_net")
        )

    )

    return resultat["total"] or 0


# ==========================================================
# SITUATION EXISTANTE
# ==========================================================

def situation_existante(
    distributeur,
    date_situation
):
    """
    Recherche une situation journalière existante
    pour un distributeur et une date donnés.
    """

    return (
        SituationJournaliere.objects

        .filter(
            distributeur=distributeur,
            date_situation=date_situation,
            actif=True,
        )

        .prefetch_related(
            "lignes__produit__compagnie",
        )

        .first()
    )


# ==========================================================
# SITUATION CLOTUREE
# ==========================================================

def situation_cloturee(
    distributeur,
    date_situation
):
    """
    Vérifie si une situation clôturée existe
    pour le distributeur et la date donnée.
    """

    return (
        SituationJournaliere.objects

        .filter(
            distributeur=distributeur,
            date_situation=date_situation,
            etat=SituationJournaliere.ETAT_CLOTUREE,
            actif=True,
        )

        .first()
    )


# ==========================================================
# QUERYSETS PRINCIPAUX
# ==========================================================

def situations_queryset():
    """
    Retourne les situations actives optimisées.
    """

    return (
        SituationJournaliere.objects
        .filter(
            actif=True
        )
        .select_related(
            "distributeur",
            "point_vente",
            "utilisateur",
        )
        .prefetch_related(
            "lignes__produit__compagnie",
            "manquant",
        )
    )


def manquants_queryset():
    """
    Retourne les manquants optimisés.
    """

    return (
        Manquant.objects
        .select_related(
            "situation",
            "distributeur",
            "utilisateur",
        )
        .prefetch_related(
            "reglements",
        )
    )


def gerants_distribues_par_directeur(utilisateur):
    """
    Retourne les gérants auxquels le Directeur
    a déjà fait une distribution.
    """

    return (
        Distribution.objects
        .filter(
            utilisateur=utilisateur,
            distributeur__categorie=(
                Distributeur.CATEGORIE_GERANT
            ),
            actif=True,
        )
        .values_list(
            "distributeur_id",
            flat=True
        )
        .distinct()
    )


# ==========================================================
# VISIBILITE
# ==========================================================

def situations_visibles(utilisateur):
    """
    Retourne les situations visibles par profil.
    """

    queryset = situations_queryset()

    if est_administrateur(utilisateur):

        return queryset

    if est_directeur(utilisateur):

        return queryset.filter(
            distributeur_id__in=(
                gerants_distribues_par_directeur(
                    utilisateur
                )
            ),
            distributeur__categorie=(
                Distributeur.CATEGORIE_GERANT
            ),
        )

    if est_gerant(utilisateur):

        return queryset.filter(
            distributeur__categorie=(
                Distributeur.CATEGORIE_DISTRIBUTEUR
            ),
            distributeur__point_vente=(
                utilisateur.profil.point_vente
            ),
        )

    return queryset.none()


def manquants_visibles(utilisateur):
    """
    Retourne les manquants visibles par profil.
    """

    queryset = manquants_queryset()

    if est_administrateur(utilisateur):

        return queryset

    if est_directeur(utilisateur):

        return queryset.filter(
            distributeur_id__in=(
                gerants_distribues_par_directeur(
                    utilisateur
                )
            ),
            distributeur__categorie=(
                Distributeur.CATEGORIE_GERANT
            ),
        )

    if est_gerant(utilisateur):

        return queryset.filter(
            distributeur__categorie=(
                Distributeur.CATEGORIE_DISTRIBUTEUR
            ),
            distributeur__point_vente=(
                utilisateur.profil.point_vente
            ),
        )

    return queryset.none()


# ==========================================================
# PAGINATION
# ==========================================================

def paginer(queryset, page):
    """
    Pagine un queryset.
    """

    taille = getattr(
        settings,
        "NB_LIGNES_PAR_PAGE",
        20
    )

    return Paginator(
        queryset,
        taille
    ).get_page(
        page
    )
