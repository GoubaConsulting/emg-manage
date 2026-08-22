"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Fonctions de calcul du module Situations.

==========================================================
"""

from decimal import Decimal


# ==========================================================
# CALCUL DU CREDIT
# ==========================================================

def calculer_credit(
    montant_total_distribue,
    fond
):
    """
    Calcule le crédit généré par les distributions
    de la journée.

    Le crédit correspond à la partie du montant
    total distribué qui dépasse le fond.
    """

    montant_total_distribue = Decimal(
        str(montant_total_distribue)
    )

    fond = Decimal(
        str(fond)
    )

    credit = (
        montant_total_distribue - fond
    )

    if credit < 0:

        credit = Decimal("0.00")

    return credit


# ==========================================================
# CALCUL DU TOTAL VERSE
# ==========================================================

def calculer_montant_total_verse(
    montant_credit_verse,
    montant_vente_verse
):
    """
    Calcule le montant total versé.

    Total versé =
        crédit versé + ventes versées
    """

    montant_credit_verse = Decimal(
        str(montant_credit_verse)
    )

    montant_vente_verse = Decimal(
        str(montant_vente_verse)
    )

    return (
        montant_credit_verse
        +
        montant_vente_verse
    )


# ==========================================================
# CALCUL DU MONTANT DES PRODUITS RESTANTS
# ==========================================================

def calculer_montant_produits_restants(
    lignes
):
    """
    Calcule la valeur des produits restant
    chez le distributeur.

    Chaque ligne doit fournir :

        quantite_restante
        prix_unitaire
    """

    total = Decimal("0.00")

    for ligne in lignes:

        quantite = Decimal(
            str(
                ligne["quantite_restante"]
            )
        )

        prix = Decimal(
            str(
                ligne["prix_unitaire"]
            )
        )

        taux_remise = Decimal(
            str(
                ligne.get(
                    "taux_remise",
                    0
                )
            )
        )

        montant_brut = (
            quantite * prix
        )

        total += (
            montant_brut
            -
            (
                montant_brut
                *
                taux_remise
                /
                Decimal("100")
            )
        )

    return total


# ==========================================================
# CALCUL DU MANQUANT
# ==========================================================

def calculer_manquant(
    montant_total_distribue,
    montant_credit_verse,
    montant_vente_verse
):
    """
    Calcule le montant manquant.

    Le montant distribue doit etre justifie par :

        credit verse + ventes versees

    Si cette somme est inferieure au montant distribue,
    la différence constitue un manquant.
    """

    montant_total_distribue = Decimal(
        str(montant_total_distribue)
    )

    montant_credit_verse = Decimal(
        str(montant_credit_verse)
    )

    montant_vente_verse = Decimal(
        str(montant_vente_verse)
    )

    manquant = (

        montant_total_distribue

        -

        montant_credit_verse

        -

        montant_vente_verse

    )

    if manquant < 0:

        manquant = Decimal("0.00")

    return manquant


# ==========================================================
# VALIDATION DU VERSEMENT DU CREDIT
# ==========================================================

def verifier_versement_credit(
    montant_credit,
    montant_credit_verse
):
    """
    Vérifie que le crédit est entièrement payé
    au moment de la clôture.
    """

    montant_credit = Decimal(
        str(montant_credit)
    )

    montant_credit_verse = Decimal(
        str(montant_credit_verse)
    )

    if montant_credit_verse < montant_credit:

        raise ValueError(

            "Le crédit doit être entièrement "
            "versé avant la clôture de la situation."

        )

    return True
