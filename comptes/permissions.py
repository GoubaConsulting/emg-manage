"""
==========================================================
Projet : EMG MANAGE

Module : Comptes

Description :
Fonctions communes de gestion des droits.

==========================================================
"""


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