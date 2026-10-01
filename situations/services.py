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

from commandes.models import (
    Commande,
    LigneCommande,
)

from distributions.models import (
    Distribution,
    LigneDistribution,
)

from stocks.models import (
    Stock,
    TYPE_NORMAL,
)

from referentiel.models import (
    Distributeur,
    Produit,
)

from .models import (
    SituationJournaliere,
    LigneSituationJournaliere,
    SituationGerant,
    LigneSituationGerant,
    Manquant,
    ReglementManquant,
)

from .calculs import (
    calculer_credit,
    calculer_montant_total_verse,
    ventiler_versement,
)

from .numerotation import (
    generer_numero_situation,
    generer_numero_situation_gerant,
    generer_numero_manquant,
    generer_numero_reglement,
)

from .permissions import (
    peut_modifier_reglement_manquant,
    peut_modifier_situation,
)


# ==========================================================
# SERVICES : SITUATION GERANT
# ==========================================================

ZERO = Decimal("0.00")


def _montant(valeur):
    """
    Normalise une valeur monetaire.
    """

    return valeur or ZERO


def gerant_du_point_vente(point_vente):
    """
    Retourne le gerant actif rattache au point de vente.
    """

    if point_vente is None:

        return None

    return (
        Distributeur.objects
        .filter(
            actif=True,
            categorie=Distributeur.CATEGORIE_GERANT,
            point_vente=point_vente,
        )
        .order_by(
            "nom",
            "prenom",
        )
        .first()
    )


def _ajouter_montant(dictionnaire, produit_id, montant):
    """
    Additionne un montant dans un dictionnaire par produit.
    """

    dictionnaire[produit_id] = (
        dictionnaire.get(
            produit_id,
            ZERO
        )
        + _montant(
            montant
        )
    )


def _montants_commandes_gerant_par_produit(
    point_vente,
    date_situation,
):
    """
    Total brut des commandes normales validees du gerant.
    """

    montants = {}

    if point_vente is None:

        return montants

    lignes = (
        LigneCommande.objects
        .filter(
            commande__actif=True,
            commande__point_vente=point_vente,
            commande__type_commande=Commande.TYPE_GERANT,
            commande__categorie_commande=(
                Commande.CATEGORIE_NORMALE
            ),
            commande__etat__in=[
                Commande.VALIDEE,
                Commande.VALIDEE_PARTIELLEMENT,
            ],
            commande__date_commande=date_situation,
        )
        .select_related(
            "produit"
        )
    )

    for ligne in lignes:

        _ajouter_montant(
            montants,
            ligne.produit_id,
            ligne.montant,
        )

    return montants


def _montants_stock_normal_par_produit(point_vente):
    """
    Valorise le stock normal courant du point de vente.
    """

    montants = {}

    if point_vente is None:

        return montants

    stocks = (
        Stock.objects
        .filter(
            actif=True,
            point_vente=point_vente,
            type_stock=TYPE_NORMAL,
            quantite__gt=0,
        )
        .select_related(
            "produit"
        )
    )

    for stock in stocks:

        _ajouter_montant(
            montants,
            stock.produit_id,
            (
                _montant(stock.quantite)
                *
                _montant(stock.produit.prix)
            ),
        )

    return montants


def _montants_distributions_gerant_par_produit(
    point_vente,
    date_situation,
    type_distribution,
):
    """
    Total brut des distributions ou ventes faites par le gerant.
    """

    montants = {}

    if point_vente is None:

        return montants

    lignes = (
        LigneDistribution.objects
        .filter(
            distribution__actif=True,
            distribution__point_vente_source=point_vente,
            distribution__type_distribution=type_distribution,
            distribution__date_distribution=date_situation,
        )
        .select_related(
            "produit"
        )
    )

    for ligne in lignes:

        _ajouter_montant(
            montants,
            ligne.produit_id,
            ligne.montant,
        )

    return montants


def _montants_retours_distributeurs_par_produit(
    point_vente,
    date_situation,
):
    """
    Somme brute des montants restants des versements distributeurs.
    """

    montants = {}

    if point_vente is None:

        return montants

    lignes = (
        LigneSituationJournaliere.objects
        .filter(
            situation__actif=True,
            situation__etat=SituationJournaliere.ETAT_CLOTUREE,
            situation__point_vente=point_vente,
            situation__date_situation=date_situation,
            situation__distributeur__categorie=(
                Distributeur.CATEGORIE_DISTRIBUTEUR
            ),
        )
        .select_related(
            "produit"
        )
    )

    for ligne in lignes:

        _ajouter_montant(
            montants,
            ligne.produit_id,
            (
                _montant(ligne.quantite_restante)
                *
                _montant(ligne.prix_unitaire)
            ),
        )

    return montants


