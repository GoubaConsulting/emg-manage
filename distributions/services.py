"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Services métier du module Distributions.

==========================================================
"""

from decimal import Decimal

from django.db import transaction

from django.db.models import Sum

from commandes.models import (
    Commande,
    LigneCommande,
)

from referentiel.models import (
    Distributeur,
    PointVente,
    Produit,
)

from stocks.models import Stock

from stocks.services import (
    ajouter_stock,
    retirer_stock,
    transferer_stock,
)

from .models import (
    Distribution,
    LigneDistribution,
)

from .calculs import (
    calculer_montant,
    calculer_montant_remise,
    calculer_montant_net,
)

from .validators import (
    verifier_presence_ligne,
    verifier_montant,
    valider_prix,
    valider_quantite,
    valider_taux_remise,
    valider_distributeur,
    valider_type_distribution,
    verifier_commande_selectionnee,
    verifier_date_distribution,
    verifier_commande_distribuable,
    verifier_produits_distribution,
    verifier_quantites_distribution,
    verifier_stock_distribution,
)

from .numerotation import (
    generer_numero_distribution,
)

from .permissions import (
    peut_modifier_distribution,
)

from objectif.models import Objectif

from objectif.services import recalculer_objectif



# ==========================================================
# CONSTRUCTION DES LIGNES
# ==========================================================

def construire_lignes_depuis_formulaire(donnees):
    """
    Construit les lignes de distribution
    à partir du formulaire Directeur.
    """

    lignes = []

    for cle in donnees:

        if not cle.startswith("produit_"):

            continue

        idproduit = int(cle.split("_")[1])

        produit = Produit.objects.get(
            pk=idproduit
        )

        montant = Decimal(
            str(
                donnees.get(
                    f"montant_{idproduit}",
                    "0"
                )
                or
                "0"
            )
        )

        montant_initial = Decimal(
            str(
                donnees.get(
                    f"montant_initial_{idproduit}",
                    "0"
                )
                or
                "0"
            )
        )

        montant_net_initial = Decimal(
            str(
                donnees.get(
                    f"montant_net_initial_{idproduit}",
                    "0"
                )
                or
                "0"
            )
        )

        # Produit non distribue et sans montant initial a suivre.
        if montant <= 0 and montant_initial <= 0:

            continue

        taux = Decimal(
            str(
                donnees.get(
                    f"taux_{idproduit}",
                    "0"
                )
                or
                "0"
            )
        )

        taux_initial = Decimal(
            str(
                donnees.get(
                    f"taux_initial_{idproduit}",
                    taux
                )
                or
                "0"
            )
        )

        prix = Decimal(str(produit.prix))

        if montant < 0 or montant_initial < 0 or montant_net_initial < 0:

            raise Exception(
                "Les montants ne peuvent pas etre negatifs."
            )

        if montant_net_initial > montant_initial:

            raise Exception(
                f"Le montant net initial du produit "
                f"{produit.designation} ne peut pas depasser "
                "le montant initial."
            )

        if montant > 0 and montant % prix != 0:

            raise Exception(

                f"Le montant du produit "

                f"{produit.designation} "

                f"doit être un multiple de "

                f"{prix} FCFA."

            )

        quantite = Decimal("0.00")

        if montant > 0:

            quantite = montant / prix

        taux_ligne = taux

        if montant <= 0 and montant_initial > 0:

            taux_ligne = taux_initial

        lignes.append({

            "produit": produit,

            "prix_unitaire": prix,

            "montant": montant,

            "quantite": quantite,

            "taux": taux_ligne,

            "taux_initial": taux_initial,

            "montant_initial": montant_initial,

            "montant_net_initial": montant_net_initial,

        })

    return lignes


def verifier_destinataire_distribution_gerant(
    type_distribution,
    distributeur
):
    """
    Verifie que le destinataire correspond au type
    de distribution realisee par le gerant.
    """

    valider_type_distribution(
        type_distribution
    )

    valider_distributeur(
        distributeur
    )

    if (
        type_distribution == Distribution.TYPE_COMMANDE_GERANT
        and
        distributeur.categorie != Distributeur.CATEGORIE_GERANT
    ):

        raise Exception(
            "Une distribution Directeur vers point de vente "
            "doit etre rattachee a un gerant."
        )

    if (
        type_distribution == Distribution.TYPE_DISTRIBUTEUR
        and
        distributeur.categorie != Distributeur.CATEGORIE_DISTRIBUTEUR
    ):

        raise Exception(
            "Une distribution terrain doit etre "
            "rattachee a un distributeur."
        )

    if (
        type_distribution == Distribution.TYPE_CLIENT_DIRECT
        and
        distributeur.categorie != Distributeur.CATEGORIE_CLIENT
    ):

        raise Exception(
            "Une vente directe doit etre rattachee "
            "a un client direct."
        )


# ==========================================================
# CREATION D'UNE DISTRIBUTION
# ==========================================================

@transaction.atomic
def creer_distribution(
    utilisateur,
    type_distribution,
    commande,
    point_vente_destination,
    distributeur,
    date_distribution,
    lignes,
):
    print("===== ENTREE creer_distribution =====")
    print("Type :", type_distribution)
    print("Commande :", commande)
    print("Distributeur :", distributeur)
    print("Nombre de lignes :", len(lignes))
    print("====================================")
    
    # ======================================================
    # VALIDATIONS
    # ======================================================
    verifier_commande_selectionnee(
        commande
    )

    verifier_date_distribution(
        date_distribution
    )

    verifier_destinataire_distribution_gerant(
        type_distribution,
        distributeur
    )

    verifier_presence_ligne(
        lignes
    )

    verifier_commande_distribuable(
        commande
    )

    verifier_produits_distribution(
        commande,
        lignes
    )

    verifier_quantites_distribution(
        commande,
        lignes
    )

    verifier_stock_distribution(
        utilisateur.profil.point_vente,
        lignes
    )

    point_vente_source = utilisateur.profil.point_vente

    for ligne in lignes:

        stock = Stock.objects.get(

            point_vente=point_vente_source,

            produit=ligne["produit"]

        )

        if ligne["quantite"] > stock.quantite:

            raise Exception(

                f"Stock insuffisant pour le produit "
                f"« {ligne['produit'].designation} ».\n\n"
                f"Stock disponible : {stock.quantite}\n"
                f"Quantité demandée : {ligne['quantite']}.\n\n"
                f"Veuillez réduire la quantité distribuée ou réapprovisionner le stock avant de poursuivre."

            )

    # ======================================================
    # DETERMINATION DES POINTS DE VENTE
    # ======================================================

    point_vente_source = utilisateur.profil.point_vente

    point_vente_destination = None

    if type_distribution == Distribution.TYPE_COMMANDE_GERANT:

        point_vente_destination = commande.point_vente

    elif type_distribution == Distribution.TYPE_DISTRIBUTEUR:

        point_vente_destination = point_vente_source

    elif type_distribution == Distribution.TYPE_CLIENT_DIRECT:

        point_vente_destination = point_vente_source

    # ======================================================
    # CREATION DE LA DISTRIBUTION
    # ======================================================

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=type_distribution,

        date_distribution=date_distribution,

        point_vente_source=point_vente_source,

        point_vente_destination=point_vente_destination,

        commande=commande,

        distributeur=distributeur,

        utilisateur=utilisateur

    )

    # ======================================================
    # LIGNES
    # ======================================================

    creer_lignes_distribution(
        distribution,
        lignes
    )

    # ======================================================
    # TOTAUX
    # ======================================================

    recalculer_totaux_distribution(
        distribution
    )

    # ======================================================
    # TRAITEMENTS METIER
    # ======================================================

    traiter_distribution_apres_creation(
        distribution
    )

    return distribution

# ==========================================================
# CREATION D'UNE DISTRIBUTION GERANT
# ==========================================================

@transaction.atomic
def creer_distribution_gerant(
    utilisateur,
    type_distribution,
    distributeur,
    date_distribution,
    lignes,
):
    """
    Création d'une distribution réalisée
    par un gérant vers un distributeur
    ou un client direct.
    """

    # ======================================================
    # VALIDATIONS
    # ======================================================

    verifier_date_distribution(
        date_distribution
    )

    verifier_destinataire_distribution_gerant(
        type_distribution,
        distributeur
    )

    verifier_presence_ligne(
        lignes
    )

    verifier_stock_distribution(
        utilisateur.profil.point_vente,
        lignes
    )

    # ======================================================
    # CREATION DE LA DISTRIBUTION
    # ======================================================

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=type_distribution,

        commande=None,

        date_distribution=date_distribution,

        point_vente_source=utilisateur.profil.point_vente,

        point_vente_destination=utilisateur.profil.point_vente,

        distributeur=distributeur,

        utilisateur=utilisateur,

    )
    
    # ======================================================
    # CREATION DES LIGNES
    # ======================================================

    creer_lignes_distribution(

        distribution,

        lignes,

    )

    # ======================================================
    # RECALCUL DES TOTAUX
    # ======================================================

    recalculer_totaux_distribution(

        distribution

    )

    # ======================================================
    # TRAITEMENT METIER
    # ======================================================

    traiter_distribution_gerant(

        distribution

    )

    return distribution

# ==========================================================
# TRAITEMENT APRES DISTRIBUTION GERANT
# ==========================================================

@transaction.atomic
def traiter_distribution_gerant(
    distribution
):
    """
    Traitement métier des distributions
    réalisées par un gérant.
    """

    for ligne in distribution.lignes.select_related(

        "produit"

    ):

        retirer_stock(

            point_vente=distribution.point_vente_source,

            produit=ligne.produit,

            quantite=ligne.quantite,

        )

    mettre_a_jour_objectifs_distribution(

        distribution

    )

    if distribution.type_distribution == Distribution.TYPE_CLIENT_DIRECT:

        from situations.services import (
            synchroniser_situation_vente_directe,
        )

        synchroniser_situation_vente_directe(
            distribution,
            distribution.utilisateur
        )


# ==========================================================
# CREATION DES LIGNES DE DISTRIBUTION
# ==========================================================

def creer_lignes_distribution(
    distribution,
    lignes
):
    """
    Crée les lignes d'une distribution.
    """

    lignes_distribution = []

    for ligne in lignes:

        produit = ligne["produit"]

        quantite = Decimal(
            str(ligne["quantite"])
        )

        prix_unitaire = Decimal(
            str(ligne["prix_unitaire"])
        )

        taux = Decimal(
            str(ligne["taux"])
        )

        taux_initial = Decimal(
            str(
                ligne.get(
                    "taux_initial",
                    taux
                )
            )
        )

        montant_brut = Decimal(
            str(ligne["montant"])
        )

        montant_initial = Decimal(
            str(
                ligne.get(
                    "montant_initial",
                    Decimal("0.00")
                )
            )
        )

        montant_net_initial = Decimal(
            str(
                ligne.get(
                    "montant_net_initial",
                    Decimal("0.00")
                )
            )
        )

        montant_remise = calculer_montant_remise(
            montant_brut,
            taux
        )

        montant_net = calculer_montant_net(
            montant_brut,
            montant_remise
        )

        if montant_initial > 0 and montant_net_initial <= 0:

            montant_net_initial = calculer_montant_net(
                montant_initial,
                calculer_montant_remise(
                    montant_initial,
                    taux_initial
                )
            )

        montant_total_brut = (
            montant_initial
            +
            montant_brut
        )

        montant_total_net = (
            montant_net_initial
            +
            montant_net
        )

        # ------------------------------
        # VALIDATIONS
        # ------------------------------

        valider_prix(
            prix_unitaire
        )

        valider_taux_remise(
            taux
        )

        valider_taux_remise(
            taux_initial
        )

        if montant_brut < 0 or montant_initial < 0:

            raise ValueError(
                "Les montants ne peuvent pas etre negatifs."
            )

        if montant_net_initial < 0:

            raise ValueError(
                "Le montant net initial ne peut pas etre negatif."
            )

        if montant_net_initial > montant_initial:

            raise ValueError(
                "Le montant net initial ne peut pas depasser "
                "le montant initial."
            )

        if quantite > 0:

            valider_quantite(
                quantite
            )

        elif montant_initial <= 0:

            valider_quantite(
                quantite
            )

        lignes_distribution.append(

            LigneDistribution(

                distribution=distribution,

                produit=produit,

                prix_unitaire=prix_unitaire,

                montant=montant_brut,

                quantite=quantite,

                taux_remise=taux,

                montant_remise=montant_remise,

                montant_net=montant_net,

                montant_initial=montant_initial,

                montant_net_initial=montant_net_initial,

                montant_total_brut=montant_total_brut,

                montant_total_net=montant_total_net,

            )

        )

    LigneDistribution.objects.bulk_create(
        lignes_distribution
    )

# ==========================================================
# RECALCUL DES TOTAUX
# ==========================================================

def recalculer_totaux_distribution(distribution):
    """
    Recalcule automatiquement les montants
    de la distribution.
    """

    totaux = (
        distribution.lignes.aggregate(

            montant_brut=Sum(
                "montant"
            ),

            montant_remise=Sum(
                "montant_remise"
            ),

            montant_net=Sum(
                "montant_net"
            ),

            montant_initial=Sum(
                "montant_initial"
            ),

            montant_net_initial=Sum(
                "montant_net_initial"
            ),

            montant_total_brut=Sum(
                "montant_total_brut"
            ),

            montant_total_net=Sum(
                "montant_total_net"
            ),

        )
    )

    distribution.montant_brut = (
        totaux["montant_brut"]
        or Decimal("0.00")
    )

    distribution.montant_net = (
        totaux["montant_net"]
        or Decimal("0.00")
    )

    distribution.montant_initial = (
        totaux["montant_initial"]
        or Decimal("0.00")
    )

    distribution.montant_net_initial = (
        totaux["montant_net_initial"]
        or Decimal("0.00")
    )

    distribution.montant_total_brut = (
        totaux["montant_total_brut"]
        or Decimal("0.00")
    )

    distribution.montant_total_net = (
        totaux["montant_total_net"]
        or Decimal("0.00")
    )

    distribution.save(
        update_fields=[
            "montant_brut",
            "montant_net",
            "montant_initial",
            "montant_net_initial",
            "montant_total_brut",
            "montant_total_net",
            "date_modification",
        ]
    )

    return distribution

# ==========================================================
# TRAITEMENT APRES CREATION
# ==========================================================

@transaction.atomic
def traiter_distribution_apres_creation(
    distribution
):
    """
    Exécute les traitements métier
    après la création d'une distribution.
    """

    # ======================================================
    # DISTRIBUTION D'UNE COMMANDE GERANT
    # ======================================================

    if distribution.type_distribution == Distribution.TYPE_COMMANDE_GERANT:

        for ligne in distribution.lignes.select_related("produit"):

            # ----------------------------------------------
            # Transfert du stock Directeur -> Gérant
            # ----------------------------------------------

            transferer_stock(

                point_vente_source=distribution.point_vente_source,

                point_vente_destination=distribution.point_vente_destination,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

            # ----------------------------------------------
            # Mise à jour de la ligne de commande
            # ----------------------------------------------

            ligne_commande = (

                distribution.commande.lignes.get(

                    produit=ligne.produit

                )

            )

            if ligne.quantite > ligne_commande.quantite:

                raise Exception(

                    f"La quantité distribuée du produit "
                    f"{ligne.produit.designation} dépasse "
                    f"la quantité commandée."

                )

            ligne_commande.quantite_distribuee = ligne.quantite

            ligne_commande.save(

                update_fields=[

                    "quantite_distribuee",

                ]

            )

        # --------------------------------------------------
        # Mise à jour de l'état de la commande
        # --------------------------------------------------

        mettre_a_jour_etat_commande(

            distribution.commande

        )

    # ======================================================
    # DISTRIBUTION AU DISTRIBUTEUR
    # ======================================================

    elif distribution.type_distribution == Distribution.TYPE_DISTRIBUTEUR:

        for ligne in distribution.lignes.select_related("produit"):

            retirer_stock(

                point_vente=distribution.point_vente_source,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

        mettre_a_jour_objectifs_distribution(

            distribution

        )

    # ======================================================
    # DISTRIBUTION AU CLIENT DIRECT
    # ======================================================

    elif distribution.type_distribution == Distribution.TYPE_CLIENT_DIRECT:

        for ligne in distribution.lignes.select_related("produit"):

            retirer_stock(

                point_vente=distribution.point_vente_source,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

        mettre_a_jour_objectifs_distribution(

            distribution

        )


# ==========================================================
# MISE A JOUR DE L'ETAT DE LA COMMANDE
# ==========================================================

def mettre_a_jour_etat_commande(
    commande
):
    """
    Met à jour automatiquement
    l'état d'une commande après
    une distribution.
    """

    lignes = commande.lignes.all()

    # Par défaut on considère
    # la commande complètement distribuée.
    commande_complete = True

    for ligne in lignes:

        if ligne.quantite_distribuee < ligne.quantite:

            commande_complete = False

            break

    if commande_complete:

        commande.etat = Commande.VALIDEE

    else:

        commande.etat = Commande.VALIDEE_PARTIELLEMENT

    commande.save(

        update_fields=[

            "etat",
            "date_modification"

        ]

    )

    return commande


# ==========================================================
# MISE A JOUR DES OBJECTIFS
# ==========================================================

def mettre_a_jour_objectifs_distribution(
    distribution
):
    """
    Recalcule les objectifs du point de vente
    après une vente à un distributeur
    ou à un client direct.
    """

    objectifs = Objectif.objects.filter(

        actif=True,

        point_vente=distribution.point_vente_source,

        mois=distribution.date_distribution.month,

        annee=distribution.date_distribution.year

    )

    compagnies = (
        distribution.lignes
        .values_list(
            "produit__compagnie_id",
            flat=True
        )
        .distinct()
    )

    objectifs = objectifs.filter(
        compagnie_id__in=compagnies
    )

    for objectif in objectifs:

        recalculer_objectif(
            objectif
        )


def recalculer_objectifs_distribution_reference(
    point_vente,
    date_reference,
    produit_ids
):
    """
    Recalcule les objectifs touches par une distribution.
    """

    produit_ids = set(
        produit_ids
        or
        []
    )

    if not produit_ids:

        return

    compagnies = (
        Produit.objects
        .filter(
            pk__in=produit_ids
        )
        .values_list(
            "compagnie_id",
            flat=True
        )
        .distinct()
    )

    objectifs = Objectif.objects.filter(
        actif=True,
        point_vente=point_vente,
        mois=date_reference.month,
        annee=date_reference.year,
        compagnie_id__in=compagnies,
    )

    for objectif in objectifs:

        recalculer_objectif(
            objectif
        )


def annuler_effet_stock_distribution(
    distribution
):
    """
    Replace en stock les quantites sorties par une
    distribution terrain ou une vente directe.
    """

    for ligne in distribution.lignes.select_related(
        "produit"
    ):

        ajouter_stock(
            point_vente=distribution.point_vente_source,
            produit=ligne.produit,
            quantite=ligne.quantite,
        )


def appliquer_effet_stock_distribution(
    distribution
):
    """
    Retire du stock les nouvelles quantites d'une
    distribution terrain ou d'une vente directe.
    """

    for ligne in distribution.lignes.select_related(
        "produit"
    ):

        retirer_stock(
            point_vente=distribution.point_vente_source,
            produit=ligne.produit,
            quantite=ligne.quantite,
        )


# ==========================================================
# MODIFICATION D'UNE DISTRIBUTION
# ==========================================================

@transaction.atomic
def modifier_distribution(
    distribution,
    date_distribution,
    distributeur,
    lignes,
    utilisateur
):
    """
    Modifie une distribution terrain
    ou une vente directe.
    """

    # ======================================================
    # VERIFICATION DU DROIT DE MODIFICATION
    # ======================================================

    if not peut_modifier_distribution(
        utilisateur,
        distribution
    ):

        raise ValueError(
            "Cette distribution n'est pas modifiable."
        )

    # ======================================================
    # INTERDICTION DES DISTRIBUTIONS ISSUES D'UNE COMMANDE
    # ======================================================

    if distribution.type_distribution == (
        Distribution.TYPE_COMMANDE_GERANT
    ):

        raise ValueError(
            "Cette distribution provient d'une commande gérant "
            "et ne peut pas être modifiée depuis cet écran."
        )

    # ======================================================
    # VALIDATIONS
    # ======================================================

    verifier_date_distribution(
        date_distribution
    )

    verifier_destinataire_distribution_gerant(
        distribution.type_distribution,
        distributeur
    )

    verifier_presence_ligne(
        lignes
    )

    # ======================================================
    # MEMORISATION DES ANCIENNES INFORMATIONS
    # ======================================================

    ancienne_date = (
        distribution.date_distribution
    )

    ancien_distributeur = (
        distribution.distributeur
    )

    anciens_produits = set(
        distribution.lignes.values_list(
            "produit_id",
            flat=True
        )
    )

    # ======================================================
    # ANNULATION DE L'ANCIEN EFFET SUR LE STOCK
    # ======================================================

    annuler_effet_stock_distribution(
        distribution
    )

    # ======================================================
    # VERIFICATION DU STOCK AVEC LES NOUVELLES LIGNES
    # ======================================================

    verifier_stock_distribution(
        distribution.point_vente_source,
        lignes
    )

    # ======================================================
    # MODIFICATION DE L'ENTETE
    # ======================================================

    distribution.date_distribution = (
        date_distribution
    )

    distribution.distributeur = (
        distributeur
    )

    distribution.point_vente_destination = (
        distribution.point_vente_source
    )

    distribution.save(
        update_fields=[
            "date_distribution",
            "distributeur",
            "point_vente_destination",
            "date_modification",
        ]
    )

    # ======================================================
    # SUPPRESSION DES ANCIENNES LIGNES
    # ======================================================

    distribution.lignes.all().delete()

    # ======================================================
    # CREATION DES NOUVELLES LIGNES
    # ======================================================

    creer_lignes_distribution(
        distribution,
        lignes
    )

    # ======================================================
    # RECALCUL DES TOTAUX
    # ======================================================

    recalculer_totaux_distribution(
        distribution
    )

    # ======================================================
    # APPLICATION DU NOUVEL EFFET SUR LE STOCK
    # ======================================================

    appliquer_effet_stock_distribution(
        distribution
    )

    # ======================================================
    # NOUVEAUX PRODUITS
    # ======================================================

    nouveaux_produits = set(
        distribution.lignes.values_list(
            "produit_id",
            flat=True
        )
    )

    # ======================================================
    # RECALCUL DES ANCIENS OBJECTIFS
    # ======================================================

    recalculer_objectifs_distribution_reference(
        distribution.point_vente_source,
        ancienne_date,
        anciens_produits,
    )

    # ======================================================
    # RECALCUL DES NOUVEAUX OBJECTIFS
    # ======================================================

    recalculer_objectifs_distribution_reference(
        distribution.point_vente_source,
        distribution.date_distribution,
        nouveaux_produits,
    )

    # ======================================================
    # CAS PARTICULIER : VENTE DIRECTE
    # ======================================================

    if distribution.type_distribution == (
        Distribution.TYPE_CLIENT_DIRECT
    ):

        from situations.services import (
            synchroniser_situation_vente_directe,
        )

        from situations.models import (
            SituationJournaliere,
        )

        # --------------------------------------------------
        # Si la date de la vente a changé
        # --------------------------------------------------

        if ancienne_date != distribution.date_distribution:

            autres_ventes_ancienne_date = (
                Distribution.objects
                .filter(
                    actif=True,
                    type_distribution=(
                        Distribution.TYPE_CLIENT_DIRECT
                    ),
                    distributeur=ancien_distributeur,
                    date_distribution=ancienne_date,
                )
                .exclude(
                    pk=distribution.pk
                )
                .exists()
            )

            # --------------------------------------------------
            # Désactivation de l'ancienne situation automatique
            # si aucune autre vente ne subsiste ce jour-là.
            # --------------------------------------------------

            if not autres_ventes_ancienne_date:

                SituationJournaliere.objects.filter(
                    actif=True,
                    distributeur=ancien_distributeur,
                    date_situation=ancienne_date,
                    coupures=(
                        "Situation automatique - vente directe"
                    ),
                ).update(
                    actif=False
                )

        # --------------------------------------------------
        # Synchronisation de la nouvelle situation
        # --------------------------------------------------

        synchroniser_situation_vente_directe(
            distribution,
            utilisateur
        )

    return distribution

# ==========================================================
# CREATION DISTRIBUTION DEPUIS COMMANDE
# ==========================================================

@transaction.atomic
def creer_distribution_depuis_commande(
    commande,
    utilisateur
):
    """
    Crée automatiquement une distribution
    à partir d'une commande gérant.
    """
    verifier_commande_distribuable(
        commande
    )

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=Distribution.TYPE_COMMANDE_GERANT,

        date_distribution=commande.date_commande,

        point_vente_source=utilisateur.profil.point_vente,

        point_vente_destination=commande.point_vente,

        commande=commande,

        distributeur=commande.distributeur,

        utilisateur=utilisateur,

    )

    lignes = []

    for ligne in commande.lignes.all():

        if ligne.quantite <= 0:

            continue

        lignes.append({

            "produit": ligne.produit,

            "prix_unitaire": ligne.prix_unitaire,

            "montant": ligne.montant,

            "quantite": ligne.quantite,

            "taux": ligne.taux_remise,

        })

    creer_lignes_distribution(

        distribution,

        lignes

    )

    recalculer_totaux_distribution(

        distribution

    )

    traiter_distribution_apres_creation(

        distribution

    )

    return distribution

