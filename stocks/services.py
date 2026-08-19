"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Services métier du module Stocks.

==========================================================
"""

from decimal import Decimal

from django.db import transaction

from .models import (
    Stock,
    TYPE_NORMAL,
    TYPE_TAMPON
)


def _decimal(valeur):
    """
    Retourne une valeur Decimal exploitable pour les affichages.
    """

    return Decimal(str(valeur or "0"))


def taux_derniere_commande_directeur_par_produit(produit_ids):
    """
    Retourne le dernier taux applique par le Directeur
    pour chaque produit donne.
    """

    from commandes.models import (
        Commande,
        LigneCommande
    )

    produit_ids = list(
        produit_ids
    )

    if not produit_ids:

        return {}

    lignes = (
        LigneCommande.objects
        .filter(
            produit_id__in=produit_ids,
            commande__actif=True,
            commande__type_commande=Commande.TYPE_DIRECTEUR,
            commande__categorie_commande__in=[
                Commande.CATEGORIE_NORMALE,
                Commande.CATEGORIE_STOCK_TAMPON,
                Commande.CATEGORIE_CAUTION,
            ],
            commande__etat__in=[
                Commande.VALIDEE,
                Commande.VALIDEE_PARTIELLEMENT,
            ],
        )
        .select_related(
            "commande"
        )
        .order_by(
            "produit_id",
            "-commande__date_commande",
            "-commande__date_validation",
            "-commande__idcommande",
            "-idlignecommande",
        )
    )

    taux_par_produit = {}

    for ligne in lignes:

        if ligne.produit_id not in taux_par_produit:

            taux_par_produit[ligne.produit_id] = _decimal(
                ligne.taux_remise
            )

    return taux_par_produit


def valoriser_stocks(stocks):
    """
    Ajoute les montants brut et net aux lignes de stock affichees.
    """

    stocks = list(
        stocks
    )

    taux_par_produit = taux_derniere_commande_directeur_par_produit(
        {
            stock.produit_id
            for stock in stocks
        }
    )

    for stock in stocks:

        montant_brut = (
            _decimal(stock.produit.prix)
            *
            _decimal(stock.quantite)
        )

        taux = _decimal(
            taux_par_produit.get(
                stock.produit_id
            )
        )

        montant_remise = (
            montant_brut
            *
            taux
            /
            Decimal("100")
        )

        stock.montant_brut = montant_brut
        stock.montant_net = montant_brut - montant_remise
        stock.taux_remise_reference = taux

    return stocks


# ==========================================================
# CREATION DU STOCK
# ==========================================================

def creer_stock(
    point_vente,
    produit,
    type_stock=TYPE_NORMAL
):
    """
    Crée un stock s'il n'existe pas.
    """

    stock, created = Stock.objects.get_or_create(

        point_vente=point_vente,

        produit=produit,

        type_stock=type_stock,

        defaults={

            "quantite": Decimal("0"),

            "seuil_alerte": Decimal("0")

        }

    )

    return stock


# ==========================================================
# CONSULTATION DU STOCK
# ==========================================================

def stock_disponible(
    point_vente,
    produit,
    type_stock=TYPE_NORMAL
):
    """
    Retourne le stock.
    """

    return creer_stock(

        point_vente,

        produit,

        type_stock

    )


# ==========================================================
# AJOUT AU STOCK
# ==========================================================

@transaction.atomic
def ajouter_stock(
    point_vente,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Ajoute une quantité au stock.
    """

    stock = creer_stock(

        point_vente,

        produit,

        type_stock

    )

    stock.quantite += Decimal(str(quantite))

    stock.save(
        update_fields=[
            "quantite",
            "date_modification"
        ]
    )

    return stock


# ==========================================================
# RETRAIT DU STOCK
# ==========================================================

@transaction.atomic
def retirer_stock(
    point_vente,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Retire une quantité du stock.
    """

    stock = creer_stock(

        point_vente,

        produit,

        type_stock

    )

    quantite = Decimal(str(quantite))

    if stock.quantite < quantite:

        raise Exception(

            f"Stock insuffisant pour {produit.designation}."

        )

    stock.quantite -= quantite

    stock.save(
        update_fields=[
            "quantite",
            "date_modification"
        ]
    )

    return stock


# ==========================================================
# MODIFICATION DIRECTE
# ==========================================================

@transaction.atomic
def modifier_quantite(
    point_vente,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Modifie directement le stock.
    (Inventaire, régularisation...)
    """

    stock = creer_stock(

        point_vente,

        produit,

        type_stock

    )

    stock.quantite = Decimal(str(quantite))

    stock.save(
        update_fields=[
            "quantite",
            "date_modification"
        ]
    )

    return stock

# ==========================================================
# TRANSFERT DE STOCK
# ==========================================================

@transaction.atomic
def transferer_stock(
    point_vente_source,
    point_vente_destination,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Transfère une quantité de stock
    d'un point de vente vers un autre.
    """

    retirer_stock(

        point_vente=point_vente_source,

        produit=produit,

        quantite=quantite,

        type_stock=type_stock

    )

    ajouter_stock(

        point_vente=point_vente_destination,

        produit=produit,

        quantite=quantite,

        type_stock=type_stock

    )
