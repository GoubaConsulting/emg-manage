"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Permissions du module.

==========================================================
"""

from comptes.utils import (
    est_administrateur,
    est_directeur,
)


def peut_consulter(utilisateur):
    """
    Le Directeur consulte les mouvements de son point
    de vente. L'administrateur peut consulter l'historique.
    """

    return (
        est_directeur(utilisateur)
        or
        est_administrateur(utilisateur)
    )


def peut_creer(utilisateur):
    """
    Seul le Directeur peut creer une entree ou sortie.
    """

    return (
        est_directeur(utilisateur)
        and
        utilisateur.profil.point_vente is not None
    )
