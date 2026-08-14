"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Services métier du module Situations.

==========================================================
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from distributions.models import Distribution

from .models import (
    SituationJournaliere,
    LigneSituationJournaliere,
    Manquant,
    ReglementManquant,
)

from .calculs import (
    calculer_credit,
    calculer_montant_total_verse,
    calculer_manquant,
    verifier_versement_credit,
)

from .numerotation import (
    generer_numero_situation,
    generer_numero_manquant,
    generer_numero_reglement,
)


# ==========================================================
# RECUPERATION DES DISTRIBUTIONS DE LA JOURNEE
# ==========================================================

def recuperer_distributions_journee(
    distributeur,
    date_situation
):
    """
    Retourne toutes les distributions réalisées
    pour un distributeur à une date donnée.

    Seules les distributions actives sont prises
    en compte.
    """

    return (
        Distribution.objects

        .filter(
            distributeur=distributeur,
            date_distribution=date_situation,
            actif=True,
        )

        .prefetch_related(
            "lignes__produit",
        )

        .order_by(
            "date_distribution",
            "iddistribution",
        )
    )


# ==========================================================
# CALCUL DU MONTANT TOTAL DISTRIBUE
# ==========================================================

def calculer_total_distribue(
    distributeur,
    date_situation
):
    """
    Calcule le montant net total de toutes les
    distributions du distributeur pour la journée.
    """

    total = (

        Distribution.objects

        .filter(
            distributeur=distributeur,
            date_distribution=date_situation,
            actif=True,
        )

        .aggregate(
            total=Sum("montant_net")
        )["total"]

        or Decimal("0.00")
    )

    return total


# ==========================================================
# CALCUL DU CREDIT DU DISTRIBUTEUR
# ==========================================================

def calculer_credit_distributeur(
    distributeur,
    date_situation
):
    """
    Calcule le crédit actuel du distributeur
    à partir de toutes ses distributions de la journée.

    Le crédit correspond à la partie du montant
    total distribué qui dépasse le fond.
    """

    montant_total_distribue = (
        calculer_total_distribue(
            distributeur,
            date_situation
        )
    )

    return calculer_credit(
        montant_total_distribue,
        distributeur.fond
    )


# ==========================================================
# CREATION DES LIGNES DE SITUATION
# ==========================================================

def creer_lignes_situation(
    situation,
    distributions
):
    """
    Construit les lignes de situation à partir
    de toutes les distributions de la journée.

    Pour chaque produit :

        - les quantités distribuées sont cumulées ;
        - le prix unitaire provient de la première
          distribution ;
        - le taux provient de la première distribution
          du produit dans la journée.

    Une seule ligne est créée pour chaque produit.
    """

    produits = {}

    for distribution in distributions:

        for ligne in distribution.lignes.select_related(
            "produit",
            "produit__compagnie",
        ):

            produit_id = ligne.produit.idproduit

            # ------------------------------------------
            # PREMIERE APPARITION DU PRODUIT
            # ------------------------------------------

            if produit_id not in produits:

                produits[produit_id] = {

                    "produit": ligne.produit,

                    "prix_unitaire": (
                        ligne.prix_unitaire
                    ),

                    "taux_remise": (
                        ligne.taux_remise
                    ),

                    "quantite_distribuee": (
                        Decimal("0.00")
                    ),

                }

            # ------------------------------------------
            # CUMUL DES QUANTITES
            # ------------------------------------------

            produits[produit_id][
                "quantite_distribuee"
            ] += ligne.quantite

    # ======================================================
    # CREATION DES LIGNES
    # ======================================================

    lignes = []

    for donnees in produits.values():

        lignes.append(

            LigneSituationJournaliere(

                situation=situation,

                produit=donnees["produit"],

                prix_unitaire=donnees[
                    "prix_unitaire"
                ],

                taux_remise=donnees[
                    "taux_remise"
                ],

                quantite_distribuee=donnees[
                    "quantite_distribuee"
                ],

                quantite_vendue=Decimal(
                    "0.00"
                ),

                quantite_restante=(
                    donnees[
                        "quantite_distribuee"
                    ]
                ),

            )

        )

    LigneSituationJournaliere.objects.bulk_create(
        lignes
    )

    return lignes