def _montants_derniere_situation_gerant_par_produit(
    point_vente,
    date_situation,
):
    """
    Recupere le total restant de la derniere situation anterieure.
    """

    montants = {}

    if point_vente is None:

        return montants

    derniere_situation = (
        SituationGerant.objects
        .filter(
            actif=True,
            point_vente=point_vente,
            date_situation__lt=date_situation,
        )
        .prefetch_related(
            "lignes"
        )
        .order_by(
            "-date_situation",
            "-idsituationgerant",
        )
        .first()
    )

    if derniere_situation is None:

        return montants

    for ligne in derniere_situation.lignes.all():

        montants[ligne.produit_id] = _montant(
            ligne.total_restant
        )

    return montants


def _produits_situation_gerant(*dictionnaires):
    """
    Retourne les produits presents dans au moins un montant.
    """

    ids_produits = set()

    for dictionnaire in dictionnaires:

        ids_produits.update(
            dictionnaire.keys()
        )

    return (
        Produit.objects
        .filter(
            pk__in=ids_produits
        )
        .select_related(
            "compagnie"
        )
        .order_by(
            "compagnie__designation",
            "designation",
        )
    )


def _somme_lignes_situation_gerant(lignes, champ):
    """
    Additionne un champ monetaire sur des lignes.
    """

    return sum(
        (
            getattr(
                ligne,
                champ
            )
            for ligne in lignes
        ),
        ZERO
    )


def _sous_total_situation_gerant(lignes):
    """
    Calcule les sous-totaux d'un groupe de lignes.
    """

    return {
        "montant_residuel_j_1": _somme_lignes_situation_gerant(
            lignes,
            "montant_residuel_j_1"
        ),
        "montant_du_jour": _somme_lignes_situation_gerant(
            lignes,
            "montant_du_jour"
        ),
        "total_du_jour": _somme_lignes_situation_gerant(
            lignes,
            "total_du_jour"
        ),
        "montant_distribue": _somme_lignes_situation_gerant(
            lignes,
            "montant_distribue"
        ),
        "montant_vendu": _somme_lignes_situation_gerant(
            lignes,
            "montant_vendu"
        ),
        "montant_retour": _somme_lignes_situation_gerant(
            lignes,
            "montant_retour"
        ),
        "total_vendu": _somme_lignes_situation_gerant(
            lignes,
            "total_vendu"
        ),
        "total_restant": _somme_lignes_situation_gerant(
            lignes,
            "total_restant"
        ),
    }


def preparer_affichage_situations_gerant(situations):
    """
    Regroupe les lignes de situation gerant par compagnie.
    """

    for situation in situations:

        groupes = {}

        for ligne in situation.lignes.all():

            compagnie = ligne.produit.compagnie

            if compagnie.pk not in groupes:

                groupes[compagnie.pk] = {
                    "compagnie": compagnie,
                    "lignes": [],
                }

            groupes[compagnie.pk]["lignes"].append(
                ligne
            )

        for groupe in groupes.values():

            groupe["sous_totaux"] = _sous_total_situation_gerant(
                groupe["lignes"]
            )

        situation.groupes_compagnies = groupes.values()


