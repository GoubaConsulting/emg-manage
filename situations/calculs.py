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

def convertir_montant_brut_en_net(
    montant_brut,
    total_brut_reference,
    total_net_reference
):
    """
    Convertit un montant brut global en equivalent net
    avec le coefficient net de la situation.
    """

    montant_brut = Decimal(
        str(montant_brut or "0")
    )

    total_brut_reference = Decimal(
        str(total_brut_reference or "0")
    )

    total_net_reference = Decimal(
        str(total_net_reference or "0")
    )

    if montant_brut <= 0:

        return Decimal("0.00")

    if total_brut_reference <= 0:

        return montant_brut

    return (
        montant_brut
        *
        total_net_reference
        /
        total_brut_reference
    )


def calculer_manquant(
    montant_total_distribue,
    montant_credit_verse,
    montant_vente_verse,
    montant_restant=0
):
    """
    Calcule le montant manquant.

    Les montants transmis doivent etre sur la meme base
    de calcul. Pour les versements, on utilise maintenant
    la base nette.

        credit verse + ventes versees + montant restant

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

    montant_restant = Decimal(
        str(montant_restant)
    )

    manquant = (

        montant_total_distribue

        -

        montant_credit_verse

        -

        montant_vente_verse

        -

        montant_restant

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
