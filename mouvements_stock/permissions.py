"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Permissions du module.

==========================================================
"""

from comptes.permissions import (
    date_dans_delai_modification,
    est_administrateur,
    est_directeur,
    point_vente_utilisateur,
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


def peut_modifier(utilisateur, mouvement):
    """
    Seul le Directeur peut corriger un mouvement recent
    rattache a son point de vente.
    """

    return (
        est_directeur(utilisateur)
        and
        mouvement.actif
        and
        mouvement.point_vente == point_vente_utilisateur(
            utilisateur
        )
        and
        date_dans_delai_modification(
            mouvement.date_mouvement
        )
    )
