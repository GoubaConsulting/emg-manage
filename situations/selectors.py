"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Sélecteurs permettant de récupérer les données
nécessaires aux situations journalières.

==========================================================
"""

from django.db.models import Sum

from distributions.models import Distribution

from .models import SituationJournaliere


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