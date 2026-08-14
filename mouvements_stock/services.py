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
