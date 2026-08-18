"""
==========================================================
Projet : EMG MANAGE

Module : Tableau de bord

Description :
Agregations de lecture pour le tableau de bord.

==========================================================
"""

from collections import defaultdict
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from commandes.models import (
    Commande,
    LigneCommande,
)
from comptes.utils import (
    est_directeur,
    est_gerant,
)
from distributions.models import (
    Distribution,
    LigneDistribution,
)
from objectif.models import Objectif
from referentiel.models import (
    Distributeur,
    Produit,
)
from situations.models import (
    LigneSituationJournaliere,
    Manquant,
    SituationJournaliere,
)
from stocks.models import (
    Stock,
    TYPE_NORMAL,
)


def _date_iso_ou_none(valeur):
    """
    Convertit une date ISO issue des filtres GET.
    """

    if not valeur:

        return None

    if hasattr(
        valeur,
        "year"
    ):

        return valeur

    try:

        return date.fromisoformat(
            str(valeur)
        )

    except ValueError:

        return None


def periode_dashboard(date_debut=None, date_fin=None):
    """
    Retourne la periode filtree du tableau de bord.
    Par defaut, elle couvre le mois courant.
    """

    aujourd_hui = timezone.localdate()

    debut_defaut = aujourd_hui.replace(
        day=1
    )

    fin_defaut = aujourd_hui.replace(
        day=monthrange(
            aujourd_hui.year,
            aujourd_hui.month,
        )[1]
    )

    debut = (
        _date_iso_ou_none(date_debut)
        or debut_defaut
    )

    fin = (
        _date_iso_ou_none(date_fin)
        or fin_defaut
    )

    if debut > fin:

        debut, fin = fin, debut

    return {
        "mois": debut.month,
        "annee": debut.year,
        "date_debut": debut,
        "date_fin": fin,
        "date_debut_iso": debut.isoformat(),
        "date_fin_iso": fin.isoformat(),
        "libelle": (
            f"du {debut.strftime('%d/%m/%Y')} "
            f"au {fin.strftime('%d/%m/%Y')}"
        ),
    }


def periode_courante():
    """
    Retourne le mois et l'annee courants.
    """

    return periode_dashboard()


def _filtrer_intervalle(queryset, champ_date, date_debut, date_fin):
    """
    Applique un intervalle de dates inclusif a un queryset.
    """

    return queryset.filter(
        **{
            f"{champ_date}__gte": date_debut,
            f"{champ_date}__lte": date_fin,
        }
    )


def _decimal(valeur):
    """
    Retourne une valeur Decimal non nulle.
    """

    return valeur or Decimal("0.00")


def _produits_actifs():
    """
    Retourne les produits actifs ordonnes par compagnie.
    """

    return list(
        Produit.objects
        .filter(
            actif=True
        )
        .select_related(
            "compagnie"
        )
        .order_by(
            "compagnie__designation",
            "designation",
        )
    )


def _totaux_lignes(lignes, champs):
    """
    Calcule les totaux d'une liste de lignes dictionnaires.
    """

    return {
        champ: sum(
            (
                _decimal(
                    ligne.get(champ)
                )
                for ligne in lignes
            ),
            Decimal("0.00")
        )
        for champ in champs
    }


def _grouper_par_compagnie(lignes, champs_totaux=None):
    """
    Regroupe une liste de lignes par compagnie.
    """

    groupes = []

    compagnies = []

    for ligne in lignes:

        compagnie = ligne["produit"].compagnie

        if compagnie not in compagnies:

            compagnies.append(
                compagnie
            )

    for compagnie in compagnies:

        lignes_compagnie = [
            ligne
            for ligne in lignes
            if ligne["produit"].compagnie == compagnie
        ]

        groupe = {
            "compagnie": compagnie,
            "lignes": lignes_compagnie,
        }

        if champs_totaux:

            groupe["totaux"] = _totaux_lignes(
                lignes_compagnie,
                champs_totaux,
            )

        groupes.append(
            groupe
        )

    return groupes


def _stock_normal_par_produit(point_vente):
    """
    Retourne la quantite de stock normal par produit.
    """

    stocks = (
        Stock.objects
        .filter(
            actif=True,
            point_vente=point_vente,
            type_stock=TYPE_NORMAL,
        )
        .values(
            "produit_id"
        )
        .annotate(
            total=Sum("quantite")
        )
    )

    return {
        stock["produit_id"]: _decimal(stock["total"])
        for stock in stocks
    }