@transaction.atomic
def calculer_situation_gerant(
    utilisateur,
    date_situation,
):
    """
    Calcule ou recalcule la situation journaliere du gerant.
    """

    point_vente = utilisateur.profil.point_vente

    gerant = gerant_du_point_vente(
        point_vente
    )

    residuels_anterieurs = (
        _montants_derniere_situation_gerant_par_produit(
            point_vente,
            date_situation,
        )
    )

    commandes_jour = _montants_commandes_gerant_par_produit(
        point_vente,
        date_situation,
    )

    if not commandes_jour:

        commandes_jour = _montants_stock_normal_par_produit(
            point_vente
        )

    distributions_jour = _montants_distributions_gerant_par_produit(
        point_vente,
        date_situation,
        Distribution.TYPE_DISTRIBUTEUR,
    )

    ventes_jour = _montants_distributions_gerant_par_produit(
        point_vente,
        date_situation,
        Distribution.TYPE_CLIENT_DIRECT,
    )

    retours_jour = _montants_retours_distributeurs_par_produit(
        point_vente,
        date_situation,
    )

    produits = _produits_situation_gerant(
        residuels_anterieurs,
        commandes_jour,
        distributions_jour,
        ventes_jour,
        retours_jour,
    )

    situation, created = (
        SituationGerant.objects
        .get_or_create(
            point_vente=point_vente,
            date_situation=date_situation,
            actif=True,
            defaults={
                "numero": generer_numero_situation_gerant(),
                "gerant": gerant,
                "utilisateur": utilisateur,
            }
        )
    )

    if not created:

        situation.gerant = gerant

        situation.utilisateur = utilisateur

        situation.lignes.all().delete()

    lignes = []

    for produit in produits:

        produit_id = produit.pk

        montant_residuel_j_1 = residuels_anterieurs.get(
            produit_id,
            ZERO
        )

        montant_du_jour = commandes_jour.get(
            produit_id,
            ZERO
        )

        montant_distribue = distributions_jour.get(
            produit_id,
            ZERO
        )

        montant_vendu = ventes_jour.get(
            produit_id,
            ZERO
        )

        montant_retour = retours_jour.get(
            produit_id,
            ZERO
        )

        total_vendu = (
            montant_distribue
            +
            montant_vendu
        )

        lignes.append(
            LigneSituationGerant(
                situation=situation,
                produit=produit,
                prix_unitaire=produit.prix,
                montant_residuel_j_1=montant_residuel_j_1,
                montant_du_jour=montant_du_jour,
                total_du_jour=(
                    montant_residuel_j_1
                    +
                    montant_du_jour
                ),
                montant_distribue=montant_distribue,
                montant_vendu=montant_vendu,
                montant_retour=montant_retour,
                total_vendu=total_vendu,
                total_restant=(
                    montant_retour
                    +
                    (
                        montant_residuel_j_1
                        +
                        montant_du_jour
                        -
                        total_vendu
                    )
                ),
            )
        )

    LigneSituationGerant.objects.bulk_create(
        lignes
    )

    situation.montant_residuel_j_1 = _somme_lignes_situation_gerant(
        lignes,
        "montant_residuel_j_1"
    )

    situation.montant_du_jour = _somme_lignes_situation_gerant(
        lignes,
        "montant_du_jour"
    )

    situation.total_du_jour = _somme_lignes_situation_gerant(
        lignes,
        "total_du_jour"
    )

    situation.montant_distribue = _somme_lignes_situation_gerant(
        lignes,
        "montant_distribue"
    )

    situation.montant_vendu = _somme_lignes_situation_gerant(
        lignes,
        "montant_vendu"
    )

    situation.montant_retour = _somme_lignes_situation_gerant(
        lignes,
        "montant_retour"
    )

    situation.total_vendu = _somme_lignes_situation_gerant(
        lignes,
        "total_vendu"
    )

    situation.total_restant = _somme_lignes_situation_gerant(
        lignes,
        "total_restant"
    )

    situation.save(
        update_fields=[
            "gerant",
            "utilisateur",
            "montant_residuel_j_1",
            "montant_du_jour",
            "total_du_jour",
            "montant_distribue",
            "montant_vendu",
            "montant_retour",
            "total_vendu",
            "total_restant",
            "date_modification",
        ]
    )

    return situation


def montants_initiaux_commande_gerant(utilisateur):
    """
    Retourne le montant restant brut par produit du dernier
    versement gerant valide par le Directeur.
    """

    if utilisateur.profil.role != "GERANT":

        return {}

    point_vente = utilisateur.profil.point_vente

    if point_vente is None:

        return {}

    gerant = gerant_du_point_vente(
        point_vente
    )

    if gerant is None:

        return {}

    date_derniere = (
        SituationJournaliere.objects
        .filter(
            actif=True,
            distributeur=gerant,
            etat=SituationJournaliere.ETAT_CLOTUREE,
        )
        .order_by("-date_situation")
        .values_list("date_situation", flat=True)
        .first()
    )

    if date_derniere is None:
        return {}

    montants = {}
    for situation in (
        SituationJournaliere.objects
        .filter(
            actif=True,
            distributeur=gerant,
            etat=SituationJournaliere.ETAT_CLOTUREE,
            date_situation=date_derniere,
        )
        .prefetch_related("lignes")
    ):
        for ligne in situation.lignes.all():
            if ligne.quantite_restante > 0:
                montants[ligne.produit_id] = (
                    montants.get(ligne.produit_id, Decimal("0.00"))
                    + calculer_valeur_brute_quantite(
                        ligne.quantite_restante, ligne.prix_unitaire
                    )
                )

    return montants


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
    inclure_cloturees=False,
    situation=None,
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

        .select_related(
            "commande",
        )

        .prefetch_related(
            "lignes__produit__compagnie",
            "commande__lignes__produit__compagnie",
        )

        .order_by(
            "date_distribution",
            "iddistribution",
        )
    )

    if situation is None:
        distributions = distributions.filter(situation__isnull=True)
    else:
        distributions = distributions.filter(situation=situation)

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
        situation.date_situation,
        situation=situation,
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


def dernieres_situations_cloturees_avant(distributeur, date_situation):
    """Retourne tous les versements clos de la derniere date anterieure."""

    situations = SituationJournaliere.objects.filter(
        distributeur=distributeur,
        date_situation__lt=date_situation,
        etat=SituationJournaliere.ETAT_CLOTUREE,
        actif=True,
    )
    derniere_date = (
        situations.order_by("-date_situation")
        .values_list("date_situation", flat=True)
        .first()
    )
    if derniere_date is None:
        return situations.none()
    return situations.filter(date_situation=derniere_date).prefetch_related(
        "lignes__produit__compagnie"
    )


