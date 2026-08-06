"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Services métier du module Commandes.

==========================================================
"""


from decimal import Decimal

from django.db import transaction

from .models import (
    Commande,
    LigneCommande
)

from stocks.services import (
    ajouter_stock,
    retirer_stock,
)

from .calculs import (
    calculer_quantite,
    calculer_remise,
    calculer_montant_net
)

from .validators import (
    verifier_presence_ligne,
    verifier_montant,
    verifier_prix,
    verifier_taux
)

from referentiel.models import (
    Distributeur,
)

from .numerotation import (
    generer_numero_commande
)

from objectif.models import Objectif

from objectif.services import recalculer_objectif

from django.utils import timezone

from .models import Commande

from distributions.models import LigneDistribution

from commandes.models import LigneCommande

from stocks.services import ajouter_stock

from stocks.models import TYPE_NORMAL
from stocks.models import TYPE_TAMPON
from .permissions import peut_modifier

from distributions.models import Distribution
from distributions.numerotation import generer_numero_distribution

# ==========================================================
# CONSTRUCTION DES LIGNES
# ==========================================================

def construire_lignes_depuis_formulaire(
    donnees,
    produits
):

    lignes = []

    for produit in produits:

        if f"produit_{produit.idproduit}" not in donnees:

            continue

        montant = Decimal(

            donnees.get(

                f"montant_{produit.idproduit}",

                "0"

            )

        )

        taux = Decimal(

            donnees.get(

                f"taux_{produit.idproduit}",

                "0"

            )

        )

        prix = produit.prix

        quantite = calculer_quantite(
            montant,
            prix
        )

        lignes.append({

            "produit": produit,

            "montant": montant,

            "quantite": quantite,

            "taux_remise": taux

        })

    return lignes


# ==========================================================
# TRAITEMENT APRES CREATION
# ==========================================================

def traiter_commande_apres_creation(
    commande
):
    """
    Traitements après création.
    """

    if commande.type_commande == Commande.TYPE_DIRECTEUR:

        commande.etat = Commande.VALIDEE

        commande.save(
            update_fields=["etat"]
        )

        mettre_a_jour_objectifs(
            commande
        )

        alimenter_stock_commande_directeur(
            commande
        )

    elif commande.type_commande == Commande.TYPE_GERANT:

        commande.etat = Commande.EN_ATTENTE

        commande.save(
            update_fields=["etat"]
        )

# ==========================================================
# ALIMENTER LE STOCK
# ==========================================================

def alimenter_stock_commande_directeur(
    commande
):
    """
    Alimente le stock à partir
    d'une commande Directeur.
    """

    for ligne in commande.lignes.all():

        ajouter_stock(

            point_vente=commande.point_vente,

            produit=ligne.produit,

            quantite=ligne.quantite

        )

# ==========================================================
# ALIMENTER LE STOCK TAMPON
# ==========================================================

def alimenter_stock_commande_stock_tampon(
    commande
):
    """
    Alimente le stock tampon.
    """

    from stocks.models import TYPE_TAMPON

    for ligne in commande.lignes.all():

        ajouter_stock(

            point_vente=commande.point_vente,

            produit=ligne.produit,

            quantite=ligne.quantite,

            type_stock=TYPE_TAMPON

        )

# ==========================================================
# CREATION COMMANDE
# ==========================================================

@transaction.atomic
def creer_commande(

    utilisateur,

    type_commande,

    categorie_commande,

    date_commande,

    lignes

):

    verifier_presence_ligne(

        lignes

    )

    commande = Commande.objects.create(

        numero=generer_numero_commande(),

        type_commande=type_commande,

        categorie_commande=categorie_commande,

        date_commande=date_commande,

        point_vente=utilisateur.profil.point_vente,

        utilisateur=utilisateur

    )

    creer_lignes_commande(

        commande,

        lignes

    )

    recalculer_totaux_commande(

        commande

    )

    traiter_commande_apres_creation(

        commande

    )

    return commande


# ==========================================================
# CREATION DES LIGNES
# ==========================================================

def creer_lignes_commande(

    commande,

    lignes

):

    for ligne in lignes:

        produit = ligne["produit"]

        montant = Decimal(

            ligne["montant"]

        )

        taux = Decimal(

            ligne["taux_remise"]

        )

        prix = produit.prix

        verifier_prix(

            prix

        )

        verifier_montant(

            montant

        )

        verifier_taux(

            taux

        )

        quantite = calculer_quantite(

            montant,

            prix

        )

        remise = calculer_remise(

            montant,

            taux

        )

        montant_net = calculer_montant_net(

            montant,

            remise

        )

        LigneCommande.objects.create(

            commande=commande,

            produit=produit,

            prix_unitaire=prix,

            montant=montant,

            quantite=quantite,

            taux_remise=taux,

            montant_remise=remise,

            montant_net=montant_net

        )


# ==========================================================
# CREATION DES LIGNES reglement
# ==========================================================

def creer_lignes_reglement_stock(
    commande,
    lignes
):

    for ligne in lignes:

        produit = ligne["produit"]

        montant = Decimal(

            ligne["montant"]

        )

        taux = Decimal(

            ligne["taux_remise"]

        )

        prix = produit.prix

        verifier_prix(

            prix

        )

        verifier_montant(

            montant

        )

        verifier_taux(

            taux

        )

        quantite = ligne["quantite"]

        remise = calculer_remise(

            montant,

            taux

        )

        montant_net = calculer_montant_net(

            montant,

            remise

        )

        LigneCommande.objects.create(

            commande=commande,

            produit=produit,

            prix_unitaire=prix,

            montant=montant,

            quantite=quantite,

            taux_remise=taux,

            montant_remise=remise,

            montant_net=montant_net

        )


# ==========================================================
# RECALCUL DES TOTAUX
# ==========================================================

def recalculer_totaux_commande(
    commande
):
    """
    Recalcule les montants brut et net
    de la commande.
    """

    total_brut = Decimal("0")
    total_net = Decimal("0")

    for ligne in commande.lignes.all():

        total_brut += ligne.montant
        total_net += ligne.montant_net

    commande.montant_brut = total_brut
    commande.montant_net = total_net

    commande.save(
        update_fields=[
            "montant_brut",
            "montant_net"
        ]
    )

# ==========================================================
# MODIFICATION
# ==========================================================

@transaction.atomic
def modifier_commande(
    commande,
    date_commande,
    lignes
):
    if not peut_modifier(
        commande.utilisateur,
        commande
    ):
        raise Exception(
            "Cette commande ne peut plus être modifiée."
        )
    verifier_presence_ligne(lignes)

    if commande.type_commande == Commande.TYPE_DIRECTEUR:

        mettre_a_jour_objectifs(
            commande,
            suppression=True
        )

        annuler_stock_commande_directeur(
            commande
        )

    commande.date_commande = date_commande

    commande.save(
        update_fields=["date_commande"]
    )

    commande.lignes.all().delete()

    creer_lignes_commande(
        commande,
        lignes
    )

    recalculer_totaux_commande(
        commande
    )

    if commande.type_commande == Commande.TYPE_DIRECTEUR:

        mettre_a_jour_objectifs(
            commande
        )

        alimenter_stock_commande_directeur(
            commande
        )

    return commande        



# ==========================================================
# MODIFICATION STOCK TAMPON
# ==========================================================

@transaction.atomic
def modifier_commande_stock_tampon(
    commande,
    date_commande,
    lignes
):
    if not peut_modifier(
        commande.utilisateur,
        commande
    ):
        raise Exception(
            "Cette commande ne peut plus être modifiée."
        )
    verifier_presence_ligne(lignes)

    mettre_a_jour_objectifs(

        commande,

        suppression=True

    )

    annuler_stock_commande_stock_tampon(

        commande

    )

    commande.date_commande = date_commande

    commande.save(
        update_fields=["date_commande"]
    )

    commande.lignes.all().delete()

    creer_lignes_commande(
        commande,
        lignes
    )

    recalculer_totaux_commande(
        commande
    )

    mettre_a_jour_objectifs(

        commande

    )

    alimenter_stock_commande_stock_tampon(

        commande

    )

    return commande   


# ==========================================================
# MODIFICATION COMMANDE CAUTION
# ==========================================================

@transaction.atomic
def modifier_commande_caution(

    commande,

    date_commande,

    lignes

):

    verifier_presence_ligne(

        lignes

    )

    mettre_a_jour_objectifs(

        commande,

        suppression=True

    )

    annuler_stock_commande_directeur(

        commande

    )

    commande.date_commande = date_commande

    commande.save(

        update_fields=[

            "date_commande"

        ]

    )

    commande.lignes.all().delete()

    creer_lignes_commande(

        commande,

        lignes

    )

    recalculer_totaux_commande(

        commande

    )

    traiter_commande_apres_creation(

        commande

    )

    return commande



# ==========================================================
# MISE A JOUR DES OBJECTIFS
# ==========================================================

def mettre_a_jour_objectifs(
    commande,
    suppression=False
):
    """
    Recalcule tous les objectifs impactés
    par la commande.
    """

    objectifs = Objectif.objects.filter(

        actif=True,

        point_vente=commande.point_vente,

        mois=commande.date_commande.month,

        annee=commande.date_commande.year

    )

    compagnies = commande.lignes.values_list(

        "produit__compagnie_id",

        flat=True

    ).distinct()

    objectifs = objectifs.filter(

        compagnie_id__in=compagnies

    )

    for objectif in objectifs:

        recalculer_objectif(

            objectif

        )


# ==========================================================
# VALIDATION D'UNE COMMANDE
# ==========================================================

@transaction.atomic
def valider_commande(
    commande,
    directeur
):
    """
    Valide une commande.

    La création automatique de la distribution
    sera ajoutée dans l'étape suivante.
    """

    if commande.etat == Commande.VALIDEE:

        raise ValueError(
            "Cette commande est déjà validée."
        )

    commande.etat = Commande.VALIDEE

    commande.date_modification = timezone.now()

    commande.save(
        update_fields=[
            "etat",
            "date_modification"
        ]
    )

    return commande


# ==========================================================
# REFUS D'UNE COMMANDE
# ==========================================================

@transaction.atomic
def refuser_commande(
    commande,
    directeur
):
    """
    Refuse une commande.
    """

    if commande.etat == Commande.REFUSEE:

        raise ValueError(
            "Cette commande est déjà refusée."
        )

    commande.etat = Commande.REFUSEE

    commande.date_modification = timezone.now()

    commande.save(
        update_fields=[
            "etat",
            "date_modification"
        ]
    )

    return commande

# ==========================================================
# ANNULATION STOCK
# ==========================================================

def annuler_stock_commande_directeur(
    commande
):
    """
    Retire du stock les quantités
    d'une commande.
    """
    
    from stocks.services import retirer_stock

    for ligne in commande.lignes.all():

        try:

            retirer_stock(

                point_vente=commande.point_vente,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

        except Exception:

            raise Exception(

                f"Impossible de modifier cette commande.\n\n"
                f"Le stock du produit "
                f"'{ligne.produit.designation}' "
                f"a déjà été utilisé en partie ou en totalité.\n\n"
                f"Cette commande ne peut donc plus être modifiée."

            )

# ==========================================================
# ANNULATION STOCK TAMPON
# ==========================================================

def annuler_stock_commande_stock_tampon(
    commande
):
    """
    Retire du stock tampon les quantités
    d'une commande.
    """

    from stocks.services import retirer_stock

    for ligne in commande.lignes.all():

        try:

            retirer_stock(

                point_vente=commande.point_vente,

                produit=ligne.produit,

                quantite=ligne.quantite,

                type_stock=TYPE_TAMPON

            )

        except Exception:

            raise Exception(

                f"Impossible de modifier cette commande.\n\n"

                f"Le stock tampon du produit "

                f"'{ligne.produit.designation}' "

                f"a déjà été utilisé en partie ou en totalité.\n\n"

                f"Cette commande ne peut donc plus être modifiée."

            )


# ==========================================================
# CREATION COMMANDE STOCK TAMPON
# ==========================================================

@transaction.atomic
def creer_commande_stock_tampon(

    utilisateur,

    date_commande,

    lignes

):

    verifier_presence_ligne(

        lignes

    )

    commande = Commande.objects.create(

        numero=generer_numero_commande(),

        type_commande=Commande.TYPE_DIRECTEUR,

        categorie_commande=Commande.CATEGORIE_STOCK_TAMPON,

        date_commande=date_commande,

        point_vente=utilisateur.profil.point_vente,

        utilisateur=utilisateur,

        etat=Commande.VALIDEE

    )

    creer_lignes_commande(

        commande,

        lignes

    )

    recalculer_totaux_commande(

        commande

    )

    alimenter_stock_commande_stock_tampon(

        commande

    )

    return commande


# ==========================================================
# CREATION COMMANDE CAUTION
# ==========================================================

@transaction.atomic
def creer_commande_caution(

    utilisateur,

    date_commande,

    lignes

):

    verifier_presence_ligne(

        lignes

    )

    commande = Commande.objects.create(

        numero=generer_numero_commande(),

        type_commande=Commande.TYPE_DIRECTEUR,

        categorie_commande=Commande.CATEGORIE_CAUTION,

        date_commande=date_commande,

        point_vente=utilisateur.profil.point_vente,

        utilisateur=utilisateur,

        etat=Commande.VALIDEE

    )

    creer_lignes_commande(

        commande,

        lignes

    )

    recalculer_totaux_commande(

        commande

    )

    traiter_commande_apres_creation(
        commande
    )

    return commande


# ==========================================================
# VERIFIER LE STOCK TAMPON
# ==========================================================

def verifier_stock_tampon(
    point_vente,
    lignes
):
    """
    Vérifie que le stock tampon est suffisant
    pour tous les produits.
    """

    from stocks.models import (
        Stock,
        TYPE_TAMPON
    )

    for ligne in lignes:

        try:

            stock = Stock.objects.get(

                point_vente=point_vente,

                produit=ligne["produit"],

                type_stock=TYPE_TAMPON

            )

        except Stock.DoesNotExist:

            raise ValueError(

                f"Stock tampon insuffisant pour "
                f"{ligne['produit'].designation}. "
                f"Disponible : {stock.quantite} - "
                f"Demandé : {ligne['quantite']}."

            )

        if stock.quantite < ligne["quantite"]:

            raise ValueError(

                f"Stock tampon insuffisant pour "
                f"{ligne['produit'].designation}."

            )
        



# ==========================================================
# CREATION REGLEMENT STOCK TAMPON
# ==========================================================

@transaction.atomic
def creer_reglement_stock_tampon(

    utilisateur,

    date_commande,

    lignes

):
    """
    Crée un règlement du stock tampon.
    """

    verifier_presence_ligne(

        lignes

    )

    verifier_stock_tampon(

        utilisateur.profil.point_vente,

        lignes

    )

    commande = Commande.objects.create(

        numero=generer_numero_commande(),

        type_commande=Commande.TYPE_DIRECTEUR,

        categorie_commande=Commande.CATEGORIE_REGLEMENT_STOCK,

        date_commande=date_commande,

        point_vente=utilisateur.profil.point_vente,

        utilisateur=utilisateur,

        etat=Commande.VALIDEE

    )

    creer_lignes_reglement_stock(
        commande,
        lignes
    )

    recalculer_totaux_commande(

        commande

    )

    traiter_reglement_stock(

        commande

    )

    return commande


# ==========================================================
# MODIFICATION REGLEMENT STOCK TAMPON
# ==========================================================

@transaction.atomic
def modifier_reglement_stock_tampon(

    commande,

    date_commande,

    lignes

):

    if not peut_modifier(

        commande.utilisateur,

        commande

    ):

        raise Exception(

            "Cette commande ne peut plus être modifiée."

        )

    verifier_presence_ligne(

        lignes

    )

    mettre_a_jour_objectifs(

        commande,

        suppression=True

    )

    annuler_reglement_stock_tampon(

        commande

    )

    verifier_stock_tampon(

        commande.point_vente,

        lignes

    )

    commande.date_commande = date_commande

    commande.save(

        update_fields=[

            "date_commande"

        ]

    )

    commande.lignes.all().delete()

    creer_lignes_reglement_stock(

        commande,

        lignes

    )

    recalculer_totaux_commande(

        commande

    )

    traiter_reglement_stock(

        commande

    )

    return commande


# ==========================================================
# ANNULATION REGLEMENT STOCK TAMPON
# ==========================================================

def annuler_reglement_stock_tampon(
    commande
):
    """
    Annule un règlement de stock tampon.

    Les produits reviennent dans le stock tampon
    et sont retirés du stock normal.
    """

    from stocks.services import (
        ajouter_stock,
        retirer_stock
    )

    for ligne in commande.lignes.all():

        try:

            retirer_stock(

                point_vente=commande.point_vente,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

        except Exception:

            raise Exception(

                f"Impossible de modifier ce règlement.\n\n"
                f"Le stock normal du produit "
                f"'{ligne.produit.designation}' "
                f"a déjà été utilisé en partie ou en totalité.\n\n"
                f"Ce règlement ne peut donc plus être modifié."

            )

        ajouter_stock(

            point_vente=commande.point_vente,

            produit=ligne.produit,

            quantite=ligne.quantite,

            type_stock=TYPE_TAMPON

        )


# ==========================================================
# SORTIE DU STOCK TAMPON
# ==========================================================

def sortir_stock_tampon(
    commande
):
    """
    Déduit les quantités
    du stock tampon.
    """

    from stocks.models import (
        Stock,
        TYPE_TAMPON
    )

    for ligne in commande.lignes.all():

        stock = Stock.objects.get(

            point_vente=commande.point_vente,

            produit=ligne.produit,

            type_stock=TYPE_TAMPON

        )

        stock.quantite -= ligne.quantite

        stock.save(

            update_fields=[
                "quantite",
                "date_modification"
            ]

        )


# ==========================================================
# ALIMENTER LE STOCK NORMAL
# ==========================================================

def alimenter_stock_reglement(
    commande
):
    """
    Ajoute les quantités
    au stock normal.
    """

    for ligne in commande.lignes.all():

        ajouter_stock(

            point_vente=commande.point_vente,

            produit=ligne.produit,

            quantite=ligne.quantite

        )


# ==========================================================
# TRAITEMENT REGLEMENT STOCK
# ==========================================================

def traiter_reglement_stock(
    commande
):
    """
    Traite un règlement
    du stock tampon.
    """

    sortir_stock_tampon(

        commande

    )

    alimenter_stock_reglement(

        commande

    )

    mettre_a_jour_objectifs(

        commande

    )

# ==========================================================
# VALIDATION COMMANDE GERANT
# ==========================================================

@transaction.atomic
def valider_commande_gerant(commande):
    """
    Valide une commande gérant.

    La création de la distribution est réalisée
    par le module Distributions.
    """

    if commande.etat != Commande.EN_ATTENTE:

        raise Exception(
            "Cette commande n'est plus en attente."
        )

    commande.etat = Commande.VALIDEE

    commande.save(
        update_fields=[
            "etat",
            "date_modification"
        ]
    )

    return commande


# ==========================================================
# REJET COMMANDE GERANT
# ==========================================================

@transaction.atomic
def rejeter_commande_gerant(commande):

    # Vérifie l'état
    if commande.etat != Commande.EN_ATTENTE:

        raise Exception(
            "Cette commande n'est plus en attente."
        )

    commande.etat = Commande.REJETEE

    commande.save(update_fields=["etat"])

    return commande

from django.db import transaction
from django.shortcuts import get_object_or_404

from commandes.models import Commande


def valider_commande_directeur_service(
    commande_id,
    utilisateur,
    gerant_id,
):

    commande = get_object_or_404(
        Commande,
        pk=commande_id
    )

    gerant = get_object_or_404(
        Distributeur,
        pk=gerant_id,
        categorie=Distributeur.CATEGORIE_GERANT,
        actif=True,
    )

    if commande.etat != Commande.EN_ATTENTE:

        raise Exception(
            "Cette commande a déjà été traitée."
        )

    # ==========================================================
    # CREATION DE LA DISTRIBUTION
    # ==========================================================

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=Distribution.TYPE_COMMANDE_GERANT,

        commande=commande,

        point_vente_source=utilisateur.profil.point_vente,

        point_vente_destination=commande.point_vente,

        utilisateur=utilisateur,

        distributeur=gerant,

        date_distribution=timezone.now().date(),

        montant_brut=commande.montant_brut,

        montant_net=commande.montant_net,
    )

    # ==========================================================
    # CREATION DES LIGNES DE DISTRIBUTION
    # ==========================================================

    lignes_commande = LigneCommande.objects.filter(
        commande=commande
    ).select_related("produit")

    for ligne in lignes_commande:

        LigneDistribution.objects.create(

            distribution=distribution,

            produit=ligne.produit,

            prix_unitaire=ligne.prix_unitaire,

            montant=ligne.montant,

            quantite=ligne.quantite,

            taux_remise=ligne.taux_remise,

            montant_remise=ligne.montant_remise,

            montant_net=ligne.montant_net,
        )

    # ==========================================================
    # TRANSFERT DU STOCK
    # ==========================================================

    for ligne in distribution.lignes.all():

        # Retrait du stock du dépôt central
        retirer_stock(

            point_vente=distribution.point_vente_source,

            produit=ligne.produit,

            quantite=ligne.quantite,

        )

        # Ajout du stock du point de vente du gérant
        ajouter_stock(

            point_vente=distribution.point_vente_destination,

            produit=ligne.produit,

            quantite=ligne.quantite,

        )


    # ==========================================================
    # VALIDATION DE LA COMMANDE
    # ==========================================================

    commande.etat = Commande.VALIDEE

    commande.utilisateur_validation = utilisateur

    commande.date_validation = timezone.now()

    commande.save(
        update_fields=[
            "etat",
            "utilisateur_validation",
            "date_validation",
        ]
    )