def _taux_derniere_commande_par_produit(point_vente, type_commande):
    """
    Retourne le taux de la derniere commande normale validee par produit.
    """

    lignes = (
        LigneCommande.objects
        .filter(
            commande__actif=True,
            commande__point_vente=point_vente,
            commande__type_commande=type_commande,
            commande__categorie_commande=Commande.CATEGORIE_NORMALE,
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


def _valoriser_quantite(produit, quantite, taux_par_produit):
    """
    Valorise une quantite avec le prix produit et le dernier taux connu.
    """

    quantite = _decimal(
        quantite
    )

    montant_brut = produit.prix * quantite

    taux = _decimal(
        taux_par_produit.get(
            produit.pk
        )
    )

    montant_remise = (
        montant_brut
        *
        taux
        /
        Decimal("100")
    )

    return {
        "montant_brut": montant_brut,
        "montant_net": (
            montant_brut
            -
            montant_remise
        ),
    }


def objectifs_mois(point_vente, mois, annee):
    """
    Objectifs du point de vente pour le mois courant.
    """

    objectifs = list(
        Objectif.objects
        .filter(
            actif=True,
            point_vente=point_vente,
            mois=mois,
            annee=annee,
        )
        .select_related(
            "compagnie",
            "point_vente",
        )
        .prefetch_related(
            "lignes__produit"
        )
        .order_by(
            "compagnie__designation",
            "designation",
        )
    )

    for objectif in objectifs:

        taux = objectif.taux_realise or Decimal("0.00")

        if taux < 0:

            taux = Decimal("0.00")

        if taux > 100:

            taux = Decimal("100.00")

        objectif.taux_graphique = taux

        objectif.taux_graphique_css = int(
            taux
        )

    total_cible = sum(
        (
            objectif.montant_cible
            for objectif in objectifs
        ),
        Decimal("0.00")
    )

    total_realise = sum(
        (
            objectif.montant_realise
            for objectif in objectifs
        ),
        Decimal("0.00")
    )

    taux_global = Decimal("0.00")

    if total_cible > 0:

        taux_global = round(
            (
                total_realise
                * Decimal("100")
            )
            /
            total_cible,
            2
        )

    return {
        "objectifs": objectifs,
        "total_cible": total_cible,
        "total_realise": total_realise,
        "taux_global": taux_global,
        "taux_global_graphique": min(
            taux_global,
            Decimal("100.00")
        ),
        "taux_global_graphique_css": int(
            min(
                taux_global,
                Decimal("100.00")
            )
        ),
    }


def synthese_distributions(
    point_vente,
    date_debut,
    date_fin,
    types_distribution,
    type_commande_reference,
):
    """
    Synthese des distributions par produit.
    """

    produits = _produits_actifs()

    stock_map = _stock_normal_par_produit(
        point_vente
    )

    taux_map = _taux_derniere_commande_par_produit(
        point_vente,
        type_commande_reference,
    )

    lignes_distribution = _filtrer_intervalle(
        LigneDistribution.objects
        .filter(
            distribution__actif=True,
            distribution__point_vente_source=point_vente,
            distribution__type_distribution__in=types_distribution,
        ),
        "distribution__date_distribution",
        date_debut,
        date_fin,
    )
    lignes_distribution = (
        lignes_distribution
        .values(
            "produit_id"
        )
        .annotate(
            quantite=Sum("quantite"),
        )
    )

    distribution_map = {
        ligne["produit_id"]: ligne
        for ligne in lignes_distribution
    }

    lignes = []

    for produit in produits:

        distribution = distribution_map.get(
            produit.pk,
            {}
        )

        stock = stock_map.get(
            produit.pk,
            Decimal("0.00")
        )

        quantite = _decimal(
            distribution.get("quantite")
        )

        stock_valorise = _valoriser_quantite(
            produit,
            stock,
            taux_map,
        )

        distribution_valorisee = _valoriser_quantite(
            produit,
            quantite,
            taux_map,
        )

        lignes.append({
            "produit": produit,
            "stock": stock,
            "stock_montant_brut": stock_valorise[
                "montant_brut"
            ],
            "stock_montant_net": stock_valorise[
                "montant_net"
            ],
            "quantite": quantite,
            "montant_brut": distribution_valorisee[
                "montant_brut"
            ],
            "montant_net": distribution_valorisee[
                "montant_net"
            ],
        })

    champs_totaux = [
        "stock",
        "stock_montant_brut",
        "stock_montant_net",
        "quantite",
        "montant_brut",
        "montant_net",
    ]

    return {
        "groupes": _grouper_par_compagnie(
            lignes,
            champs_totaux,
        ),
        "totaux": _totaux_lignes(
            lignes,
            champs_totaux,
        ),
    }


def synthese_distributions_par_destinataire(
    point_vente,
    date_debut,
    date_fin,
):
    """
    Detail des distributions terrain par distributeur.
    Les clients directs sont volontairement exclus.
    """

    lignes_queryset = _filtrer_intervalle(
        LigneDistribution.objects
        .filter(
            distribution__actif=True,
            distribution__point_vente_source=point_vente,
            distribution__type_distribution=Distribution.TYPE_DISTRIBUTEUR,
        )
        .select_related(
            "distribution",
            "distribution__distributeur",
            "produit",
            "produit__compagnie",
        )
        .order_by(
            "distribution__distributeur__nom",
            "distribution__distributeur__prenom",
            "produit__compagnie__designation",
            "produit__designation",
        ),
        "distribution__date_distribution",
        date_debut,
        date_fin,
    )

    donnees = {}

    for ligne in lignes_queryset:

        distributeur = ligne.distribution.distributeur

        if distributeur.pk not in donnees:

            donnees[distributeur.pk] = {
                "distributeur": distributeur,
                "produits": {},
            }

        produits = donnees[distributeur.pk]["produits"]

        if ligne.produit_id not in produits:

            produits[ligne.produit_id] = {
                "produit": ligne.produit,
                "quantite": Decimal("0.00"),
                "montant_brut": Decimal("0.00"),
                "montant_net": Decimal("0.00"),
            }

        produits[ligne.produit_id]["quantite"] += ligne.quantite
        produits[ligne.produit_id]["montant_brut"] += ligne.montant
        produits[ligne.produit_id]["montant_net"] += ligne.montant_net

    champs_totaux = [
        "quantite",
        "montant_brut",
        "montant_net",
    ]

    destinataires = []

    toutes_lignes = []

    for donnees_distributeur in donnees.values():

        lignes = list(
            donnees_distributeur["produits"].values()
        )

        toutes_lignes.extend(
            lignes
        )

        destinataires.append({
            "distributeur": donnees_distributeur[
                "distributeur"
            ],
            "groupes": _grouper_par_compagnie(
                lignes,
                champs_totaux,
            ),
            "totaux": _totaux_lignes(
                lignes,
                champs_totaux,
            ),
        })

    return {
        "destinataires": destinataires,
        "totaux": _totaux_lignes(
            toutes_lignes,
            champs_totaux,
        ),
    }


def gerants_disponibles():
    """
    Liste des gerants pour le tableau Directeur.
    """

    return list(
        Distributeur.objects
        .filter(
            actif=True,
            categorie=Distributeur.CATEGORIE_GERANT,
        )
        .select_related(
            "point_vente"
        )
        .order_by(
            "point_vente__designation",
            "nom",
            "prenom",
        )
    )


def personnes_directeur(point_vente):
    """
    Liste les gerants et les distributeurs directs du Directeur.
    """

    return list(
        Distributeur.objects
        .filter(
            actif=True,
        )
        .filter(
            Q(
                categorie=Distributeur.CATEGORIE_GERANT,
            )
            |
            Q(
                categorie=Distributeur.CATEGORIE_DISTRIBUTEUR,
                point_vente=point_vente,
            )
        )
        .select_related(
            "point_vente"
        )
        .order_by(
            "categorie",
            "point_vente__designation",
            "nom",
            "prenom",
        )
    )


def distributeurs_disponibles(point_vente):
    """
    Liste des distributeurs du point de vente du gerant.
    """

    return list(
        Distributeur.objects
        .filter(
            actif=True,
            point_vente=point_vente,
            categorie=Distributeur.CATEGORIE_DISTRIBUTEUR,
        )
        .order_by(
            "nom",
            "prenom",
        )
    )


def _selectionner_personne(personnes, personne_id):
    """
    Selectionne une personne depuis la liste.
    """

    if not personnes:

        return None

    if personne_id:

        for personne in personnes:

            if str(personne.pk) == str(personne_id):

                return personne

    return personnes[0]


def _montants_reference_directeur(
    personne,
    point_vente,
    date_debut,
    date_fin,
):
    """
    Retourne le montant reference d'une personne suivie
    par le Directeur selon sa categorie.
    """

    if personne is None:

        return {}

    if personne.categorie == Distributeur.CATEGORIE_GERANT:

        return _montants_commandes_gerant(
            personne,
            date_debut,
            date_fin,
        )

    if personne.categorie == Distributeur.CATEGORIE_DISTRIBUTEUR:

        return _montants_distribues_distributeur(
            personne,
            point_vente,
            date_debut,
            date_fin,
        )

    return {}


def _montants_commandes_gerant(personne, date_debut, date_fin):
    """
    Montants nets commandes par produit pour un gerant.
    """

    if personne is None:

        return {}

    lignes = _filtrer_intervalle(
        LigneCommande.objects
        .filter(
            commande__actif=True,
            commande__point_vente=personne.point_vente,
            commande__categorie_commande=Commande.CATEGORIE_NORMALE,
        ),
        "commande__date_commande",
        date_debut,
        date_fin,
    )
    lignes = (
        lignes
        .values(
            "produit_id"
        )
        .annotate(
            total=Sum("montant_net")
        )
    )

    return {
        ligne["produit_id"]: _decimal(ligne["total"])
        for ligne in lignes
    }


def _montants_distribues_distributeur(
    personne,
    point_vente,
    date_debut,
    date_fin,
):
    """
    Montants nets distribues par produit a un distributeur.
    """

    if personne is None:

        return {}

    lignes = _filtrer_intervalle(
        LigneDistribution.objects
        .filter(
            distribution__actif=True,
            distribution__point_vente_source=point_vente,
            distribution__distributeur=personne,
            distribution__type_distribution=Distribution.TYPE_DISTRIBUTEUR,
        ),
        "distribution__date_distribution",
        date_debut,
        date_fin,
    )
    lignes = (
        lignes
        .values(
            "produit_id"
        )
        .annotate(
            total=Sum("montant_net")
        )
    )

    return {
        ligne["produit_id"]: _decimal(ligne["total"])
        for ligne in lignes
    }


def _montants_verses_par_produit(personne, date_debut, date_fin):
    """
    Montants vendus/verses issus des lignes de situation.
    """

    montants = defaultdict(
        lambda: Decimal("0.00")
    )

    if personne is None:

        return montants

    lignes = _filtrer_intervalle(
        LigneSituationJournaliere.objects
        .filter(
            situation__actif=True,
            situation__etat=SituationJournaliere.ETAT_CLOTUREE,
            situation__distributeur=personne,
        ),
        "situation__date_situation",
        date_debut,
        date_fin,
    )
    lignes = (
        lignes
        .select_related(
            "produit",
            "produit__compagnie",
        )
    )

    for ligne in lignes:

        montants[ligne.produit_id] += (
            ligne.quantite_vendue
            *
            ligne.prix_unitaire
        )

    return montants


def synthese_situations_personne(
    personne,
    date_debut,
    date_fin,
    montant_reference_map,
):
    """
    Tableau produits pour les situations d'une personne.
    """

    montant_verse_map = _montants_verses_par_produit(
        personne,
        date_debut,
        date_fin,
    )

    produit_ids = set(
        montant_reference_map.keys()
    ) | set(
        montant_verse_map.keys()
    )

    produits = (
        Produit.objects
        .filter(
            pk__in=produit_ids
        )
        .select_related(
            "compagnie"
        )
        .order_by(
            "compagnie__designation",
            "designation",
        )
    )

    lignes = []

    for produit in produits:

        montant_reference = _decimal(
            montant_reference_map.get(
                produit.pk
            )
        )

        montant_verse = _decimal(
            montant_verse_map.get(
                produit.pk
            )
        )

        lignes.append({
            "produit": produit,
            "montant_reference": montant_reference,
            "montant_verse": montant_verse,
            "ecart": (
                montant_reference
                -
                montant_verse
            ),
        })

    champs_totaux = [
        "montant_reference",
        "montant_verse",
        "ecart",
    ]

    return {
        "groupes": _grouper_par_compagnie(
            lignes,
            champs_totaux,
        ),
        "totaux": _totaux_lignes(
            lignes,
            champs_totaux,
        ),
    }


def tableau_manquants(personne, date_debut, date_fin):
    """
    Manquants et paiements d'une personne pour la periode.
    """

    if personne is None:

        return {
            "lignes": [],
            "totaux": {
                "montant": Decimal("0.00"),
                "paiements": Decimal("0.00"),
                "reste": Decimal("0.00"),
            },
        }

    manquants = _filtrer_intervalle(
        Manquant.objects
        .filter(
            situation__actif=True,
            situation__distributeur=personne,
        ),
        "situation__date_situation",
        date_debut,
        date_fin,
    )
    manquants = (
        manquants
        .select_related(
            "situation",
            "distributeur",
        )
        .prefetch_related(
            "reglements"
        )
        .order_by(
            "-situation__date_situation",
            "-idmanquant",
        )
    )

    lignes = []

    for manquant in manquants:

        total_paiements = sum(
            (
                reglement.montant
                for reglement in manquant.reglements.all()
            ),
            Decimal("0.00")
        )

        lignes.append({
            "manquant": manquant,
            "total_paiements": total_paiements,
            "reste_a_payer": manquant.reste_a_payer,
        })

    return {
        "lignes": lignes,
        "totaux": {
            "montant": sum(
                (
                    ligne["manquant"].montant
                    for ligne in lignes
                ),
                Decimal("0.00")
            ),
            "paiements": sum(
                (
                    ligne["total_paiements"]
                    for ligne in lignes
                ),
                Decimal("0.00")
            ),
            "reste": sum(
                (
                    ligne["reste_a_payer"]
                    for ligne in lignes
                ),
                Decimal("0.00")
            ),
        },
    }


def synthese_ventes_directes(
    point_vente,
    date_debut,
    date_fin,
    type_commande_reference,
):
    """
    Somme des ventes directes par produit.
    """

    lignes_distribution = _filtrer_intervalle(
        LigneDistribution.objects
        .filter(
            distribution__actif=True,
            distribution__point_vente_source=point_vente,
            distribution__type_distribution=Distribution.TYPE_CLIENT_DIRECT,
        ),
        "distribution__date_distribution",
        date_debut,
        date_fin,
    )
    lignes_distribution = (
        lignes_distribution
        .values(
            "produit_id"
        )
        .annotate(
            quantite=Sum("quantite"),
        )
    )

    distribution_map = {
        ligne["produit_id"]: ligne
        for ligne in lignes_distribution
    }

    produits = (
        Produit.objects
        .filter(
            pk__in=distribution_map.keys()
        )
        .select_related(
            "compagnie"
        )
        .order_by(
            "compagnie__designation",
            "designation",
        )
    )

    lignes = []

    taux_map = _taux_derniere_commande_par_produit(
        point_vente,
        type_commande_reference,
    )

    for produit in produits:

        distribution = distribution_map.get(
            produit.pk,
            {}
        )

        quantite = _decimal(
            distribution.get("quantite")
        )

        vente_valorisee = _valoriser_quantite(
            produit,
            quantite,
            taux_map,
        )

        lignes.append({
            "produit": produit,
            "quantite": quantite,
            "montant_brut": vente_valorisee[
                "montant_brut"
            ],
            "montant_net": vente_valorisee[
                "montant_net"
            ],
        })

    champs_totaux = [
        "quantite",
        "montant_brut",
        "montant_net",
    ]

    return {
        "groupes": _grouper_par_compagnie(
            lignes,
            champs_totaux,
        ),
        "totaux": _totaux_lignes(
            lignes,
            champs_totaux,
        ),
    }


def donnees_dashboard(
    utilisateur,
    personne_id=None,
    date_debut=None,
    date_fin=None,
):
    """
    Construit le contexte metier du tableau de bord.
    """

    periode = periode_dashboard(
        date_debut,
        date_fin,
    )

    mois = periode["mois"]

    annee = periode["annee"]

    date_debut = periode["date_debut"]

    date_fin = periode["date_fin"]

    profil = utilisateur.profil

    point_vente = profil.point_vente

    contexte = {
        "profil": profil,
        "periode": periode,
        "est_directeur": est_directeur(utilisateur),
        "est_gerant": est_gerant(utilisateur),
    }

    if point_vente is None:

        return contexte

    if est_directeur(utilisateur):

        personnes = personnes_directeur(
            point_vente
        )

        personne_selectionnee = _selectionner_personne(
            personnes,
            personne_id,
        )

        montant_reference_map = _montants_reference_directeur(
            personne_selectionnee,
            point_vente,
            date_debut,
            date_fin,
        )

        distribution_synthese = synthese_distributions(
            point_vente,
            date_debut,
            date_fin,
            [
                Distribution.TYPE_COMMANDE_GERANT,
            ],
            Commande.TYPE_DIRECTEUR,
        )

        distribution_destinataires_synthese = (
            synthese_distributions_par_destinataire(
                point_vente,
                date_debut,
                date_fin,
            )
        )

        situation_synthese = synthese_situations_personne(
            personne_selectionnee,
            date_debut,
            date_fin,
            montant_reference_map,
        )

        manquants_synthese = tableau_manquants(
            personne_selectionnee,
            date_debut,
            date_fin,
        )

        ventes_directes_synthese = synthese_ventes_directes(
            point_vente,
            date_debut,
            date_fin,
            Commande.TYPE_DIRECTEUR,
        )

        contexte.update({
            "objectifs": objectifs_mois(
                point_vente,
                mois,
                annee,
            ),
            "distribution_groupes": distribution_synthese[
                "groupes"
            ],
            "distribution_totaux": distribution_synthese[
                "totaux"
            ],
            "distribution_destinataires": (
                distribution_destinataires_synthese[
                    "destinataires"
                ]
            ),
            "distribution_destinataires_totaux": (
                distribution_destinataires_synthese[
                    "totaux"
                ]
            ),
            "personnes": personnes,
            "personne_selectionnee": personne_selectionnee,
            "personne_label": "Gérant / Distributeur",
            "montant_reference_label": "Montant net à justifier",
            "situation_groupes": situation_synthese[
                "groupes"
            ],
            "situation_totaux": situation_synthese[
                "totaux"
            ],
            "manquants": manquants_synthese[
                "lignes"
            ],
            "manquants_totaux": manquants_synthese[
                "totaux"
            ],
            "ventes_directes_groupes": ventes_directes_synthese[
                "groupes"
            ],
            "ventes_directes_totaux": ventes_directes_synthese[
                "totaux"
            ],
        })

    elif est_gerant(utilisateur):

        personnes = distributeurs_disponibles(
            point_vente
        )

        personne_selectionnee = _selectionner_personne(
            personnes,
            personne_id,
        )

        montant_reference_map = _montants_distribues_distributeur(
            personne_selectionnee,
            point_vente,
            date_debut,
            date_fin,
        )

        distribution_synthese = synthese_distributions(
            point_vente,
            date_debut,
            date_fin,
            [
                Distribution.TYPE_DISTRIBUTEUR,
            ],
            Commande.TYPE_GERANT,
        )

        distribution_destinataires_synthese = (
            synthese_distributions_par_destinataire(
                point_vente,
                date_debut,
                date_fin,
            )
        )

        situation_synthese = synthese_situations_personne(
            personne_selectionnee,
            date_debut,
            date_fin,
            montant_reference_map,
        )

        manquants_synthese = tableau_manquants(
            personne_selectionnee,
            date_debut,
            date_fin,
        )

        ventes_directes_synthese = synthese_ventes_directes(
            point_vente,
            date_debut,
            date_fin,
            Commande.TYPE_GERANT,
        )

        contexte.update({
            "distribution_groupes": distribution_synthese[
                "groupes"
            ],
            "distribution_totaux": distribution_synthese[
                "totaux"
            ],
            "distribution_destinataires": (
                distribution_destinataires_synthese[
                    "destinataires"
                ]
            ),
            "distribution_destinataires_totaux": (
                distribution_destinataires_synthese[
                    "totaux"
                ]
            ),
            "personnes": personnes,
            "personne_selectionnee": personne_selectionnee,
            "personne_label": "Distributeur",
            "montant_reference_label": "Montant net distribué",
            "situation_groupes": situation_synthese[
                "groupes"
            ],
            "situation_totaux": situation_synthese[
                "totaux"
            ],
            "manquants": manquants_synthese[
                "lignes"
            ],
            "manquants_totaux": manquants_synthese[
                "totaux"
            ],
            "ventes_directes_groupes": ventes_directes_synthese[
                "groupes"
            ],
            "ventes_directes_totaux": ventes_directes_synthese[
                "totaux"
            ],
        })

    return contexte
