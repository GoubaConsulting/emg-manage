"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Sélecteurs du module Distributions.

Toutes les lectures de la base de données
doivent être réalisées dans ce fichier.

==========================================================
"""

from django.db.models import Sum

from .models import (
    Distribution,
    LigneDistribution
)


# ==========================================================
# DISTRIBUTIONS
# ==========================================================

def get_distribution_par_id(iddistribution):
    """
    Retourne une distribution à partir de son identifiant.
    """

    return Distribution.objects.select_related(
        "commande",
        "point_vente",
        "utilisateur",
        "distributeur"
    ).get(
        pk=iddistribution
    )


def get_distribution_par_numero(numero):
    """
    Retourne une distribution à partir de son numéro.
    """

    return Distribution.objects.select_related(
        "commande",
        "point_vente",
        "utilisateur",
        "distributeur"
    ).get(
        numero=numero
    )


def get_distributions():
    """
    Retourne toutes les distributions actives.
    """

    return Distribution.objects.filter(
        actif=True
    ).select_related(
        "point_vente",
        "utilisateur",
        "distributeur"
    )


def get_distributions_point_vente(point_vente):
    """
    Retourne les distributions d'un point de vente.
    """

    return Distribution.objects.filter(
        actif=True,
        point_vente=point_vente
    ).select_related(
        "utilisateur",
        "distributeur"
    )


def get_distributions_distributeur(distributeur):
    """
    Retourne les distributions d'un distributeur.
    """

    return Distribution.objects.filter(
        actif=True,
        distributeur=distributeur
    ).select_related(
        "point_vente",
        "utilisateur"
    )


# ==========================================================
# LIGNES
# ==========================================================

def get_lignes_distribution(distribution):
    """
    Retourne toutes les lignes d'une distribution.
    """

    return LigneDistribution.objects.filter(
        distribution=distribution
    ).select_related(
        "produit"
    )


def get_ligne_distribution(distribution, produit):
    """
    Retourne la ligne correspondant à un produit.
    """

    return LigneDistribution.objects.filter(
        distribution=distribution,
        produit=produit
    ).first()


# ==========================================================
# TOTAUX
# ==========================================================

def get_total_brut(distribution):
    """
    Retourne le montant brut total.
    """

    return (
        LigneDistribution.objects.filter(
            distribution=distribution
        )
        .aggregate(
            total=Sum("montant")
        )
        .get("total")
        or 0
    )


def get_total_remise(distribution):
    """
    Retourne le montant total des remises.
    """

    return (
        LigneDistribution.objects.filter(
            distribution=distribution
        )
        .aggregate(
            total=Sum("montant_remise")
        )
        .get("total")
        or 0
    )


def get_total_net(distribution):
    """
    Retourne le montant net total.
    """

    return (
        LigneDistribution.objects.filter(
            distribution=distribution
        )
        .aggregate(
            total=Sum("montant_net")
        )
        .get("total")
        or 0
    )

from django.db.models import Prefetch

from .models import Distribution


# ==========================================================
# OBTENIR UNE DISTRIBUTION
# ==========================================================

def obtenir_distribution(id_distribution):
    """
    Retourne une distribution avec toutes
    ses informations utiles.
    """

    return (

        Distribution.objects

        .select_related(

            "commande",

            "point_vente_source",

            "point_vente_destination",

            "distributeur",

            "utilisateur_creation"

        )

        .prefetch_related(

            "lignes__produit"

        )

        .filter(

            actif=True

        )

        .get(

            id=id_distribution

        )

    )

# ==========================================================
# LISTE DES DISTRIBUTIONS
# ==========================================================

def obtenir_distributions(
    point_vente=None,
    type_distribution=None,
    etat=None
):
    """
    Retourne la liste des distributions.
    """

    distributions = (

        Distribution.objects

        .select_related(

            "commande",

            "point_vente_source",

            "point_vente_destination",

            "distributeur"

        )

        .filter(

            actif=True

        )

        .order_by(

            "-date_distribution",

            "-id"

        )

    )

    if point_vente:

        distributions = distributions.filter(

            point_vente_source=point_vente

        )

    if type_distribution:

        distributions = distributions.filter(

            type_distribution=type_distribution

        )

    if etat:

        distributions = distributions.filter(

            etat=etat

        )

    return distributions

from commandes.models import Commande


# ==========================================================
# COMMANDES DISTRIBUABLES
# ==========================================================

def obtenir_commandes_distribuables():
    """
    Retourne uniquement les commandes
    pouvant être distribuées.
    """

    return (

        Commande.objects

        .select_related(

            "point_vente"

        )

        .filter(

            actif=True,

            etat=Commande.EN_ATTENTE

        )

        .exclude(

            distribution__actif=True

        )

        .order_by(

            "date_commande"

        )

    )