import json
from urllib.parse import urlsplit

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.urls import reverse

from referentiel.models import Distributeur

from .models import CorrectionApercu, NotificationCorrection, ProfilUtilisateur
from .permissions import date_dans_delai_modification, est_directeur


def gerant_du_point_vente(point_vente):
    return Distributeur.objects.filter(
        point_vente=point_vente,
        categorie=Distributeur.CATEGORIE_GERANT,
        actif=True,
    ).order_by("pk").first()


def retour_apercu(request, onglet):
    candidat = request.POST.get("next") or request.GET.get("next") or ""
    chemin = urlsplit(candidat)
    if not chemin.netloc and chemin.path == reverse("apercu_directeur"):
        return candidat
    return f"{reverse('apercu_directeur')}#{onglet}"


def commande_corrigeable(utilisateur, commande):
    from commandes.models import Commande

    return bool(
        est_directeur(utilisateur)
        and commande.actif
        and commande.type_commande == Commande.TYPE_GERANT
        and commande.categorie_commande == Commande.CATEGORIE_NORMALE
        and commande.etat in (Commande.EN_ATTENTE, Commande.REFUSEE)
        and date_dans_delai_modification(commande.date_commande)
        and gerant_du_point_vente(commande.point_vente)
        and not commande.distributions.exists()
    )


def distribution_corrigeable(utilisateur, distribution):
    from distributions.models import Distribution
    from distributions.permissions import peut_modifier_distribution
    from situations.models import SituationJournaliere

    autorisee = bool(
        est_directeur(utilisateur)
        and gerant_du_point_vente(distribution.point_vente_source)
        and distribution.type_distribution in (
            Distribution.TYPE_DISTRIBUTEUR, Distribution.TYPE_CLIENT_DIRECT
        )
        and peut_modifier_distribution(utilisateur, distribution)
        and (
            distribution.type_distribution == Distribution.TYPE_CLIENT_DIRECT
            or distribution.situation_id is None
        )
    )
    if not autorisee:
        return False
    if any(
        not ligne.produit.actif or ligne.produit.prix != ligne.prix_unitaire
        for ligne in distribution.lignes.select_related("produit")
    ):
        return False
    if distribution.type_distribution == Distribution.TYPE_CLIENT_DIRECT:
        situations = SituationJournaliere.objects.filter(
            distributeur=distribution.distributeur,
            date_situation=distribution.date_distribution,
            actif=True,
        )
        return not any(
            situation.coupures != "Situation automatique - vente directe"
            or getattr(situation, "manquant", None) is not None
            for situation in situations
        )
    return True


def situation_corrigeable(utilisateur, situation):
    from distributions.models import Distribution
    from situations.models import SituationJournaliere
    from situations.permissions import peut_modifier_situation

    if not (
        est_directeur(utilisateur)
        and gerant_du_point_vente(situation.point_vente)
        and situation.etat == SituationJournaliere.ETAT_CLOTUREE
        and situation.distributeur.categorie == Distributeur.CATEGORIE_DISTRIBUTEUR
        and peut_modifier_situation(utilisateur, situation)
        and situation.distributions.filter(actif=True).exists()
    ):
        return False

    manquant = getattr(situation, "manquant", None)
    if manquant is not None and manquant.reglements.exists():
        return False

    # A later operation can already have consumed the remaining amount.
    return not (
        SituationJournaliere.objects.filter(
            distributeur=situation.distributeur,
            actif=True,
        ).filter(
            Q(date_situation__gt=situation.date_situation)
            | Q(date_situation=situation.date_situation, pk__gt=situation.pk)
        ).exists()
        or Distribution.objects.filter(
            distributeur=situation.distributeur,
            actif=True,
            date_distribution__gt=situation.date_situation,
        ).exists()
        or Distribution.objects.filter(
            distributeur=situation.distributeur,
            actif=True,
            date_distribution=situation.date_situation,
            date_creation__gt=situation.date_creation,
        ).exclude(situation=situation).exists()
    )


def reglement_corrigeable(utilisateur, reglement):
    from situations.permissions import peut_modifier_reglement_manquant

    return bool(
        est_directeur(utilisateur)
        and reglement.manquant.situation.actif
        and gerant_du_point_vente(reglement.manquant.situation.point_vente)
        and peut_modifier_reglement_manquant(utilisateur, reglement)
    )


def instantane(operation):
    def champs(objet):
        return {
            champ.name: getattr(objet, champ.attname)
            for champ in objet._meta.concrete_fields
        }

    valeurs = {"operation": champs(operation)}
    if hasattr(operation, "lignes"):
        valeurs["lignes"] = [
            champs(ligne) for ligne in operation.lignes.order_by("pk")
        ]
    if operation._meta.model_name == "situationjournaliere":
        manquant = getattr(operation, "manquant", None)
        valeurs["manquant"] = champs(manquant) if manquant else None
    if hasattr(operation, "manquant") and operation._meta.model_name == "reglementmanquant":
        valeurs["manquant"] = champs(operation.manquant)
    return json.loads(json.dumps(valeurs, cls=DjangoJSONEncoder))


def enregistrer_correction(
    *, utilisateur, gerant, operation, type_operation, motif, avant, lien
):
    correction = CorrectionApercu.objects.create(
        operation_type=type_operation,
        operation_numero=operation.numero,
        gerant=gerant,
        directeur=utilisateur,
        motif=motif.strip(),
        anciennes_valeurs=avant,
        nouvelles_valeurs=instantane(operation),
        lien_operation=lien,
    )
    destinataires = ProfilUtilisateur.objects.filter(
        role="GERANT", point_vente=gerant.point_vente, actif=True,
        utilisateur__is_active=True,
    ).values_list("utilisateur_id", flat=True)
    NotificationCorrection.objects.bulk_create([
        NotificationCorrection(correction=correction, destinataire_id=identifiant)
        for identifiant in destinataires
    ])
    return correction