def reliquat_deja_affecte_ce_jour(distributeur, date_situation, situation=None):
    situations = SituationJournaliere.objects.filter(
        distributeur=distributeur,
        date_situation=date_situation,
        actif=True,
    )
    if situation is not None:
        situations = situations.filter(idsituation__lt=situation.pk)
    return situations.exists()


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
    date_situation,
    produits_exclus=None,
    situation=None,
):
    """
    Calcule la valeur brute des quantites restantes
    de la derniere situation cloturee.
    """

    if reliquat_deja_affecte_ce_jour(distributeur, date_situation, situation):
        return Decimal("0.00")

    total = Decimal("0.00")

    produits_exclus = set(
        produits_exclus
        or
        []
    )

    for ligne in (
        ligne
        for precedente in dernieres_situations_cloturees_avant(
            distributeur, date_situation
        )
        for ligne in precedente.lignes.all()
    ):

        if ligne.quantite_restante <= 0:

            continue

        if ligne.produit_id in produits_exclus:

            continue

        total += calculer_valeur_brute_quantite(
            ligne.quantite_restante,
            ligne.prix_unitaire,
        )

    return total


def calculer_total_distribue(
    distributeur,
    date_situation,
    situation=None,
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

    if situation is None:
        distributions = distributions.filter(situation__isnull=True)
    else:
        distributions = distributions.filter(situation=situation)

    if types_distribution:

        distributions = distributions.filter(
            type_distribution__in=types_distribution
        )

    total = Decimal("0.00")

    produits_initiaux_jour = set()

    for distribution in distributions.select_related(
        "commande"
    ).prefetch_related(
        "lignes",
        "commande__lignes",
    ):

        if (
            distribution.type_distribution == Distribution.TYPE_COMMANDE_GERANT
            and
            distribution.commande_id
        ):

            total += (
                distribution.montant_brut
                or Decimal("0.00")
            )

            total += (
                distribution.commande.montant_initial
                or Decimal("0.00")
            )

            for ligne_commande in distribution.commande.lignes.all():

                if ligne_commande.montant_initial > 0:

                    produits_initiaux_jour.add(
                        ligne_commande.produit_id
                    )

            continue

        if (
            distribution.type_distribution
            ==
            Distribution.TYPE_DISTRIBUTEUR
        ):

            total += (
                distribution.montant_total_brut
                or
                distribution.montant_brut
                or
                Decimal("0.00")
            )

            for ligne in distribution.lignes.all():

                if ligne.montant_initial > 0:

                    produits_initiaux_jour.add(
                        ligne.produit_id
                    )

            continue

        total += (
            distribution.montant_brut
            or Decimal("0.00")
        )

    total += calculer_valeur_reliquat_precedent(
        distributeur,
        date_situation,
        produits_exclus=produits_initiaux_jour,
        situation=situation,
    )

    return total


def calculer_total_distribue_net(distributeur, date_situation, situation=None):
    """Valorise les distributions ouvertes et les reliquats une seule fois."""

    return sum(
        (
            donnees["montant_net_distribue"]
            for donnees in construire_donnees_lignes_situation(
                distributeur,
                date_situation,
                situation=situation,
            )
        ),
        Decimal("0.00"),
    )


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
        calculer_total_distribue_net(
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
    distributions=None,
    situation=None,
):
    """
    Construit les lignes metier d'une situation.

    La quantite distribuee du jour inclut une seule fois
    le reliquat de la derniere situation cloturee.
    """

    if distributions is None:

        distributions = recuperer_distributions_journee(
            distributeur,
            date_situation,
            situation=situation,
        )

    distributions = list(
        distributions
    )

    produits = {}

    produits_initiaux_operations = set()

    for distribution in distributions:

        if (
            distribution.type_distribution
            ==
            Distribution.TYPE_COMMANDE_GERANT
            and
            distribution.commande_id
        ):

            for ligne_commande in distribution.commande.lignes.all():

                if ligne_commande.montant_initial > 0:

                    produits_initiaux_operations.add(
                        ligne_commande.produit_id
                    )

        if (
            distribution.type_distribution
            ==
            Distribution.TYPE_DISTRIBUTEUR
        ):

            for ligne_distribution in distribution.lignes.all():

                if ligne_distribution.montant_initial > 0:

                    produits_initiaux_operations.add(
                        ligne_distribution.produit_id
                    )

    if not reliquat_deja_affecte_ce_jour(
        distributeur, date_situation, situation
    ):
        lignes_precedentes = (
            ligne
            for precedente in dernieres_situations_cloturees_avant(
                distributeur, date_situation
            )
            for ligne in precedente.lignes.all()
        )

        for ligne in lignes_precedentes:

            if ligne.quantite_restante <= 0:

                continue

            if ligne.produit_id in produits_initiaux_operations:

                continue

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

            produits[produit_id]["quantite_initiale"] += ligne.quantite_restante
            produits[produit_id]["quantite_distribuee"] += ligne.quantite_restante
            produits[produit_id]["montant_distribue"] += (
                calculer_valeur_brute_quantite(
                    ligne.quantite_restante, ligne.prix_unitaire
                )
            )
            produits[produit_id]["montant_net_distribue"] += (
                calculer_valeur_nette_quantite(
                    ligne.quantite_restante, ligne.prix_unitaire, ligne.taux_remise
                )
            )

    for distribution in distributions:

        if (
            distribution.type_distribution == Distribution.TYPE_COMMANDE_GERANT
            and
            distribution.commande_id
        ):

            for ligne_commande in distribution.commande.lignes.select_related(
                "produit",
                "produit__compagnie",
            ):

                montant_initial = (
                    ligne_commande.montant_initial
                    or Decimal("0.00")
                )

                if montant_initial <= 0:

                    continue

                produit_id = ligne_commande.produit.idproduit
                prix_unitaire = ligne_commande.prix_unitaire
                taux_remise = ligne_commande.taux_remise

                if produit_id not in produits:

                    produits[produit_id] = {
                        "produit": ligne_commande.produit,
                        "prix_unitaire": prix_unitaire,
                        "taux_remise": taux_remise,
                        "taux_distribution": taux_remise,
                        "quantite_initiale": Decimal("0.00"),
                        "quantite_jour": Decimal("0.00"),
                        "quantite_distribuee": Decimal("0.00"),
                        "montant_distribue": Decimal("0.00"),
                        "montant_net_distribue": Decimal("0.00"),
                    }

                quantite_initiale = Decimal("0.00")

                if prix_unitaire > 0:

                    quantite_initiale = (
                        montant_initial
                        /
                        prix_unitaire
                    )

                produits[produit_id]["quantite_initiale"] += (
                    quantite_initiale
                )

                produits[produit_id]["quantite_distribuee"] += (
                    quantite_initiale
                )

                produits[produit_id]["montant_distribue"] += (
                    montant_initial
                )

                produits[produit_id]["montant_net_distribue"] += (
                    ligne_commande.montant_net_initial
                    or Decimal("0.00")
                )

                if produits[produit_id]["taux_distribution"] == Decimal("0.00"):

                    produits[produit_id]["taux_distribution"] = (
                        taux_remise
                    )

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

            if (
                distribution.type_distribution
                ==
                Distribution.TYPE_DISTRIBUTEUR
            ):

                montant_initial = (
                    ligne.montant_initial
                    or Decimal("0.00")
                )

                if montant_initial > 0:

                    quantite_initiale = Decimal("0.00")

                    if ligne.prix_unitaire > 0:

                        quantite_initiale = (
                            montant_initial
                            /
                            ligne.prix_unitaire
                        )

                    produits[produit_id]["quantite_initiale"] += (
                        quantite_initiale
                    )

                    produits[produit_id]["quantite_distribuee"] += (
                        quantite_initiale
                    )

                    produits[produit_id]["montant_distribue"] += (
                        montant_initial
                    )

                    produits[produit_id]["montant_net_distribue"] += (
                        ligne.montant_net_initial
                        or
                        calculer_valeur_nette_quantite(
                            quantite_initiale,
                            ligne.prix_unitaire,
                            ligne.taux_remise,
                        )
                    )

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
                taux_remise=donnees["taux_remise"],
                taux_distribution=donnees["taux_distribution"],
            )
        )

    return lignes


