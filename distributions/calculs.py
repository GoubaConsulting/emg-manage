"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Fonctions de calcul des montants d'une distribution.

==========================================================
"""

from decimal import Decimal


# ==========================================================
# CALCUL DU MONTANT D'UNE LIGNE
# ==========================================================

def calculer_montant(prix_unitaire, quantite):
    """
    Calcule le montant brut d'une ligne.
    """

    return Decimal(prix_unitaire) * Decimal(quantite)


# ==========================================================
# CALCUL DE LA REMISE
# ==========================================================

def calculer_montant_remise(montant, taux_remise):
    """
    Calcule le montant de la remise.
    """

    return (
        Decimal(montant)
        * Decimal(taux_remise)
        / Decimal("100")
    )


# ==========================================================
# CALCUL DU MONTANT NET
# ==========================================================

def calculer_montant_net(montant, montant_remise):
    """
    Calcule le montant net d'une ligne.
    """

    return Decimal(montant) - Decimal(montant_remise)


# ==========================================================
# TOTAL BRUT
# ==========================================================

def calculer_total_brut(lignes):
    """
    Calcule le montant brut de la distribution.
    """

    return sum(
        ligne.montant
        for ligne in lignes
    )


# ==========================================================
# TOTAL REMISE
# ==========================================================

def calculer_total_remise(lignes):
    """
    Calcule le total des remises.
    """

    return sum(
        ligne.montant_remise
        for ligne in lignes
    )


# ==========================================================
# TOTAL NET
# ==========================================================

def calculer_total_net(lignes):
    """
    Calcule le montant net total de la distribution.
    """

    return sum(
        ligne.montant_net
        for ligne in lignes
    )