"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Services metier du module.

==========================================================
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction

from referentiel.models import Produit

from stocks.services import (
    ajouter_stock,
    creer_stock,
    retirer_stock,
)

from .models import (
    LigneMouvementStock,
    MouvementStock,
)

from .numerotation import generer_numero_mouvement_stock
from .permissions import peut_modifier


def construire_lignes_depuis_formulaire(donnees):
    """
    Construit les lignes depuis les champs quantite_<idproduit>.
    """

    lignes = []

    for cle in donnees:

        if not cle.startswith("quantite_"):

            continue

        produit_id = cle.split("_")[1]

        try:

            produit_id = int(produit_id)

            quantite = Decimal(
                str(donnees.get(cle) or "0")
            )

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ):

            raise ValueError(
                "Une quantite saisie est invalide."
            )

        if quantite <= 0:

            continue

        produit = Produit.objects.get(
            pk=produit_id,
            actif=True,
        )

        lignes.append({
            "produit": produit,
            "quantite": quantite,
        })

    return lignes


@transaction.atomic
def creer_mouvement_stock(
    utilisateur,
    type_mouvement,
    type_stock,
    date_mouvement,
    motif,
    observation,
    lignes,
):
    """
    Cree un mouvement et applique l'entree/sortie au stock.
    """

    if not lignes:

        raise ValueError(
            "Veuillez saisir au moins un produit."
        )

    point_vente = utilisateur.profil.point_vente

    if point_vente is None:

        raise ValueError(
            "Aucun point de vente n'est rattache a cet utilisateur."
        )

    mouvement = MouvementStock.objects.create(
        numero=generer_numero_mouvement_stock(),
        type_mouvement=type_mouvement,
        type_stock=type_stock,
        date_mouvement=date_mouvement,
        point_vente=point_vente,
        motif=motif,
        observation=observation or "",
        utilisateur=utilisateur,
    )

    lignes_mouvement = []

    total_quantite = Decimal("0.00")

    for ligne in lignes:

        produit = ligne["produit"]

        quantite = Decimal(
            str(ligne["quantite"])
        )

        if quantite <= 0:

            raise ValueError(
                "La quantite doit etre superieure a zero."
            )

        stock = creer_stock(
            point_vente=point_vente,
            produit=produit,
            type_stock=type_stock,
        )

        stock_avant = stock.quantite

        if type_mouvement == MouvementStock.TYPE_ENTREE:

            stock = ajouter_stock(
                point_vente=point_vente,
                produit=produit,
                quantite=quantite,
                type_stock=type_stock,
            )

        elif type_mouvement == MouvementStock.TYPE_SORTIE:

            stock = retirer_stock(
                point_vente=point_vente,
                produit=produit,
                quantite=quantite,
                type_stock=type_stock,
            )

        else:

            raise ValueError(
                "Le type de mouvement est invalide."
            )

        lignes_mouvement.append(
            LigneMouvementStock(
                mouvement=mouvement,
                produit=produit,
                quantite=quantite,
                stock_avant=stock_avant,
                stock_apres=stock.quantite,
            )
        )

        total_quantite += quantite

    LigneMouvementStock.objects.bulk_create(
        lignes_mouvement
    )

    mouvement.total_quantite = total_quantite

    mouvement.save(
        update_fields=[
            "total_quantite",
            "date_modification",
        ]
    )

    return mouvement


def _appliquer_lignes_mouvement(
    mouvement,
    lignes,
):
    """
    Applique les lignes d'un mouvement au stock
    et retourne la quantite totale.
    """

    lignes_mouvement = []

    total_quantite = Decimal("0.00")

    for ligne in lignes:

        produit = ligne["produit"]

        quantite = Decimal(
            str(ligne["quantite"])
        )

        if quantite <= 0:

            raise ValueError(
                "La quantite doit etre superieure a zero."
            )

        stock = creer_stock(
            point_vente=mouvement.point_vente,
            produit=produit,
            type_stock=mouvement.type_stock,
        )

        stock_avant = stock.quantite

        if mouvement.type_mouvement == MouvementStock.TYPE_ENTREE:

            stock = ajouter_stock(
                point_vente=mouvement.point_vente,
                produit=produit,
                quantite=quantite,
                type_stock=mouvement.type_stock,
            )

        elif mouvement.type_mouvement == MouvementStock.TYPE_SORTIE:

            stock = retirer_stock(
                point_vente=mouvement.point_vente,
                produit=produit,
                quantite=quantite,
                type_stock=mouvement.type_stock,
            )

        else:

            raise ValueError(
                "Le type de mouvement est invalide."
            )

        lignes_mouvement.append(
            LigneMouvementStock(
                mouvement=mouvement,
                produit=produit,
                quantite=quantite,
                stock_avant=stock_avant,
                stock_apres=stock.quantite,
            )
        )

        total_quantite += quantite

    LigneMouvementStock.objects.bulk_create(
        lignes_mouvement
    )

    return total_quantite


def _annuler_effet_stock_mouvement(mouvement):
    """
    Retire l'effet stock deja produit par un mouvement.
    """

    for ligne in mouvement.lignes.select_related(
        "produit"
    ):

        if mouvement.type_mouvement == MouvementStock.TYPE_ENTREE:

            retirer_stock(
                point_vente=mouvement.point_vente,
                produit=ligne.produit,
                quantite=ligne.quantite,
                type_stock=mouvement.type_stock,
            )

        elif mouvement.type_mouvement == MouvementStock.TYPE_SORTIE:

            ajouter_stock(
                point_vente=mouvement.point_vente,
                produit=ligne.produit,
                quantite=ligne.quantite,
                type_stock=mouvement.type_stock,
            )

        else:

            raise ValueError(
                "Le type de mouvement est invalide."
            )


@transaction.atomic
def modifier_mouvement_stock(
    mouvement,
    type_mouvement,
    type_stock,
    date_mouvement,
    motif,
    observation,
    lignes,
    utilisateur,
):
    """
    Corrige un mouvement et rejoue son impact stock.
    """

    if not peut_modifier(
        utilisateur,
        mouvement
    ):

        raise ValueError(
            "Ce mouvement de stock n'est pas modifiable."
        )

    if not lignes:

        raise ValueError(
            "Veuillez saisir au moins un produit."
        )

    _annuler_effet_stock_mouvement(
        mouvement
    )

    mouvement.type_mouvement = type_mouvement
    mouvement.type_stock = type_stock
    mouvement.date_mouvement = date_mouvement
    mouvement.motif = motif
    mouvement.observation = observation or ""

    mouvement.lignes.all().delete()

    total_quantite = _appliquer_lignes_mouvement(
        mouvement,
        lignes
    )

    mouvement.total_quantite = total_quantite

    mouvement.save(
        update_fields=[
            "type_mouvement",
            "type_stock",
            "date_mouvement",
            "motif",
            "observation",
            "total_quantite",
            "date_modification",
        ]
    )

    return mouvement
