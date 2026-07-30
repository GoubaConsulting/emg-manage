"""
==========================================================
Projet : EMG MANAGE

Module : Objectif

Description :
Gestion des permissions du module Objectif.

==========================================================
"""

from comptes.utils import (
    est_administrateur,
    est_directeur,
    est_gerant
)


# ==========================================================
# Consultation
# ==========================================================

def peut_consulter(utilisateur):
    """
    Tous les utilisateurs connectés
    peuvent consulter leurs objectifs.
    """

    return (
        est_administrateur(utilisateur)
        or est_directeur(utilisateur)
        or est_gerant(utilisateur)
    )


# ==========================================================
# Création
# ==========================================================

def peut_creer(utilisateur):
    """
    Seuls le Directeur et le Gérant
    peuvent créer un objectif.

    L'administrateur n'est rattaché
    à aucun point de vente.
    """

    return (
        est_directeur(utilisateur)
        or est_gerant(utilisateur)
    )


# ==========================================================
# Modification
# ==========================================================

def peut_modifier(utilisateur, objectif):
    """
    Le Directeur peut modifier
    uniquement les objectifs de la Direction.

    Le Gérant uniquement ceux
    de son point de vente.
    """

    if est_directeur(utilisateur):

        return (
            utilisateur.profil.point_vente
            ==
            objectif.point_vente
        )

    if est_gerant(utilisateur):

        return (
            utilisateur.profil.point_vente
            ==
            objectif.point_vente
        )

    return False


# ==========================================================
# Suppression
# ==========================================================

def peut_supprimer(utilisateur, objectif):
    """
    Même règle que la modification.
    """

    return peut_modifier(
        utilisateur,
        objectif
    )


# ==========================================================
# Visualisation d'un objectif
# ==========================================================

def peut_voir(utilisateur, objectif):
    """
    L'administrateur voit tout.

    Le Directeur voit tous les objectifs.

    Le Gérant uniquement
    ceux de son point de vente.
    """

    if est_administrateur(utilisateur):

        return True

    if est_directeur(utilisateur):

        return True

    return (
        utilisateur.profil.point_vente
        ==
        objectif.point_vente
    )