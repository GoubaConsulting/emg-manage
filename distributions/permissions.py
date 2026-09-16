"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Gestion des permissions du module Distributions.

==========================================================
"""

from django.core.exceptions import PermissionDenied

from comptes.permissions import (
    date_dans_delai_modification,
    est_directeur,
)

from .models import Distribution


# ==========================================================
# CREATION
# ==========================================================

def verifier_creation_distribution(utilisateur):
    """
    Vérifie que l'utilisateur peut créer
    une distribution.
    """

    if not utilisateur.is_authenticated:

        raise PermissionDenied(
            "Vous devez être connecté."
        )


# ==========================================================
# CONSULTATION
# ==========================================================

def verifier_consultation_distribution(utilisateur):
    """
    Vérifie que l'utilisateur peut consulter
    les distributions.
    """

    if not utilisateur.is_authenticated:

        raise PermissionDenied(
            "Vous devez être connecté."
        )


# ==========================================================
# MODIFICATION
# ==========================================================

def verifier_modification_distribution(utilisateur):
    """
    Vérifie que l'utilisateur peut modifier
    une distribution.
    """

    if not utilisateur.is_authenticated:

        raise PermissionDenied(
            "Vous devez être connecté."
        )


def peut_modifier_distribution(
    utilisateur,
    distribution
):
    """
    Seul le Directeur peut modifier une distribution
    dans le delai autorise.
    """

    if not est_directeur(
        utilisateur
    ):

        return False

    if not date_dans_delai_modification(
        distribution.date_distribution
    ):

        return False

    if distribution.type_distribution == (
        Distribution.TYPE_COMMANDE_GERANT
    ):

        return False

    if (
        distribution.type_distribution
        ==
        Distribution.TYPE_DISTRIBUTEUR
        and
        distribution.etat != Distribution.ETAT_OUVERTE
    ):

        return False

    return distribution.actif


# ==========================================================
# SUPPRESSION
# ==========================================================

def verifier_suppression_distribution(utilisateur):
    """
    Vérifie que l'utilisateur peut supprimer
    une distribution.
    """

    if not utilisateur.is_authenticated:

        raise PermissionDenied(
            "Vous devez être connecté."
        )
