"""
Services métier du référentiel.
"""

from .models import Distributeur
from comptes.utils import (
    est_direction,
    point_vente_utilisateur
)


def distributeurs_visibles(utilisateur):
    """
    Retourne les distributeurs visibles
    selon le profil connecté.
    """

    if est_direction(utilisateur):

        return (
            Distributeur.objects
            .filter(actif=True)
            .select_related("point_vente")
            .order_by("nom", "prenom")
        )

    return (
        Distributeur.objects
        .filter(
            actif=True,
            point_vente=point_vente_utilisateur(utilisateur)
        )
        .select_related("point_vente")
        .order_by("nom", "prenom")
    )