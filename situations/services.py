"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Services métier du module Situations.

==========================================================
"""

from decimal import Decimal

from types import SimpleNamespace

from django.db import transaction
from django.db.models import Sum

from distributions.models import Distribution

from referentiel.models import Distributeur

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

def types_distribution_pour_distributeur(distributeur):
    """
    Retourne les types de distribution attendus
    selon la categorie du destinataire.
    """

    if distributeur.categorie == Distributeur.CATEGORIE_GERANT:

        return [
            Distribution.TYPE_COMMANDE_GERANT,
        ]

    if distributeur.categorie == Distributeur.CATEGORIE_DISTRIBUTEUR:

        return [
            Distribution.TYPE_DISTRIBUTEUR,
        ]

    if distributeur.categorie == Distributeur.CATEGORIE_CLIENT:

        return [
            Distribution.TYPE_CLIENT_DIRECT,
        ]

    return []


def recuperer_distributions_journee(
    distributeur,
    date_situation,
    inclure_cloturees=False
):
    """
    Retourne toutes les distributions réalisées
    pour un distributeur à une date donnée.

    Seules les distributions actives et ouvertes sont
    prises en compte par defaut.
    """

    types_distribution = types_distribution_pour_distributeur(
        distributeur
    )

    distributions = (
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

    if types_distribution:

        distributions = distributions.filter(
            type_distribution__in=types_distribution
        )

    if not inclure_cloturees:

        distributions = distributions.filter(
            etat=Distribution.ETAT_OUVERTE
        )

    return distributions


def cloturer_distributions_situation(
    situation
):
    """
    Marque comme cloturees les distributions ouvertes
    rattachees a la situation.
    """

    distributions = recuperer_distributions_journee(
        situation.distributeur,
        situation.date_situation
    )

    return distributions.update(
        etat=Distribution.ETAT_CLOTUREE
    )


# ==========================================================
# CALCUL DU MONTANT TOTAL DISTRIBUE
# ==========================================================

def derniere_situation_cloturee_avant(
    distributeur,
    date_situation
):
    """
    Retourne la derniere situation cloturee avant
    la date traitee.
    """

    return (
        SituationJournaliere.objects
        .filter(
            distributeur=distributeur,
            date_situation__lt=date_situation,
            etat=SituationJournaliere.ETAT_CLOTUREE,
            actif=True,
        )
        .prefetch_related(
            "lignes__produit__compagnie",
        )
        .order_by(
            "-date_situation",
            "-idsituation",
        )
        .first()
    )


def calculer_valeur_nette_quantite(
    quantite,
    prix_unitaire,
    taux_remise=0
):
    """
    Valorise une quantite au prix net de remise.
    """

    montant_brut = (
        Decimal(str(quantite))
        *
        Decimal(str(prix_unitaire))
    )

    remise = (
        montant_brut
        *
        Decimal(str(taux_remise or 0))
        /
        Decimal("100")
    )

    return (
        montant_brut
        -
        remise
    )


def calculer_valeur_brute_quantite(
    quantite,
    prix_unitaire
):
    """
    Valorise une quantite au prix brut.
    """

    return (
        Decimal(str(quantite))
        *
        Decimal(str(prix_unitaire))
    )


def calculer_valeur_reliquat_precedent(
    distributeur,
    date_situation
):
    """
    Calcule la valeur brute des quantites restantes
    de la derniere situation cloturee.
    """

    situation = derniere_situation_cloturee_avant(
        distributeur,
        date_situation
    )

    if situation is None:

        return Decimal("0.00")

    total = Decimal("0.00")

    for ligne in situation.lignes.all():

        if ligne.quantite_restante <= 0:

            continue

        total += calculer_valeur_brute_quantite(
            ligne.quantite_restante,
            ligne.prix_unitaire,
        )

    return total


def calculer_total_distribue(
    distributeur,
    date_situation
):
    """
    Calcule le montant brut total de toutes les
    distributions du distributeur pour la journée.
    """

    types_distribution = types_distribution_pour_distributeur(
        distributeur
    )

    distributions = (

        Distribution.objects

        .filter(
            distributeur=distributeur,
            date_distribution=date_situation,
            actif=True,
            etat=Distribution.ETAT_OUVERTE,
        )
    )

    if types_distribution:

        distributions = distributions.filter(
            type_distribution__in=types_distribution
        )

    total = (
        distributions

        .aggregate(
            total=Sum("montant_brut")
        )["total"]

        or Decimal("0.00")
    )

    total += calculer_valeur_reliquat_precedent(
        distributeur,
        date_situation
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

def construire_donnees_lignes_situation(
    distributeur,
    date_situation,
    distributions=None
):
    """
    Construit les lignes metier d'une situation.

    La quantite distribuee du jour inclut une seule fois
    le reliquat de la derniere situation cloturee.
    """

    if distributions is None:

        distributions = recuperer_distributions_journee(
            distributeur,
            date_situation
        )

    produits = {}

    situation_precedente = derniere_situation_cloturee_avant(
        distributeur,
        date_situation
    )

    if situation_precedente is not None:

        for ligne in situation_precedente.lignes.select_related(
            "produit",
            "produit__compagnie",
        ):

            if ligne.quantite_restante <= 0:

                continue

            produit_id = ligne.produit.idproduit

            produits[produit_id] = {
                "produit": ligne.produit,
                "prix_unitaire": ligne.prix_unitaire,
                "taux_remise": ligne.taux_remise,
                "taux_distribution": ligne.taux_remise,
                "quantite_initiale": ligne.quantite_restante,
                "quantite_jour": Decimal("0.00"),
                "quantite_distribuee": ligne.quantite_restante,
                "montant_distribue": (
                    calculer_valeur_brute_quantite(
                        ligne.quantite_restante,
                        ligne.prix_unitaire,
                    )
                ),
                "montant_net_distribue": (
                    calculer_valeur_nette_quantite(
                        ligne.quantite_restante,
                        ligne.prix_unitaire,
                        ligne.taux_remise,
                    )
                ),
            }

    for distribution in distributions:

        for ligne in distribution.lignes.select_related(
            "produit",
            "produit__compagnie",
        ):

            produit_id = ligne.produit.idproduit

            if produit_id not in produits:

                produits[produit_id] = {
                    "produit": ligne.produit,
                    "prix_unitaire": ligne.prix_unitaire,
                    "taux_remise": ligne.taux_remise,
                    "taux_distribution": ligne.taux_remise,
                    "quantite_initiale": Decimal("0.00"),
                    "quantite_jour": Decimal("0.00"),
                    "quantite_distribuee": Decimal("0.00"),
                    "montant_distribue": Decimal("0.00"),
                    "montant_net_distribue": Decimal("0.00"),
                }

            produits[produit_id]["quantite_jour"] += ligne.quantite

            produits[produit_id]["quantite_distribuee"] += ligne.quantite

            produits[produit_id]["montant_distribue"] += (
                ligne.montant
            )

            produits[produit_id]["montant_net_distribue"] += (
                ligne.montant_net
            )

            if produits[produit_id]["taux_distribution"] == Decimal("0.00"):

                produits[produit_id]["taux_distribution"] = (
                    ligne.taux_remise
                )

    return list(
        produits.values()
    )


def construire_lignes_affichage_situation(
    distributeur,
    date_situation,
    distributions=None
):
    """
    Construit des lignes temporaires affichables dans
    le formulaire de situation avant creation en base.
    """

    lignes = []

    for donnees in construire_donnees_lignes_situation(
        distributeur,
        date_situation,
        distributions
    ):

        lignes.append(
            SimpleNamespace(
                idlignesituation=None,
                produit=donnees["produit"],
                prix_unitaire=donnees["prix_unitaire"],
                quantite_initiale=donnees["quantite_initiale"],
                quantite_jour=donnees["quantite_jour"],
                quantite_distribuee=donnees["quantite_distribuee"],
                montant_distribue=donnees["montant_distribue"],
                montant_net_distribue=donnees["montant_net_distribue"],
                quantite_vendue=Decimal("0.00"),
                quantite_restante=donnees["quantite_distribuee"],
                taux_distribution=donnees["taux_distribution"],
            )
        )

    return lignes


def annoter_lignes_reliquat(
    lignes,
    distributeur,
    date_situation,
    distributions=None
):
    """
    Ajoute les informations de reliquat aux lignes
    existantes pour l'affichage.
    """

    donnees_par_produit = {
        donnees["produit"].idproduit: donnees
        for donnees in construire_donnees_lignes_situation(
            distributeur,
            date_situation,
            distributions
        )
    }

    for ligne in lignes:

        donnees = donnees_par_produit.get(
            ligne.produit.idproduit,
            {}
        )

        ligne.quantite_initiale = donnees.get(
            "quantite_initiale",
            Decimal("0.00")
        )

        ligne.quantite_jour = donnees.get(
            "quantite_jour",
            Decimal("0.00")
        )

        ligne.taux_distribution = donnees.get(
            "taux_distribution",
            Decimal("0.00")
        )

        ligne.montant_distribue = donnees.get(
            "montant_distribue",
            calculer_valeur_brute_quantite(
                ligne.quantite_distribuee,
                ligne.prix_unitaire,
            )
        )

        ligne.montant_net_distribue = donnees.get(
            "montant_net_distribue",
            calculer_valeur_nette_quantite(
                ligne.quantite_distribuee,
                ligne.prix_unitaire,
                ligne.taux_remise,
            )
        )

    return lignes


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

    donnees_lignes = construire_donnees_lignes_situation(
        situation.distributeur,
        situation.date_situation,
        distributions
    )

    # ======================================================
    # CREATION DES LIGNES
    # ======================================================

    lignes = []

    for donnees in donnees_lignes:

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
# SITUATION AUTOMATIQUE D'UNE VENTE DIRECTE
# ==========================================================

@transaction.atomic
def synchroniser_situation_vente_directe(
    distribution,
    utilisateur
):
    """
    Cree ou met a jour la situation automatique liee
    aux ventes directes d'un client pour une journee.
    """

    if distribution.type_distribution != Distribution.TYPE_CLIENT_DIRECT:

        return None

    if distribution.distributeur.categorie != Distributeur.CATEGORIE_CLIENT:

        raise ValueError(
            "Une vente directe doit etre rattachee "
            "a un client direct."
        )

    distributions = (
        Distribution.objects
        .filter(
            actif=True,
            type_distribution=Distribution.TYPE_CLIENT_DIRECT,
            distributeur=distribution.distributeur,
            date_distribution=distribution.date_distribution,
        )
        .prefetch_related(
            "lignes__produit__compagnie",
        )
    )

    montant_total = (
        distributions.aggregate(
            total=Sum("montant_net")
        )["total"]
        or Decimal("0.00")
    )

    situation, created = SituationJournaliere.objects.get_or_create(
        distributeur=distribution.distributeur,
        date_situation=distribution.date_distribution,
        actif=True,
        defaults={
            "numero": generer_numero_situation(),
            "point_vente": distribution.point_vente_source,
            "utilisateur": utilisateur,
        }
    )

    situation.point_vente = distribution.point_vente_source
    situation.utilisateur = utilisateur
    situation.fond = Decimal("0.00")
    situation.montant_total_distribue = montant_total
    situation.montant_credit = Decimal("0.00")
    situation.montant_credit_verse = Decimal("0.00")
    situation.montant_vente_verse = montant_total
    situation.montant_total_verse = montant_total
    situation.montant_manquant = Decimal("0.00")
    situation.coupures = "Situation automatique - vente directe"
    situation.etat = SituationJournaliere.ETAT_CLOTUREE
    situation.actif = True
    situation.save()

    if not created:

        situation.lignes.all().delete()

    produits = {}

    for distribution_directe in distributions:

        for ligne in distribution_directe.lignes.select_related(
            "produit",
            "produit__compagnie",
        ):

            produit_id = ligne.produit.idproduit

            if produit_id not in produits:

                produits[produit_id] = {
                    "produit": ligne.produit,
                    "prix_unitaire": ligne.prix_unitaire,
                    "taux_remise": ligne.taux_remise,
                    "quantite": Decimal("0.00"),
                }

            produits[produit_id]["quantite"] += ligne.quantite

    lignes = []

    for donnees in produits.values():

        lignes.append(
            LigneSituationJournaliere(
                situation=situation,
                produit=donnees["produit"],
                prix_unitaire=donnees["prix_unitaire"],
                taux_remise=donnees["taux_remise"],
                quantite_distribuee=donnees["quantite"],
                quantite_vendue=donnees["quantite"],
                quantite_restante=Decimal("0.00"),
            )
        )

    LigneSituationJournaliere.objects.bulk_create(
        lignes
    )

    distributions.update(
        etat=Distribution.ETAT_CLOTUREE
    )

    return situation


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

        toutes_distributions = recuperer_distributions_journee(
            distributeur,
            date_situation,
            inclure_cloturees=True
        )

        if toutes_distributions.exists():

            raise ValueError(
                "Toutes les distributions de cette personne "
                "pour la date sélectionnée sont clôturées."
            )

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

        total += calculer_valeur_nette_quantite(
            ligne.quantite_restante,
            ligne.prix_unitaire,
            ligne.taux_remise,
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

    Le montant distribue doit etre justifie par :

        credit verse + ventes versees.
    """

    return calculer_manquant(

        situation.montant_total_distribue,

        situation.montant_credit_verse,

        situation.montant_vente_verse,

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

    Le montant restant saisi pour chaque produit
    correspond au montant brut restant.

    La quantité restante est calculée automatiquement :

        montant brut restant / prix unitaire

    La quantité vendue est calculée automatiquement :

        quantité distribuée - quantité restante
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

    situation.montant_total_distribue = calculer_total_distribue(
        situation.distributeur,
        situation.date_situation
    )

    situation.montant_credit = calculer_credit(
        situation.montant_total_distribue,
        situation.fond
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
        # MONTANT BRUT RESTANT SAISI
        # --------------------------------------------------

        montant_restant = Decimal(
            str(
                donnees.get(
                    "montant_restant",
                    "0"
                )
            )
        )

        if montant_restant < 0:

            raise ValueError(
                f"Le montant restant du produit "
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

        if montant_restant % prix != 0:

            raise ValueError(
                f"Le montant restant du produit "
                f"« {ligne.produit.designation} » "
                f"doit être un multiple de "
                f"{prix} FCFA."
            )

        # --------------------------------------------------
        # CALCUL DE LA QUANTITE RESTANTE
        # --------------------------------------------------

        quantite_restante = (
            montant_restant / prix
        )

        # --------------------------------------------------
        # VERIFICATION DE LA QUANTITE
        # --------------------------------------------------

        if (
            quantite_restante
            >
            ligne.quantite_distribuee
        ):

            raise ValueError(
                f"La quantité restante du produit "
                f"« {ligne.produit.designation} » "
                f"dépasse la quantité distribuée."
            )

        # --------------------------------------------------
        # CALCUL DE LA QUANTITE VENDUE
        # --------------------------------------------------

        quantite_vendue = (
            ligne.quantite_distribuee
            -
            quantite_restante
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
    # MANQUANT
    # ======================================================

    montant_manquant = calculer_manquant(

        situation.montant_total_distribue,

        situation.montant_credit_verse,

        situation.montant_vente_verse,

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

    cloturer_distributions_situation(
        situation
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
