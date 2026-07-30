"""
Fonctions utilitaires relatives aux utilisateurs.
"""


def est_administrateur(user):
    """
    Vérifie si l'utilisateur connecté est Administrateur.
    """

    return (
        user.is_authenticated
        and user.profil.role == "ADMIN"
    )


def est_directeur(user):
    """
    Vérifie si l'utilisateur connecté est Directeur.
    """

    return (
        user.is_authenticated
        and user.profil.role == "DIRECTEUR"
    )


def est_gerant(user):
    """
    Vérifie si l'utilisateur connecté est Gérant.
    """

    return (
        user.is_authenticated
        and user.profil.role == "GERANT"
    )


def point_vente_utilisateur(user):
    """
    Retourne le point de vente de l'utilisateur connecté.
    """

    return user.profil.point_vente


def est_direction(user):
    """
    Les utilisateurs de direction sont
    l'Administrateur et le Directeur.
    """

    return (
        est_administrateur(user)
        or est_directeur(user)
    )