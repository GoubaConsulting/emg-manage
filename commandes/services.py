"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Services métier du module Commandes.

==========================================================
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
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

from stocks.models import (
    Stock,
    TYPE_NORMAL,
    TYPE_TAMPON,
)

from .permissions import (
    peut_modifier,
    peut_corriger_par_directeur
)

from distributions.models import Distribution
from distributions.numerotation import generer_numero_distribution
from comptes.corrections_apercu import commande_corrigeable

# ==========================================================
# CONSTRUCTION DES LIGNES
# ==========================================================

def convertir_decimal_formulaire(valeur, libelle):
    """Convertit une valeur numerique POST, y compris au format francais."""

    if valeur is None or valeur == "":
        return Decimal("0")

    valeur_normalisee = (
        str(valeur)
        .strip()
        .replace("\u00a0", "")
        .replace("\u202f", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return Decimal(valeur_normalisee)
    except (InvalidOperation, TypeError, ValueError) as erreur:
        raise ValidationError(
            f"La valeur du champ {libelle} n'est pas un nombre valide."
        ) from erreur

def construire_lignes_depuis_formulaire(
    donnees,
    produits,
    taux_initiaux=None
):

    lignes = []

    for produit in produits:

        montant = convertir_decimal_formulaire(
            donnees.get(
                f"montant_{produit.idproduit}",
                "0"
            ),
            f"montant du produit « {produit.designation} »"
        )

        montant_initial = convertir_decimal_formulaire(
            donnees.get(
                f"montant_initial_{produit.idproduit}",
                "0"
            ),
            f"montant initial du produit « {produit.designation} »"
        )

        if (
            f"produit_{produit.idproduit}" not in donnees
            and
            montant_initial <= 0
        ):

            continue

        taux = convertir_decimal_formulaire(
            donnees.get(
                f"taux_{produit.idproduit}",
                "0"
            ),
            f"taux du produit « {produit.designation} »"
        )

        taux_initial = convertir_decimal_formulaire(
            (
                taux_initiaux
                or
                {}
            ).get(
                produit.idproduit,
                donnees.get(
                    f"taux_initial_{produit.idproduit}",
                    taux
                )
            ),
            f"taux initial du produit « {produit.designation} »"
        )

        taux_ligne = taux

        if (
            montant <= 0
            and
            montant_initial > 0
        ):

            taux_ligne = taux_initial

        prix = produit.prix

        quantite = calculer_quantite(
            montant,
            prix
        )

        lignes.append({

            "produit": produit,

            "montant": montant,

            "quantite": quantite,

            "taux_remise": taux_ligne,

            "taux_initial": taux_initial,

            "montant_initial": montant_initial,

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

        montant_initial = Decimal(

            ligne.get(
                "montant_initial",
                Decimal("0.00")
            )

        )

        taux = Decimal(

            ligne["taux_remise"]

        )

        taux_initial = Decimal(

            ligne.get(
                "taux_initial",
                taux
            )

        )

        prix = produit.prix

        verifier_prix(

            prix

        )

        if montant < 0 or montant_initial < 0:

            raise ValueError(
                "Les montants ne peuvent pas etre negatifs."
            )

        if montant <= 0 and montant_initial <= 0:

            verifier_montant(

                montant

            )

        if montant > 0:

            verifier_montant(

                montant

            )

        verifier_taux(

            taux

        )

        verifier_taux(

            taux_initial

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

        remise_initiale = calculer_remise(

            montant_initial,

            taux_initial

        )

        montant_net_initial = calculer_montant_net(

            montant_initial,

            remise_initiale

        )

        montant_total_brut = (
            montant_initial
            +
            montant
        )

        montant_total_net = (
            montant_net_initial
            +
            montant_net
        )

        LigneCommande.objects.create(

            commande=commande,

            produit=produit,

            prix_unitaire=prix,

            montant=montant,

            quantite=quantite,

            taux_remise=taux,

            montant_remise=remise,

            montant_net=montant_net,

            montant_initial=montant_initial,

            montant_net_initial=montant_net_initial,

            montant_total_brut=montant_total_brut,

            montant_total_net=montant_total_net

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
    Recalcule les montants de la commande.
    """

    total_brut = Decimal("0")
    total_net = Decimal("0")
    total_initial = Decimal("0")
    total_net_initial = Decimal("0")
    total_total_brut = Decimal("0")
    total_total_net = Decimal("0")

    for ligne in commande.lignes.all():

        total_brut += ligne.montant
        total_net += ligne.montant_net
        total_initial += ligne.montant_initial
        total_net_initial += ligne.montant_net_initial
        total_total_brut += ligne.montant_total_brut
        total_total_net += ligne.montant_total_net

    commande.montant_brut = total_brut
    commande.montant_net = total_net
    commande.montant_initial = total_initial
    commande.montant_net_initial = total_net_initial
    commande.montant_total_brut = total_total_brut
    commande.montant_total_net = total_total_net

    commande.save(
        update_fields=[
            "montant_brut",
            "montant_net",
            "montant_initial",
            "montant_net_initial",
            "montant_total_brut",
            "montant_total_net",
        ]
    )


def synchroniser_distribution_commande_gerant(
    commande
):
    """
    Aligne la distribution ouverte liee a une commande gerant
    apres correction de la commande.
    """

    distributions = list(
        commande.distributions.filter(
            type_distribution=Distribution.TYPE_COMMANDE_GERANT
        )
        .prefetch_related(
            "lignes__produit"
        )
    )

    if not distributions:

        return

    distributions_cloturees = [
        distribution
        for distribution in distributions
        if distribution.etat == Distribution.ETAT_CLOTUREE
    ]

    if distributions_cloturees:

        raise Exception(
            "Cette commande ne peut plus etre modifiee "
            "car une distribution liee est deja cloturee."
        )

    if len(distributions) > 1:

        raise Exception(
            "Cette commande possede plusieurs distributions liees. "
            "La correction automatique est impossible."
        )

    distribution = distributions[0]

    anciennes_lignes = list(
        distribution.lignes.select_related(
            "produit"
        )
    )

    for ligne in anciennes_lignes:

        try:

            retirer_stock(
                point_vente=distribution.point_vente_destination,
                produit=ligne.produit,
                quantite=ligne.quantite,
            )

            ajouter_stock(
                point_vente=distribution.point_vente_source,
                produit=ligne.produit,
                quantite=ligne.quantite,
            )

        except Exception as exc:

            raise Exception(
                "Impossible de modifier cette commande : "
                "le stock du gerant ne permet pas d'annuler "
                f"la distribution du produit {ligne.produit.designation}."
            ) from exc

    distribution.lignes.all().delete()

    lignes_commande = list(
        commande.lignes.select_related(
            "produit"
        )
    )

    for ligne in lignes_commande:

        if ligne.quantite <= 0:

            ligne.quantite_distribuee = Decimal("0.00")

            ligne.save(
                update_fields=[
                    "quantite_distribuee",
                ]
            )

            continue

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

        ligne.quantite_distribuee = ligne.quantite

        ligne.save(
            update_fields=[
                "quantite_distribuee",
            ]
        )

    distribution.montant_brut = commande.montant_brut
    distribution.montant_net = commande.montant_net

    distribution.save(
        update_fields=[
            "montant_brut",
            "montant_net",
            "date_modification",
        ]
    )

    for ligne in distribution.lignes.select_related(
        "produit"
    ):

        try:

            retirer_stock(
                point_vente=distribution.point_vente_source,
                produit=ligne.produit,
                quantite=ligne.quantite,
            )

            ajouter_stock(
                point_vente=distribution.point_vente_destination,
                produit=ligne.produit,
                quantite=ligne.quantite,
            )

        except Exception as exc:

            raise Exception(
                "Impossible de modifier cette commande : "
                "le stock du Directeur ne suffit pas pour "
                f"la nouvelle quantite du produit {ligne.produit.designation}."
            ) from exc


# ==========================================================
# MODIFICATION
# ==========================================================

@transaction.atomic
def modifier_commande(
    commande,
    date_commande,
    lignes,
    utilisateur_action=None
):
    utilisateur_permission = (
        utilisateur_action
        or
        commande.utilisateur
    )

    if not peut_modifier(
        utilisateur_permission,
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

    if commande.type_commande == Commande.TYPE_GERANT:

        synchroniser_distribution_commande_gerant(
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

    commande.etat = Commande.REFUSEE

    commande.save(update_fields=["etat"])

    return commande

from django.db import transaction
from django.shortcuts import get_object_or_404

from commandes.models import Commande


def verifier_stock_commande_gerant(
    commande,
    point_vente_source,
):
    """
    Verifie le stock normal du Directeur avant validation.
    """

    lignes = list(
        LigneCommande.objects
        .filter(
            commande=commande
        )
        .select_related(
            "produit__compagnie"
        )
        .order_by(
            "produit__compagnie__designation",
            "produit__designation",
            "idlignecommande",
        )
    )

    for ligne in lignes:

        if ligne.quantite <= 0:

            continue

        stock = (
            Stock.objects
            .select_for_update()
            .filter(
                point_vente=point_vente_source,
                produit=ligne.produit,
                type_stock=TYPE_NORMAL,
            )
            .first()
        )

        stock_disponible = (
            stock.quantite
            if stock is not None
            else Decimal("0.00")
        )

        if stock_disponible < ligne.quantite:

            compagnie = ligne.produit.compagnie.designation

            raise Exception(
                "Stock insuffisant pour le produit "
                f"« {ligne.produit.designation} » "
                f"de la compagnie « {compagnie} ». "
                f"Stock disponible : {stock_disponible}. "
                f"Quantité demandée : {ligne.quantite}."
            )

    return lignes


@transaction.atomic
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

    point_vente_source = utilisateur.profil.point_vente

    lignes_commande = verifier_stock_commande_gerant(
        commande,
        point_vente_source,
    )

    # ==========================================================
    # CREATION DE LA DISTRIBUTION
    # ==========================================================

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=Distribution.TYPE_COMMANDE_GERANT,

        commande=commande,

        point_vente_source=point_vente_source,

        point_vente_destination=commande.point_vente,

        utilisateur=utilisateur,

        distributeur=gerant,

        date_distribution=commande.date_commande,

        montant_brut=commande.montant_brut,

        montant_net=commande.montant_net,
    )

    # ==========================================================
    # CREATION DES LIGNES DE DISTRIBUTION
    # ==========================================================

    for ligne in lignes_commande:

        if ligne.quantite <= 0:

            continue

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

    return distribution


# ==========================================================
# CORRECTION COMMANDE GERANT PAR DIRECTEUR
# ==========================================================

@transaction.atomic
def corriger_commande_par_directeur(
    commande,
    directeur,
    date_commande,
    lignes,
):
    commande = Commande.objects.select_for_update().get(pk=commande.pk)
    if not commande_corrigeable(directeur, commande):
        raise ValueError("Cette commande ne peut plus être corrigée.")

    anciennes = {
        ligne.produit_id: ligne
        for ligne in commande.lignes.select_related("produit")
    }
    if any(ligne.montant_initial > 0 for ligne in anciennes.values()):
        if date_commande != commande.date_commande:
            raise ValueError(
                "La date d'une commande avec montant initial ne peut pas changer."
            )

    for ligne in lignes:
        produit = ligne["produit"]
        ancienne = anciennes.get(produit.pk)
        initial_attendu = ancienne.montant_initial if ancienne else Decimal("0")
        if Decimal(str(ligne.get("montant_initial", 0))) != initial_attendu:
            raise ValueError("Les montants initiaux ne peuvent pas être corrigés ici.")
        if ancienne and ancienne.prix_unitaire != produit.prix:
            raise ValueError(
                f"Le prix du produit {produit.designation} a changé. "
                "Cette commande doit être examinée manuellement."
            )

    produits_presents = {ligne["produit"].pk for ligne in lignes}
    if any(
        ligne.montant_initial > 0 and produit_id not in produits_presents
        for produit_id, ligne in anciennes.items()
    ):
        raise ValueError("Un produit avec montant initial ne peut pas être retiré.")

    verifier_presence_ligne(lignes)
    commande.date_commande = date_commande
    commande.save(update_fields=["date_commande", "date_modification"])
    commande.lignes.all().delete()
    creer_lignes_commande(commande, lignes)
    recalculer_totaux_commande(commande)
    return commande
