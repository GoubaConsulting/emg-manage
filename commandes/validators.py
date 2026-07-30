"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Règles de validation du module Commandes.

==========================================================
"""

from django.core.exceptions import ValidationError


# ==========================================================
# PRESENCE D'AU MOINS UNE LIGNE
# ==========================================================

def verifier_presence_ligne(lignes):
    """
    Vérifie qu'une commande contient
    au moins une ligne.
    """

    if not lignes:

        raise ValidationError(
            "La commande doit contenir au moins un produit."
        )


# ==========================================================
# MONTANT
# ==========================================================

def verifier_montant(montant):
    """
    Vérifie que le montant est valide.
    """

    if montant is None:

        raise ValidationError(
            "Le montant est obligatoire."
        )

    if montant <= 0:

        raise ValidationError(
            "Le montant doit être supérieur à zéro."
        )


# ==========================================================
# PRIX
# ==========================================================

def verifier_prix(prix):
    """
    Vérifie que le prix du produit est valide.
    """

    if prix <= 0:

        raise ValidationError(
            "Le prix du produit est invalide."
        )


# ==========================================================
# TAUX DE REMISE
# ==========================================================

def verifier_taux(taux):
    """
    Vérifie le taux de remise.
    """

    if taux < 0:

        raise ValidationError(
            "Le taux de remise ne peut pas être négatif."
        )

    if taux > 100:

        raise ValidationError(
            "Le taux de remise ne peut pas dépasser 100%."
        )