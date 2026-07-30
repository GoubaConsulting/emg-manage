"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Gestion des permissions du module Distributions.

==========================================================
"""

from django.core.exceptions import PermissionDenied


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