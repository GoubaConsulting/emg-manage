"""
==========================================================
Projet : EMG MANAGE

Module : Comptes

Description :
Fonctions communes de gestion des droits.

==========================================================
"""

from django.utils import timezone


DELAI_MODIFICATION_OPERATION_JOURS = 3


# ==========================================================
# ADMINISTRATEUR
# ==========================================================

def est_administrateur(utilisateur):

    return (
        utilisateur.is_authenticated
        and utilisateur.profil.role == "ADMIN"
    )


# ==========================================================
# DIRECTEUR
# ==========================================================

def est_directeur(utilisateur):

    return (
        utilisateur.is_authenticated
        and utilisateur.profil.role == "DIRECTEUR"
    )


# ==========================================================
# GERANT
# ==========================================================

def est_gerant(utilisateur):

    return (
        utilisateur.is_authenticated
        and utilisateur.profil.role == "GERANT"
    )


# ==========================================================
# EXPLOITATION
# ==========================================================

def est_exploitation(utilisateur):
    """
    Retourne True pour les utilisateurs
    participant à l'exploitation.
    """

    return (
        est_directeur(utilisateur)
        or est_gerant(utilisateur)
    )


# ==========================================================
# POINT DE VENTE
# ==========================================================

def point_vente_utilisateur(utilisateur):
    """
    Retourne le point de vente
    de l'utilisateur connecté.
    """

    return utilisateur.profil.point_vente


# ==========================================================
# DELAI DE MODIFICATION
# ==========================================================

def date_dans_delai_modification(
    date_operation,
    jours=DELAI_MODIFICATION_OPERATION_JOURS
):
    """
    Retourne True si une operation est encore modifiable.
    """

    if date_operation is None:

        return False

    if hasattr(
        date_operation,
        "date"
    ):

        date_operation = date_operation.date()

    ecart = (
        timezone.localdate()
        -
        date_operation
    ).days

    return (
        0 <= ecart <= jours
    )