# ==========================================================
# CREATION D'UNE SITUATION JOURNALIERE
# ==========================================================

def creer_situation_journaliere(
    distributeur,
    date_situation,
    utilisateur
):
    """
    Crée une situation journalière à partir
    des distributions du distributeur pour la date.

    Une seule situation active est autorisée
    pour un distributeur et une date.

    Le fond est récupéré directement depuis
    le distributeur.

    Le montant total distribué et le crédit
    sont calculés à partir des distributions
    de la journée.
    """

    # ======================================================
    # RECUPERATION DES DISTRIBUTIONS
    # ======================================================

    distributions = (
        recuperer_distributions_journee(
            distributeur,
            date_situation
        )
    )

    if not distributions.exists():

        raise ValueError(
            "Aucune distribution n'a été enregistrée "
            "pour ce distributeur à cette date."
        )

    # ======================================================
    # VERIFICATION D'UNE SITUATION EXISTANTE
    # ======================================================

    situation_existante = (
        SituationJournaliere.objects

        .filter(
            distributeur=distributeur,
            date_situation=date_situation,
            actif=True,
        )

        .first()
    )

    if situation_existante:

        return situation_existante

    # ======================================================
    # CALCULS
    # ======================================================

    montant_total_distribue = (
        calculer_total_distribue(
            distributeur,
            date_situation
        )
    )

    montant_credit = calculer_credit(
        montant_total_distribue,
        distributeur.fond
    )

    # ======================================================
    # CREATION DE LA SITUATION
    # ======================================================

    situation = SituationJournaliere.objects.create(

        numero=generer_numero_situation(),

        date_situation=date_situation,

        distributeur=distributeur,

        point_vente=distributeur.point_vente,

        utilisateur=utilisateur,

        fond=distributeur.fond,

        montant_total_distribue=(
            montant_total_distribue
        ),

        montant_credit=(
            montant_credit
        ),

        montant_credit_verse=Decimal(
            "0.00"
        ),

        montant_vente_verse=Decimal(
            "0.00"
        ),

        montant_total_verse=Decimal(
            "0.00"
        ),

        montant_manquant=Decimal(
            "0.00"
        ),

        etat=(
            SituationJournaliere.ETAT_OUVERTE
        ),

        actif=True,

    )

    # ======================================================
    # CREATION DES LIGNES
    # ======================================================

    creer_lignes_situation(
        situation,
        distributions
    )

    return situation


# ==========================================================
# CALCUL DE LA VALEUR DES PRODUITS RESTANTS
# ==========================================================

def calculer_valeur_produits_restants(
    situation
):
    """
    Calcule la valeur totale des produits
    restant chez le distributeur.
    """

    total = Decimal("0.00")

    for ligne in situation.lignes.all():

        total += (
            ligne.quantite_restante
            *
            ligne.prix_unitaire
        )

    return total


# ==========================================================
# MISE A JOUR DU TOTAL VERSE
# ==========================================================

def mettre_a_jour_total_verse(
    situation
):
    """
    Recalcule le montant total versé.
    """

    situation.montant_total_verse = (

        calculer_montant_total_verse(

            situation.montant_credit_verse,

            situation.montant_vente_verse

        )

    )

    return situation


# ==========================================================
# CALCUL DU MANQUANT
# ==========================================================

def calculer_manquant_situation(
    situation
):
    """
    Calcule le montant manquant d'une situation.

    Le fond doit être reconstitué par :

        montant des ventes versé
        +
        valeur des produits restants.
    """

    montant_produits_restants = (

        calculer_valeur_produits_restants(
            situation
        )

    )

    return calculer_manquant(

        situation.fond,

        situation.montant_vente_verse,

        montant_produits_restants

    )


