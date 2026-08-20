"""
Services métier du référentiel.
"""

from .models import Distributeur
from comptes.utils import (
    est_direction,
    point_vente_utilisateur
)


def distributeurs_visibles(
    utilisateur,
    actif=True
):
    """
    Retourne les distributeurs visibles
    selon le profil connecté.
    """

    categories = [
        Distributeur.CATEGORIE_GERANT,
        Distributeur.CATEGORIE_DISTRIBUTEUR,
    ]

    filtres = {
        "actif": actif,
        "categorie__in": categories,
    }

    if not est_direction(utilisateur):

        filtres["point_vente"] = point_vente_utilisateur(
            utilisateur
        )

    return (
        Distributeur.objects
        .filter(
            **filtres
        )
        .select_related("point_vente")
        .order_by("nom", "prenom")
    )
