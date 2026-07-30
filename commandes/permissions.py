"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Gestion des droits d'accès
du module Commandes.

==========================================================
"""

from comptes.permissions import (
    est_directeur,
    est_gerant,
    point_vente_utilisateur
)

from datetime import timedelta

from django.utils import timezone

from commandes.models import Commande

# ==========================================================
# CONSULTATION
# ==========================================================

def peut_consulter(utilisateur):
    """
    Les Directeurs et les Gérants
    peuvent consulter les commandes.
    """

    return (
        est_directeur(utilisateur)
        or
        est_gerant(utilisateur)
    )


# ==========================================================
# CREATION
# ==========================================================

def peut_creer(utilisateur):
    """
    Les Directeurs et les Gérants
    peuvent créer une commande.
    """

    return peut_consulter(utilisateur)


# ==========================================================
# MODIFICATION
# ==========================================================

def peut_modifier(utilisateur, commande):

    if not peut_consulter(utilisateur):
        return False

    if commande.point_vente != point_vente_utilisateur(utilisateur):
        return False

    if commande.type_commande == Commande.TYPE_DIRECTEUR:

        return (
            timezone.now().date() -
            commande.date_commande
        ).days <= 3

    if commande.type_commande == Commande.TYPE_GERANT:

        return commande.etat == Commande.EN_ATTENTE

    return False

# ==========================================================
# SUPPRESSION
# ==========================================================

def peut_supprimer(utilisateur, commande):
    """
    Les commandes ne sont jamais supprimées.
    """

    return False