# ==========================================================
# CREATION DU MANQUANT
# ==========================================================

def creer_manquant_situation(
    situation,
    montant_manquant,
    utilisateur
):
    """
    Crée le manquant correspondant à une situation
    lorsque le montant manquant est supérieur à zéro.
    """

    if montant_manquant <= 0:

        return None

    manquant = Manquant.objects.create(

        numero=generer_numero_manquant(),

        situation=situation,

        distributeur=situation.distributeur,

        montant=montant_manquant,

        reste_a_payer=montant_manquant,

        statut=Manquant.STATUT_EN_COURS,

        utilisateur=utilisateur,

    )

    return manquant


# ==========================================================
# CLOTURE D'UNE SITUATION JOURNALIERE
# ==========================================================

@transaction.atomic
def cloturer_situation(
    situation,
    donnees_lignes,
    montant_credit_verse,
    montant_vente_verse,
    coupures,
    utilisateur,
):
    """
    Clôture une situation journalière.

    Le montant vendu saisi pour chaque produit
    correspond directement au montant NET vendu.

    La quantité vendue est calculée automatiquement :

        montant vendu / prix unitaire

    La quantité restante est calculée automatiquement :

        quantité distribuée - quantité vendue
    """

    # ======================================================
    # VERIFICATION DE L'ETAT
    # ======================================================

    if situation.etat == SituationJournaliere.ETAT_CLOTUREE:

        raise ValueError(
            "Cette situation journalière est déjà clôturée."
        )

    # ======================================================
    # CONVERSION DES MONTANTS
    # ======================================================

    montant_credit_verse = Decimal(
        str(montant_credit_verse or "0")
    )

    montant_vente_verse = Decimal(
        str(montant_vente_verse or "0")
    )

    # ======================================================
    # VERIFICATION DES MONTANTS
    # ======================================================

    if montant_credit_verse < 0:

        raise ValueError(
            "Le montant du crédit versé "
            "ne peut pas être négatif."
        )

    if montant_vente_verse < 0:

        raise ValueError(
            "Le montant des ventes versé "
            "ne peut pas être négatif."
        )

    # ======================================================
    # VERIFICATION DU CREDIT
    # ======================================================

    verifier_versement_credit(
        situation.montant_credit,
        montant_credit_verse
    )

    # ======================================================
    # MISE A JOUR DES LIGNES
    # ======================================================

    for ligne in situation.lignes.select_related(
        "produit"
    ):

        donnees = donnees_lignes.get(
            str(ligne.idlignesituation)
        )

        if not donnees:

            raise ValueError(
                f"Les données du produit "
                f"« {ligne.produit.designation} » "
                f"sont absentes."
            )

        # --------------------------------------------------
        # MONTANT NET VENDU SAISI
        # --------------------------------------------------

        montant_vendu = Decimal(
            str(
                donnees.get(
                    "montant_vendu",
                    "0"
                )
            )
        )

        if montant_vendu < 0:

            raise ValueError(
                f"Le montant vendu du produit "
                f"« {ligne.produit.designation} » "
                f"ne peut pas être négatif."
            )

        # --------------------------------------------------
        # PRIX
        # --------------------------------------------------

        prix = Decimal(
            str(ligne.prix_unitaire)
        )

        if prix <= 0:

            raise ValueError(
                f"Le prix du produit "
                f"« {ligne.produit.designation} » "
                f"est invalide."
            )

        # --------------------------------------------------
        # VERIFICATION DU MULTIPLE
        # --------------------------------------------------

        if montant_vendu % prix != 0:

            raise ValueError(
                f"Le montant vendu du produit "
                f"« {ligne.produit.designation} » "
                f"doit être un multiple de "
                f"{prix} FCFA."
            )

        # --------------------------------------------------
        # CALCUL DE LA QUANTITE VENDUE
        # --------------------------------------------------

        quantite_vendue = (
            montant_vendu / prix
        )

        # --------------------------------------------------
        # VERIFICATION DE LA QUANTITE
        # --------------------------------------------------

        if (
            quantite_vendue
            >
            ligne.quantite_distribuee
        ):

            raise ValueError(
                f"La quantité vendue du produit "
                f"« {ligne.produit.designation} » "
                f"dépasse la quantité distribuée."
            )

        # --------------------------------------------------
        # CALCUL DE LA QUANTITE RESTANTE
        # --------------------------------------------------

        quantite_restante = (
            ligne.quantite_distribuee
            -
            quantite_vendue
        )

        # --------------------------------------------------
        # MISE A JOUR
        # --------------------------------------------------

        ligne.quantite_vendue = (
            quantite_vendue
        )

        ligne.quantite_restante = (
            quantite_restante
        )

        ligne.save(
            update_fields=[
                "quantite_vendue",
                "quantite_restante",
            ]
        )

    # ======================================================
    # MONTANTS
    # ======================================================

    situation.montant_credit_verse = (
        montant_credit_verse
    )

    situation.montant_vente_verse = (
        montant_vente_verse
    )

    # ======================================================
    # TOTAL VERSE
    # ======================================================

    mettre_a_jour_total_verse(
        situation
    )

    # ======================================================
    # VALEUR DES PRODUITS RESTANTS
    # ======================================================

    montant_produits_restants = (
        calculer_valeur_produits_restants(
            situation
        )
    )

    # ======================================================
    # MANQUANT
    # ======================================================

    montant_manquant = calculer_manquant(

        situation.fond,

        situation.montant_vente_verse,

        montant_produits_restants

    )

    situation.montant_manquant = (
        montant_manquant
    )

    # ======================================================
    # COUPURES
    # ======================================================

    if coupures:

        situation.coupures = (

            f"10000 x {coupures.get('10000', 0)}\n"
            f"5000 x {coupures.get('5000', 0)}\n"
            f"2000 x {coupures.get('2000', 0)}\n"
            f"1000 x {coupures.get('1000', 0)}\n"
            f"500 x {coupures.get('500', 0)}"

        )

    else:

        situation.coupures = ""

    # ======================================================
    # CREATION DU MANQUANT
    # ======================================================

    if montant_manquant > 0:

        creer_manquant_situation(

            situation,

            montant_manquant,

            utilisateur

        )

    # ======================================================
    # CLOTURE
    # ======================================================

    situation.etat = (
        SituationJournaliere.ETAT_CLOTUREE
    )

    situation.save()

    return situation


