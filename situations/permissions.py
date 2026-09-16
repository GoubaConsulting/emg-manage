"""
Permissions du module Situations.
"""

from comptes.permissions import (
    date_dans_delai_modification,
    est_directeur,
)


def peut_modifier_situation(
    utilisateur,
    situation
):
    """
    Seul le Directeur peut corriger une situation recente.
    """

    return (
        est_directeur(utilisateur)
        and
        situation.actif
        and
        date_dans_delai_modification(
            situation.date_situation
        )
    )


def peut_modifier_reglement_manquant(
    utilisateur,
    reglement
):
    """
    Seul le Directeur peut corriger un reglement recent.
    """

    return (
        est_directeur(utilisateur)
        and
        date_dans_delai_modification(
            reglement.date_reglement
        )
    )
