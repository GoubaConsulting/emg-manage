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
    date_dans_delai_modification,
    est_directeur,
    est_gerant,
    point_vente_utilisateur
)

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

def commande_gerant_modifiable_par_directeur(commande):
    """
    Une commande gerant peut etre corrigee par le Directeur
    tant qu'elle n'est pas rattachee a une distribution cloturee.
    """

    if (
        commande.type_commande != Commande.TYPE_GERANT
        or
        commande.categorie_commande != Commande.CATEGORIE_NORMALE
    ):

        return False

    if commande.etat == Commande.VALIDEE_PARTIELLEMENT:

        return False

    if not date_dans_delai_modification(
        commande.date_commande
    ):

        return False

    if not commande.pk:

        return True

    return not commande.distributions.filter(
        etat="CLOTUREE"
    ).exists()



# ==========================================================
# CORRECTION D'UNE COMMANDE GERANT PAR LE DIRECTEUR
# ==========================================================

def peut_corriger_par_directeur(
    utilisateur,
    commande
):
    """
    Autorise le Directeur à corriger
    une commande normale enregistrée par un Gérant.
    """

    if not est_directeur(utilisateur):
        return False

    if commande.type_commande != Commande.TYPE_GERANT:
        return False

    if commande.categorie_commande != Commande.CATEGORIE_NORMALE:
        return False

    if not commande.actif:
        return False

    return True


# ==========================================================
# Qui peut modifier
# ==========================================================

def peut_modifier(utilisateur, commande):

    if not peut_consulter(utilisateur):
        return False

    if (
        est_directeur(utilisateur)
        and
        commande.type_commande == Commande.TYPE_GERANT
    ):

        return commande_gerant_modifiable_par_directeur(
            commande
        )

    if not est_directeur(utilisateur):

        return False

    if commande.point_vente != point_vente_utilisateur(utilisateur):
        return False

    if commande.type_commande == Commande.TYPE_DIRECTEUR:

        return date_dans_delai_modification(
            commande.date_commande
        )

    if commande.type_commande == Commande.TYPE_GERANT:

        return False

    return False

# ==========================================================
# CORRECTION PAR LE DIRECTEUR
# ==========================================================

def peut_corriger_par_directeur(
    utilisateur,
    commande
):

    if not est_directeur(utilisateur):
        return False

    if commande.type_commande != Commande.TYPE_GERANT:
        return False

    if commande.categorie_commande != Commande.CATEGORIE_NORMALE:
        return False

    if not commande.actif:
        return False

    return True


# ==========================================================
# SUPPRESSION
# ==========================================================

def peut_supprimer(utilisateur, commande):
    """
    Les commandes ne sont jamais supprimées.
    """

    return False