def annoter_lignes_reliquat(
    lignes,
    distributeur,
    date_situation,
    distributions=None,
    situation=None,
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
            distributions,
            situation=situation,
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

        taux_remise = donnees.get(
            "taux_remise",
            getattr(
                ligne,
                "taux_remise",
                getattr(
                    ligne,
                    "taux_distribution",
                    Decimal("0.00")
                )
            )
        )

        ligne.taux_remise = taux_remise

        ligne.taux_distribution = donnees.get(
            "taux_distribution",
            taux_remise
        )

        montant_distribue = donnees.get(
            "montant_distribue"
        )

        if montant_distribue is None:

            montant_distribue = calculer_valeur_brute_quantite(
                ligne.quantite_distribuee,
                ligne.prix_unitaire,
            )

        ligne.montant_distribue = montant_distribue

        montant_net_distribue = donnees.get(
            "montant_net_distribue"
        )

        if montant_net_distribue is None:

            montant_net_distribue = calculer_valeur_nette_quantite(
                ligne.quantite_distribuee,
                ligne.prix_unitaire,
                taux_remise,
            )

        ligne.montant_net_distribue = montant_net_distribue

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
        distributions,
        situation=situation,
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
    situation.montant_surplus = Decimal("0.00")
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

@transaction.atomic
def creer_situation_journaliere(
    distributeur,
    date_situation,
    utilisateur,
    ids_distributions_attendus=None,
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

    distributions = list(recuperer_distributions_journee(
        distributeur, date_situation
    ))

    if not distributions:

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

    ids_distributions = [distribution.pk for distribution in distributions]
    if (
        ids_distributions_attendus is not None
        and set(ids_distributions) != set(ids_distributions_attendus)
    ):
        raise ValueError(
            "Les distributions ont change depuis la recherche. "
            "Relancez la recherche avant d'enregistrer le versement."
        )

    verrouillees = list(Distribution.objects.select_for_update().filter(
        pk__in=ids_distributions,
        situation__isnull=True,
        etat=Distribution.ETAT_OUVERTE,
    ).values_list("pk", flat=True))
    if len(verrouillees) != len(ids_distributions):
        raise ValueError("Les distributions de ce versement ont deja ete prises en compte.")

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
        calculer_total_distribue_net(distributeur, date_situation),
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

    rattachees = Distribution.objects.filter(
        pk__in=ids_distributions,
        situation__isnull=True,
    ).update(situation=situation)
    if rattachees != len(ids_distributions):
        raise ValueError("Les distributions de ce versement ont change.")

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

    Le montant net vendu est justifie par le paiement unique.
    """

    montant_total_distribue_net = Decimal("0.00")
    montant_restant_net = Decimal("0.00")

    for ligne in situation.lignes.all():

        montant_total_distribue_net += calculer_valeur_nette_quantite(
            ligne.quantite_distribuee,
            ligne.prix_unitaire,
            ligne.taux_remise,
        )

        montant_restant_net += calculer_valeur_nette_quantite(
            ligne.quantite_restante,
            ligne.prix_unitaire,
            ligne.taux_remise,
        )

    return ventiler_versement(
        situation.montant_total_verse,
        situation.montant_credit,
        montant_total_distribue_net - montant_restant_net,
    )["montant_manquant"]


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
# SOUMISSION D'UN VERSEMENT GERANT AU DIRECTEUR
# ==========================================================

@transaction.atomic
def soumettre_versement_gerant(
    situation,
    donnees_lignes,
    montant_total_verse,
    coupures,
    utilisateur,
):
    """
    Enregistre le versement saisi par un gerant pour les
    distributions recues du Directeur, sans le rendre effectif.

    Les distributions restent ouvertes et aucun manquant n'est
    cree tant que le Directeur n'a pas valide le versement.
    """

    if utilisateur.profil.role != "GERANT":

        raise ValueError(
            "Seul un gerant peut soumettre ce versement."
        )

    gerant = gerant_du_point_vente(
        utilisateur.profil.point_vente
    )

    if (
        gerant is None
        or
        gerant.pk != situation.distributeur_id
    ):

        raise ValueError(
            "Ce versement ne correspond pas au gerant connecte."
        )

    if situation.etat == SituationJournaliere.ETAT_CLOTUREE:

        raise ValueError(
            "Cette situation est deja cloturee."
        )

    distributions = recuperer_distributions_journee(
        situation.distributeur,
        situation.date_situation,
        situation=situation,
    )

    if not distributions.exists():

        raise ValueError(
            "Aucune distribution ouverte n'est disponible "
            "pour cette date."
        )

    montant_total_verse = Decimal(str(montant_total_verse or "0"))

    if montant_total_verse < 0:
        raise ValueError("Le montant verse ne peut pas etre negatif.")

    situation.montant_total_distribue = calculer_total_distribue(
        situation.distributeur,
        situation.date_situation,
        situation=situation,
    )

    situation.montant_credit = calculer_credit(
        calculer_total_distribue_net(
            situation.distributeur,
            situation.date_situation,
            situation=situation,
        ),
        situation.fond
    )

    montant_total_restant_net = Decimal("0.00")
    montant_total_distribue_net = Decimal("0.00")

    for ligne in situation.lignes.select_related(
        "produit"
    ):

        donnees = donnees_lignes.get(
            str(ligne.idlignesituation)
        )

        if not donnees:

            raise ValueError(
                f"Les donnees du produit "
                f"'{ligne.produit.designation}' "
                f"sont absentes."
            )

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
                f"'{ligne.produit.designation}' "
                f"ne peut pas etre negatif."
            )

        prix = Decimal(
            str(ligne.prix_unitaire)
        )

        if prix <= 0:

            raise ValueError(
                f"Le prix du produit "
                f"'{ligne.produit.designation}' "
                f"est invalide."
            )

        if montant_restant % prix != 0:

            raise ValueError(
                f"Le montant restant du produit "
                f"'{ligne.produit.designation}' "
                f"doit etre un multiple de {prix} FCFA."
            )

        quantite_restante = (
            montant_restant
            /
            prix
        )

        if quantite_restante > ligne.quantite_distribuee:

            raise ValueError(
                f"La quantite restante du produit "
                f"'{ligne.produit.designation}' "
                f"depasse la quantite distribuee."
            )

        montant_total_restant_net += calculer_valeur_nette_quantite(
            quantite_restante,
            ligne.prix_unitaire,
            ligne.taux_remise,
        )

        montant_total_distribue_net += calculer_valeur_nette_quantite(
            ligne.quantite_distribuee,
            ligne.prix_unitaire,
            ligne.taux_remise,
        )

        ligne.quantite_vendue = (
            ligne.quantite_distribuee
            -
            quantite_restante
        )

        ligne.quantite_restante = quantite_restante

        ligne.save(
            update_fields=[
                "quantite_vendue",
                "quantite_restante",
            ]
        )

    repartition = ventiler_versement(
        montant_total_verse,
        situation.montant_credit,
        montant_total_distribue_net - montant_total_restant_net,
    )
    situation.montant_credit_verse = repartition["montant_credit_verse"]
    situation.montant_vente_verse = repartition["montant_vente_verse"]
    situation.montant_total_verse = repartition["montant_total_verse"]
    situation.montant_manquant = repartition["montant_manquant"]
    situation.montant_surplus = repartition["montant_surplus"]

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

    situation.utilisateur = utilisateur
    situation.etat = SituationJournaliere.ETAT_ATTENTE_VALIDATION

    situation.save()

    return situation


# ==========================================================
# VALIDATION / REJET D'UN VERSEMENT GERANT
# ==========================================================

def _verifier_directeur_validation(utilisateur):
    """
    Verifie que l'utilisateur peut traiter un versement
    soumis par un gerant.
    """

    if utilisateur.profil.role != "DIRECTEUR":

        raise ValueError(
            "Seul le Directeur peut traiter ce versement."
        )


def _verifier_situation_gerant_en_attente(situation):
    """
    Controle qu'une situation est bien un versement gerant
    en attente de validation.
    """

    if situation.etat != SituationJournaliere.ETAT_ATTENTE_VALIDATION:

        raise ValueError(
            "Ce versement n'est pas en attente de validation."
        )

    if situation.distributeur.categorie != Distributeur.CATEGORIE_GERANT:

        raise ValueError(
            "Ce versement ne concerne pas un gerant."
        )


@transaction.atomic
def valider_versement_gerant(
    situation,
    utilisateur,
):
    """
    Rend effectif un versement soumis par un gerant.

    Effets definitifs :
        - creation du manquant si necessaire ;
        - cloture des distributions concernees ;
        - passage de la situation a l'etat cloturee.
    """

    _verifier_directeur_validation(
        utilisateur
    )

    _verifier_situation_gerant_en_attente(
        situation
    )

    distributions = recuperer_distributions_journee(
        situation.distributeur,
        situation.date_situation,
        situation=situation,
    )

    if not distributions.exists():

        raise ValueError(
            "Aucune distribution ouverte n'est disponible "
            "pour valider ce versement."
        )

    montant_total_actuel = calculer_total_distribue(
        situation.distributeur,
        situation.date_situation,
        situation=situation,
    )

    if montant_total_actuel != situation.montant_total_distribue:

        raise ValueError(
            "Les distributions ouvertes de cette date ont change "
            "depuis la soumission du versement. Le gerant doit "
            "mettre a jour et resoumettre son versement."
        )

    if situation.montant_manquant > 0:

        manquant = getattr(
            situation,
            "manquant",
            None
        )

        if manquant is None:

            creer_manquant_situation(
                situation,
                situation.montant_manquant,
                utilisateur,
            )

    cloturer_distributions_situation(
        situation
    )

    situation.etat = SituationJournaliere.ETAT_CLOTUREE

    situation.save(
        update_fields=[
            "etat",
            "date_modification",
        ]
    )

    return situation


@transaction.atomic
def rejeter_versement_gerant(
    situation,
    utilisateur,
):
    """
    Refuse un versement soumis par un gerant.

    Les distributions restent ouvertes afin que le gerant
    puisse corriger puis resoumettre le versement.
    """

    _verifier_directeur_validation(
        utilisateur
    )

    _verifier_situation_gerant_en_attente(
        situation
    )

    situation.etat = SituationJournaliere.ETAT_REFUSEE

    situation.save(
        update_fields=[
            "etat",
            "date_modification",
        ]
    )

    return situation


# ==========================================================
# CLOTURE D'UNE SITUATION JOURNALIERE
# ==========================================================

@transaction.atomic
def cloturer_situation(
    situation,
    donnees_lignes,
    montant_total_verse,
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

    montant_total_verse = Decimal(str(montant_total_verse or "0"))

    # ======================================================
    # VERIFICATION DES MONTANTS
    # ======================================================

    if montant_total_verse < 0:
        raise ValueError("Le montant verse ne peut pas etre negatif.")

    situation.montant_total_distribue = calculer_total_distribue(
        situation.distributeur,
        situation.date_situation,
        situation=situation,
    )

    situation.montant_credit = calculer_credit(
        calculer_total_distribue_net(
            situation.distributeur,
            situation.date_situation,
            situation=situation,
        ),
        situation.fond
    )

    # ======================================================
    # MISE A JOUR DES LIGNES
    # ======================================================

    montant_total_restant_net = Decimal("0.00")
    montant_total_distribue_net = Decimal("0.00")

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

        montant_total_restant_net += calculer_valeur_nette_quantite(
            quantite_restante,
            ligne.prix_unitaire,
            ligne.taux_remise,
        )

        montant_total_distribue_net += calculer_valeur_nette_quantite(
            ligne.quantite_distribuee,
            ligne.prix_unitaire,
            ligne.taux_remise,
        )

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

    repartition = ventiler_versement(
        montant_total_verse,
        situation.montant_credit,
        montant_total_distribue_net - montant_total_restant_net,
    )
    situation.montant_credit_verse = repartition["montant_credit_verse"]
    situation.montant_vente_verse = repartition["montant_vente_verse"]
    situation.montant_total_verse = repartition["montant_total_verse"]
    situation.montant_manquant = repartition["montant_manquant"]
    situation.montant_surplus = repartition["montant_surplus"]

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

    if situation.montant_manquant > 0:

        creer_manquant_situation(

            situation,

            situation.montant_manquant,

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
# MODIFICATION D'UNE SITUATION CLOTUREE
# ==========================================================

@transaction.atomic
def modifier_situation_cloturee(
    situation,
    donnees_lignes,
    montant_total_verse,
    coupures,
    utilisateur,
):
    """
    Rejoue la cloture d'une situation recente.
    """

    if not peut_modifier_situation(
        utilisateur,
        situation
    ):

        raise ValueError(
            "Cette situation n'est pas modifiable."
        )

    manquant = getattr(
        situation,
        "manquant",
        None
    )

    if (
        manquant is not None
        and
        manquant.reglements.exists()
    ):

        raise ValueError(
            "Cette situation ne peut pas etre modifiee "
            "car son manquant possede deja des reglements."
        )

    if manquant is not None:

        manquant.delete()

    distributions = recuperer_distributions_journee(
        situation.distributeur,
        situation.date_situation,
        inclure_cloturees=True,
        situation=situation,
    )

    if not distributions.exists():

        raise ValueError(
            "Aucune distribution active n'est rattachee "
            "a cette situation."
        )

    distributions.update(
        etat=Distribution.ETAT_OUVERTE
    )

    situation.etat = SituationJournaliere.ETAT_OUVERTE

    situation.save(
        update_fields=[
            "etat",
            "date_modification",
        ]
    )

    return cloturer_situation(
        situation=situation,
        donnees_lignes=donnees_lignes,
        montant_total_verse=montant_total_verse,
        coupures=coupures,
        utilisateur=utilisateur,
    )


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


def recalculer_reste_manquant(
    manquant
):
    """
    Recalcule le reste a payer depuis les reglements.
    """

    total_regle = (
        manquant.reglements.aggregate(
            total=Sum("montant")
        )["total"]
        or
        Decimal("0.00")
    )

    reste = (
        manquant.montant
        -
        total_regle
    )

    if reste <= 0:

        reste = Decimal("0.00")

        manquant.statut = Manquant.STATUT_SOLDE

    else:

        manquant.statut = Manquant.STATUT_EN_COURS

    manquant.reste_a_payer = reste

    manquant.save(
        update_fields=[
            "reste_a_payer",
            "statut",
            "date_modification",
        ]
    )

    return manquant


@transaction.atomic
def modifier_reglement_manquant(
    reglement,
    date_reglement,
    montant,
    utilisateur,
):
    """
    Modifie un reglement recent de manquant.
    """

    if not peut_modifier_reglement_manquant(
        utilisateur,
        reglement
    ):

        raise ValueError(
            "Ce reglement n'est pas modifiable."
        )

    montant = Decimal(
        str(montant or "0")
    )

    if montant <= 0:

        raise ValueError(
            "Le montant du reglement doit etre superieur a zero."
        )

    manquant = reglement.manquant

    total_autres_reglements = (
        manquant.reglements
        .exclude(
            pk=reglement.pk
        )
        .aggregate(
            total=Sum("montant")
        )["total"]
        or
        Decimal("0.00")
    )

    if total_autres_reglements + montant > manquant.montant:

        raise ValueError(
            "Le total des reglements depasse le montant du manquant."
        )

    reglement.date_reglement = date_reglement
    reglement.montant = montant

    reglement.save(
        update_fields=[
            "date_reglement",
            "montant",
        ]
    )

    recalculer_reste_manquant(
        manquant
    )

    return reglement