# ==========================================================
# REGLEMENT D'UN MANQUANT
# ==========================================================

@transaction.atomic
def regler_manquant(
    manquant,
    date_reglement,
    montant,
    utilisateur,
):
    """
    Enregistre un règlement partiel ou total
    d'un manquant.
    """

    if manquant.statut == Manquant.STATUT_SOLDE:

        raise ValueError(
            "Ce manquant est déjà soldé."
        )

    montant = Decimal(
        str(montant or "0")
    )

    if montant <= 0:

        raise ValueError(
            "Le montant du règlement doit être supérieur à zéro."
        )

    if montant > manquant.reste_a_payer:

        raise ValueError(
            "Le montant du règlement dépasse le reste à payer."
        )

    reglement = ReglementManquant.objects.create(

        numero=generer_numero_reglement(),

        manquant=manquant,

        date_reglement=date_reglement,

        montant=montant,

        utilisateur=utilisateur,

    )

    manquant.reste_a_payer = (
        manquant.reste_a_payer
        -
        montant
    )

    if manquant.reste_a_payer <= 0:

        manquant.reste_a_payer = Decimal(
            "0.00"
        )

        manquant.statut = Manquant.STATUT_SOLDE

    else:

        manquant.statut = Manquant.STATUT_EN_COURS

    manquant.save(
        update_fields=[
            "reste_a_payer",
            "statut",
            "date_modification",
        ]
    )

    return reglement
