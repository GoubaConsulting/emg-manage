"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Fonctions de calcul du module Commandes.

==========================================================
"""

from decimal import Decimal


# ==========================================================
# QUANTITE
# ==========================================================

def calculer_quantite(
    montant,
    prix_unitaire
):
    """
    Calcule automatiquement
    la quantité commandée.
    """

    if prix_unitaire == 0:

        return Decimal("0")

    return Decimal(montant) / Decimal(prix_unitaire)


# ==========================================================
# REMISE
# ==========================================================

def calculer_remise(
    montant,
    taux
):
    """
    Calcule le montant
    de la remise.
    """

    return Decimal(montant) * Decimal(taux) / Decimal("100")


# ==========================================================
# MONTANT NET
# ==========================================================

def calculer_montant_net(
    montant,
    remise
):
    """
    Retourne le montant net
    d'une ligne.
    """

    return Decimal(montant) - Decimal(remise)


# ==========================================================
# TOTAL BRUT
# ==========================================================

def calculer_total_brut(
    lignes
):
    """
    Calcule le montant brut
    de la commande.
    """

    total = Decimal("0")

    for ligne in lignes:

        total += ligne["montant"]

    return total


# ==========================================================
# TOTAL NET
# ==========================================================

def calculer_total_net(
    lignes
):
    """
    Calcule le montant net
    de la commande.
    """

    total = Decimal("0")

    for ligne in lignes:

        total += ligne["montant_net"]

    return total