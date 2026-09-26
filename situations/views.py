"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Vues du module Situations.

==========================================================
"""
from decimal import Decimal
from calendar import monthrange
from datetime import date
from types import SimpleNamespace

from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from referentiel.models import Distributeur

from .forms import (
    SelectionSituationForm,
    SituationGerantDateForm,
    VersementGerantSelectionForm,
    ReglementManquantForm,
)

from .selectors import (
    distributions_du_jour,
    situation_existante,
    situations_visibles,
    manquants_visibles,
    reglements_manquants_visibles,
    paginer,
)

from .services import (
    annoter_lignes_reliquat,
    calculer_valeur_nette_quantite,
    calculer_total_distribue,
    calculer_total_distribue_net,
    calculer_situation_gerant,
    construire_lignes_affichage_situation,
    creer_situation_journaliere,
    creer_lignes_situation,
    gerant_du_point_vente,
    cloturer_situation,
    modifier_reglement_manquant,
    modifier_situation_cloturee,
    preparer_affichage_situations_gerant,
    regler_manquant,
    soumettre_versement_gerant,
    valider_versement_gerant,
    rejeter_versement_gerant,
)

from .models import (
    SituationJournaliere,
    SituationGerant,
    Manquant,
    ReglementManquant,
)

from .permissions import (
    peut_modifier_reglement_manquant,
    peut_modifier_situation,
)

from itertools import groupby

from .calculs import (
    calculer_credit,
)


# ==========================================================
# OUTILS INTERNES
# ==========================================================

def _distributeur_autorise(
    utilisateur,
    distributeur,
):
    """
    Verifie que le distributeur d'une situation appartient
    au perimetre autorise par le formulaire de selection.
    """

    form = SelectionSituationForm(
        utilisateur=utilisateur
    )

    return (
        form.fields["distributeur"]
        .queryset
        .filter(pk=distributeur.pk)
        .exists()
    )


def _situation_depuis_post(request):
    """
    Recupere une situation depuis idsituation lorsque
    l'identifiant est fourni.
    """

    idsituation = request.POST.get(
        "idsituation"
    )

    if not idsituation:
        return None

    try:

        idsituation = int(idsituation)

    except (TypeError, ValueError):

        raise ValueError(
            "La situation indiquee est invalide."
        )

    situation = (
        SituationJournaliere.objects
        .select_related(
            "distributeur",
            "point_vente",
        )
        .filter(
            pk=idsituation,
            actif=True,
        )
        .first()
    )

    if situation is None:

        raise ValueError(
            "La situation indiquee est introuvable."
        )

    if not _distributeur_autorise(
        request.user,
        situation.distributeur,
    ):

        raise ValueError(
            "Vous n'etes pas autorise a cloturer "
            "cette situation."
        )

    return situation


def _contexte_cloture_depuis_post(request):
    """
    Determine le distributeur, la date et la situation
    a cloturer.

    Si idsituation est present, les informations fiables
    viennent de la base. Sinon, on valide la selection
    postee pour permettre la creation a la cloture.
    """

    situation = _situation_depuis_post(
        request
    )

    if situation is not None:

        return (
            situation.distributeur,
            situation.date_situation,
            situation,
        )

    form_selection = SelectionSituationForm(
        request.POST,
        utilisateur=request.user
    )

    if not form_selection.is_valid():

        raise ValueError(
            "Les informations de selection "
            "sont invalides."
        )

    return (
        form_selection.cleaned_data["distributeur"],
        form_selection.cleaned_data["date_situation"],
        None,
    )


def _situation_affichage_temporaire(
    distributeur,
    date_situation,
    distributions,
):
    """
    Construit les informations affichees au-dessus du
    tableau lorsqu'aucune situation n'existe encore en base.
    """

    montant_total_distribue = calculer_total_distribue(
        distributeur,
        date_situation
    )
    montant_total_distribue_net = calculer_total_distribue_net(
        distributeur,
        date_situation,
    )

    point_vente = None

    for distribution in distributions:

        if point_vente is None:

            point_vente = (
                distribution.point_vente_destination
                or
                distribution.point_vente_source
            )

    if point_vente is None:

        point_vente = distributeur.point_vente

    fond = (
        distributeur.fond
        or
        Decimal("0.00")
    )

    return SimpleNamespace(

        idsituation="",

        numero="Non enregistree",

        date_situation=date_situation,

        distributeur=distributeur,

        point_vente=point_vente,

        fond=fond,

        montant_total_distribue=(
            montant_total_distribue
        ),

        montant_credit=calculer_credit(
            montant_total_distribue_net,
            fond,
        ),

        etat=SituationJournaliere.ETAT_OUVERTE,

    )


def _message_distributions_indisponibles(
    distributeur,
    date_situation,
):
    """
    Retourne le message d'erreur adapte lorsque
    aucune distribution ouverte n'est disponible.
    """

    toutes_distributions = distributions_du_jour(
        distributeur,
        date_situation,
        inclure_cloturees=True
    )

    if toutes_distributions.exists():

        return (
            "Toutes les distributions de "
            f"{distributeur.nom} {distributeur.prenom} "
            "pour la date du "
            f"{date_situation.strftime('%d/%m/%Y')} "
            "sont clôturées."
        )

    return (
        "Aucune distribution n'a été enregistrée "
        "pour cette personne à la date sélectionnée."
    )


def _filtre_texte(request, nom):
    """
    Nettoie un filtre texte GET.
    """

    valeur = str(
        request.GET.get(
            nom,
            ""
        )
        or
        ""
    ).strip()

    if valeur.lower() == "none":

        return ""

    return valeur


def _filtres_dates(request):
    """
    Retourne les bornes de dates de liste.
    """

    date_debut = request.GET.get(
        "date_debut",
        ""
    )

    date_fin = request.GET.get(
        "date_fin",
        ""
    )

    if (
        "date_debut" not in request.GET
        and
        "date_fin" not in request.GET
    ):

        aujourd_hui = date.today()

        date_debut = aujourd_hui.replace(
            day=1
        ).isoformat()

        date_fin = aujourd_hui.replace(
            day=monthrange(
                aujourd_hui.year,
                aujourd_hui.month
            )[1]
        ).isoformat()

    return date_debut, date_fin


def _distributeurs_filtre(utilisateur):
    """
    Retourne les distributeurs/gérants filtrables
    selon le même périmètre que la sélection.
    """

    if utilisateur.profil.role == "ADMIN":

        return (
            Distributeur.objects
            .filter(
                actif=True
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

    form = SelectionSituationForm(
        utilisateur=utilisateur
    )

    return form.fields[
        "distributeur"
    ].queryset


def _querystring_pagination(request):
    """
    Conserve les filtres lors de la pagination.
    """

    params = request.GET.copy()

    params.pop(
        "page",
        None
    )

    return params.urlencode()


def _url_retour_securisee(request):
    """
    Retourne une URL locale valide pour revenir a la page source.
    """

    retour = (
        request.POST.get("next")
        or
        request.GET.get("next")
    )

    if not retour:

        return ""

    if url_has_allowed_host_and_scheme(
        url=retour,
        allowed_hosts={
            request.get_host()
        },
        require_https=request.is_secure(),
    ):

        return retour

    return ""


def _donnees_lignes_depuis_post(
    situation,
    request
):
    """
    Recupere les montants restants saisis par produit.
    """

    donnees_lignes = {}

    lignes = (
        situation.lignes.all()
        .select_related(
            "produit",
            "produit__compagnie",
        )
    )

    for ligne in lignes:

        donnees_lignes[
            str(ligne.idlignesituation)
        ] = {
            "montant_restant": request.POST.get(
                f"montant_restant_{ligne.produit.idproduit}",
                "0"
            ),
        }

    return donnees_lignes


def _coupures_depuis_post(request):
    """
    Recupere les coupures saisies.
    """

    return {
        "10000": request.POST.get(
            "coupure_10000",
            "0"
        ),
        "5000": request.POST.get(
            "coupure_5000",
            "0"
        ),
        "2000": request.POST.get(
            "coupure_2000",
            "0"
        ),
        "1000": request.POST.get(
            "coupure_1000",
            "0"
        ),
        "500": request.POST.get(
            "coupure_500",
            "0"
        ),
    }


def _coupures_depuis_texte(texte):
    """
    Relit les coupures enregistrees dans une situation.
    """

    coupures = {
        "10000": "0",
        "5000": "0",
        "2000": "0",
        "1000": "0",
        "500": "0",
    }

    for ligne in str(texte or "").splitlines():

        if "x" not in ligne:

            continue

        valeur, quantite = ligne.split(
            "x",
            1
        )

        valeur = valeur.strip()

        if valeur in coupures:

            coupures[valeur] = quantite.strip()

    return coupures


def _annoter_montants_existants_situation(lignes):
    """
    Ajoute le montant brut restant deja enregistre.
    """

    for ligne in lignes:

        ligne.montant_restant_brut = (
            ligne.quantite_restante
            *
            ligne.prix_unitaire
        )

    return lignes


def _groupes_compagnies_lignes(lignes):
    """
    Regroupe les lignes de situation par compagnie.
    """

    lignes_triees = sorted(
        lignes,
        key=lambda ligne: (
            ligne.produit.compagnie.designation,
            ligne.produit.designation,
        )
    )

    groupes = []

    for compagnie, lignes_compagnie in groupby(
        lignes_triees,
        key=lambda ligne: ligne.produit.compagnie
    ):

        groupes.append({
            "compagnie": compagnie,
            "lignes": list(
                lignes_compagnie
            ),
        })

    return groupes


def _preparer_details_situations(
    situations_page,
    utilisateur=None
):
    """
    Prépare les groupes affichés dans les collapses.
    """

    for situation in situations_page:

        if utilisateur is not None:

            situation.peut_modifier = peut_modifier_situation(
                utilisateur,
                situation
            )

        lignes = []

        total_vendu = Decimal(
            "0.00"
        )

        total_restant = Decimal(
            "0.00"
        )

        for ligne in situation.lignes.all():

            ligne.montant_vendu = (
                calculer_valeur_nette_quantite(
                    ligne.quantite_vendue,
                    ligne.prix_unitaire,
                    ligne.taux_remise,
                )
            )

            ligne.montant_restant = (
                calculer_valeur_nette_quantite(
                    ligne.quantite_restante,
                    ligne.prix_unitaire,
                    ligne.taux_remise,
                )
            )

            total_vendu += ligne.montant_vendu

            total_restant += ligne.montant_restant

            lignes.append(
                ligne
            )

        lignes = sorted(
            lignes,
            key=lambda ligne: (
                ligne.produit.compagnie.designation,
                ligne.produit.designation,
            )
        )

        situation.total_vendu_produits = (
            total_vendu
        )

        situation.total_restant_produits = (
            total_restant
        )

        situation.groupes_compagnies = []

        for compagnie, lignes_compagnie in groupby(
            lignes,
            key=lambda ligne: ligne.produit.compagnie
        ):

            situation.groupes_compagnies.append({
                "compagnie": compagnie,
                "lignes": list(lignes_compagnie),
            })


def _preparer_details_manquants(manquants_page):
    """
    Prépare les règlements affichés dans les collapses.
    """

    for manquant in manquants_page:

        reglements = list(
            manquant.reglements.all()
        )

        manquant.reglements_liste = reglements

        manquant.total_regle = sum(
            (
                reglement.montant
                for reglement in reglements
            ),
            Decimal("0.00")
        )


def _preparer_details_reglements_manquants(
    reglements_page,
    utilisateur=None
):
    """
    Prepare les informations completes du manquant
    rattache a chaque reglement affiche.
    """

    for reglement in reglements_page:

        if utilisateur is not None:

            reglement.peut_modifier = peut_modifier_reglement_manquant(
                utilisateur,
                reglement
            )

        reglements = list(
            reglement.manquant.reglements.all()
        )

        reglement.manquant.reglements_liste = reglements

        reglement.manquant.total_regle = sum(
            (
                item.montant
                for item in reglements
            ),
            Decimal("0.00")
        )


# ==========================================================
# LISTE DES SITUATIONS GERANT
# ==========================================================

@login_required
def liste_situations_gerant(request):
    """
    Liste et calcule les situations journalieres du gerant.
    """

    if request.user.profil.role != "GERANT":

        return HttpResponseForbidden()

    point_vente = request.user.profil.point_vente

    form_calcul = SituationGerantDateForm()

    if request.method == "POST":

        form_calcul = SituationGerantDateForm(
            request.POST
        )

        if point_vente is None:

            messages.error(
                request,
                "Votre compte gerant n'est rattache a aucun point de vente."
            )

        elif form_calcul.is_valid():

            try:

                situation = calculer_situation_gerant(
                    request.user,
                    form_calcul.cleaned_data["date_situation"],
                )

                messages.success(
                    request,
                    "Situation gerant calculee avec succes."
                )

                date_situation = (
                    form_calcul.cleaned_data[
                        "date_situation"
                    ].isoformat()
                )

                return redirect(
                    (
                        f"{reverse('situations:liste_situations_gerant')}"
                        f"?date_debut={date_situation}"
                        f"&date_fin={date_situation}"
                        f"&ouvrir={situation.pk}"
                    )
                )

            except Exception as e:

                form_calcul.add_error(
                    None,
                    str(e)
                )

    date_debut, date_fin = _filtres_dates(
        request
    )

    situations = (
        SituationGerant.objects
        .filter(
            actif=True,
            point_vente=point_vente,
        )
        .select_related(
            "gerant",
            "point_vente",
            "utilisateur",
        )
        .prefetch_related(
            "lignes__produit__compagnie"
        )
    )

    if date_debut:

        situations = situations.filter(
            date_situation__gte=date_debut
        )

    if date_fin:

        situations = situations.filter(
            date_situation__lte=date_fin
        )

    situations = situations.order_by(
        "-date_situation",
        "-idsituationgerant"
    )

    totaux = situations.aggregate(
        montant_residuel=Sum(
            "montant_residuel_j_1"
        ),
        montant_jour=Sum(
            "montant_du_jour"
        ),
        total_jour=Sum(
            "total_du_jour"
        ),
        montant_distribue=Sum(
            "montant_distribue"
        ),
        montant_vendu=Sum(
            "montant_vendu"
        ),
        montant_retour=Sum(
            "montant_retour"
        ),
        total_vendu=Sum(
            "total_vendu"
        ),
        total_restant=Sum(
            "total_restant"
        ),
    )

    page = paginer(
        situations,
        request.GET.get(
            "page"
        )
    )

    preparer_affichage_situations_gerant(
        page
    )

    return render(
        request,
        "situations/situations_gerant.html",
        {
            "situations": page,
            "form_calcul": form_calcul,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "ouvrir": request.GET.get(
                "ouvrir",
                ""
            ),
            "pagination_querystring": (
                _querystring_pagination(
                    request
                )
            ),
            "totaux": {
                "montant_residuel_j_1": (
                    totaux["montant_residuel"]
                    or
                    Decimal("0.00")
                ),
                "montant_du_jour": (
                    totaux["montant_jour"]
                    or
                    Decimal("0.00")
                ),
                "total_du_jour": (
                    totaux["total_jour"]
                    or
                    Decimal("0.00")
                ),
                "montant_distribue": (
                    totaux["montant_distribue"]
                    or
                    Decimal("0.00")
                ),
                "montant_vendu": (
                    totaux["montant_vendu"]
                    or
                    Decimal("0.00")
                ),
                "montant_retour": (
                    totaux["montant_retour"]
                    or
                    Decimal("0.00")
                ),
                "total_vendu": (
                    totaux["total_vendu"]
                    or
                    Decimal("0.00")
                ),
                "total_restant": (
                    totaux["total_restant"]
                    or
                    Decimal("0.00")
                ),
            },
        }
    )


# ==========================================================
# LISTE DES SITUATIONS CLOTUREES
# ==========================================================

@login_required
def liste_situations(request):
    """
    Liste des situations clôturées, c'est-à-dire
    des versements déjà enregistrés.
    """

    numero = _filtre_texte(
        request,
        "numero"
    )

    date_debut, date_fin = _filtres_dates(
        request
    )

    distributeur = request.GET.get(
        "distributeur",
        ""
    )

    situations = (
        situations_visibles(
            request.user
        )
        .filter(
            etat=SituationJournaliere.ETAT_CLOTUREE
        )
    )

    if numero:

        situations = situations.filter(
            numero__icontains=numero
        )

    if date_debut:

        situations = situations.filter(
            date_situation__gte=date_debut
        )

    if date_fin:

        situations = situations.filter(
            date_situation__lte=date_fin
        )

    if distributeur:

        situations = situations.filter(
            distributeur_id=distributeur
        )

    situations = situations.order_by(
        "-date_situation",
        "-idsituation"
    )

    totaux = situations.aggregate(
        total_distribue=Sum(
            "montant_total_distribue"
        ),
        total_verse=Sum(
            "montant_total_verse"
        ),
        total_manquant=Sum(
            "montant_manquant"
        ),
        total_surplus=Sum(
            "montant_surplus"
        ),
    )

    page = paginer(
        situations,
        request.GET.get(
            "page"
        )
    )

    _preparer_details_situations(
        page,
        request.user
    )

    return render(
        request,
        "situations/liste.html",
        {
            "situations": page,
            "numero": numero,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "distributeur_selectionne": distributeur,
            "distributeurs": _distributeurs_filtre(
                request.user
            ),
            "pagination_querystring": (
                _querystring_pagination(
                    request
                )
            ),
            "total_distribue": (
                totaux["total_distribue"]
                or
                Decimal("0.00")
            ),
            "total_verse": (
                totaux["total_verse"]
                or
                Decimal("0.00")
            ),
            "total_manquant": (
                totaux["total_manquant"]
                or
                Decimal("0.00")
            ),
            "total_surplus": (
                totaux["total_surplus"]
                or
                Decimal("0.00")
            ),
        }
    )


# ==========================================================
# LISTE DES REGLEMENTS DE MANQUANTS
# ==========================================================

@login_required
def liste_reglements_manquants(request):
    """
    Liste detaillee des reglements effectues
    sur les manquants.
    """

    numero = _filtre_texte(
        request,
        "numero"
    )

    numero_manquant = _filtre_texte(
        request,
        "numero_manquant"
    )

    date_debut, date_fin = _filtres_dates(
        request
    )

    distributeur = request.GET.get(
        "distributeur",
        ""
    )

    reglements = reglements_manquants_visibles(
        request.user
    )

    if numero:

        reglements = reglements.filter(
            numero__icontains=numero
        )

    if numero_manquant:

        reglements = reglements.filter(
            manquant__numero__icontains=numero_manquant
        )

    if date_debut:

        reglements = reglements.filter(
            date_reglement__gte=date_debut
        )

    if date_fin:

        reglements = reglements.filter(
            date_reglement__lte=date_fin
        )

    if distributeur:

        reglements = reglements.filter(
            manquant__distributeur_id=distributeur
        )

    reglements = reglements.order_by(
        "-date_reglement",
        "-idreglement"
    )

    totaux = reglements.aggregate(
        total_regle=Sum(
            "montant"
        )
    )

    page = paginer(
        reglements,
        request.GET.get(
            "page"
        )
    )

    _preparer_details_reglements_manquants(
        page,
        request.user
    )

    return render(
        request,
        "situations/reglements_manquants.html",
        {
            "reglements": page,
            "numero": numero,
            "numero_manquant": numero_manquant,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "distributeur_selectionne": distributeur,
            "distributeurs": _distributeurs_filtre(
                request.user
            ),
            "pagination_querystring": (
                _querystring_pagination(
                    request
                )
            ),
            "total_regle": (
                totaux["total_regle"]
                or
                Decimal("0.00")
            ),
        }
    )


# ==========================================================
# LISTE DES MANQUANTS
# ==========================================================

@login_required
def liste_manquants(request):
    """
    Suivi des manquants constatés à la clôture.
    """

    numero = _filtre_texte(
        request,
        "numero"
    )

    date_debut, date_fin = _filtres_dates(
        request
    )

    statut = request.GET.get(
        "statut",
        Manquant.STATUT_EN_COURS
    )

    distributeur = request.GET.get(
        "distributeur",
        ""
    )

    manquants = manquants_visibles(
        request.user
    )

    if numero:

        manquants = manquants.filter(
            numero__icontains=numero
        )

    if date_debut:

        manquants = manquants.filter(
            situation__date_situation__gte=date_debut
        )

    if date_fin:

        manquants = manquants.filter(
            situation__date_situation__lte=date_fin
        )

    if statut:

        manquants = manquants.filter(
            statut=statut
        )

    if distributeur:

        manquants = manquants.filter(
            distributeur_id=distributeur
        )

    manquants = manquants.order_by(
        "-date_creation",
        "-idmanquant"
    )

    totaux = manquants.aggregate(
        total_manquant=Sum(
            "montant"
        ),
        total_reste=Sum(
            "reste_a_payer"
        ),
    )

    page = paginer(
        manquants,
        request.GET.get(
            "page"
        )
    )

    _preparer_details_manquants(
        page
    )

    return render(
        request,
        "situations/manquants.html",
        {
            "manquants": page,
            "numero": numero,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "statut": statut,
            "statuts": Manquant.STATUTS,
            "distributeur_selectionne": distributeur,
            "distributeurs": _distributeurs_filtre(
                request.user
            ),
            "pagination_querystring": (
                _querystring_pagination(
                    request
                )
            ),
            "total_manquant": (
                totaux["total_manquant"]
                or
                Decimal("0.00")
            ),
            "total_reste": (
                totaux["total_reste"]
                or
                Decimal("0.00")
            ),
        }
    )


# ==========================================================
# REGLEMENT D'UN MANQUANT
# ==========================================================

@login_required
def regler_manquant_view(request, pk):
    """
    Enregistre un règlement partiel ou total
    d'un manquant.
    """

    manquant = get_object_or_404(
        manquants_visibles(
            request.user
        ),
        pk=pk
    )

    if manquant.statut == Manquant.STATUT_SOLDE:

        messages.info(
            request,
            "Ce manquant est déjà soldé."
        )

        return redirect(
            "situations:liste_manquants"
        )

    if request.method == "POST":

        form = ReglementManquantForm(
            request.POST
        )

        if form.is_valid():

            try:

                regler_manquant(
                    manquant=manquant,
                    date_reglement=(
                        form.cleaned_data[
                            "date_reglement"
                        ]
                    ),
                    montant=(
                        form.cleaned_data[
                            "montant"
                        ]
                    ),
                    utilisateur=request.user,
                )

                messages.success(
                    request,
                    "Règlement enregistré avec succès."
                )

                return redirect(
                    "situations:liste_manquants"
                )

            except Exception as e:

                form.add_error(
                    None,
                    str(e)
                )

    else:

        form = ReglementManquantForm()

    return render(
        request,
        "situations/regler_manquant.html",
        {
            "form": form,
            "manquant": manquant,
        }
    )


# ==========================================================
# MODIFICATION D'UN REGLEMENT DE MANQUANT
# ==========================================================

@login_required
def modifier_reglement_manquant_view(request, pk):
    """
    Corrige un reglement de manquant.
    """

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    reglement = get_object_or_404(
        reglements_manquants_visibles(
            request.user
        ),
        pk=pk
    )

    next_url = _url_retour_securisee(
        request
    )

    if not peut_modifier_reglement_manquant(
        request.user,
        reglement
    ):

        messages.error(
            request,
            "Ce reglement n'est pas modifiable. "
            "Le delai de 3 jours est depasse."
        )

        if next_url:

            return redirect(
                next_url
            )

        return redirect(
            "situations:liste_reglements_manquants"
        )

    if request.method == "POST":

        form = ReglementManquantForm(
            request.POST
        )

        if form.is_valid():

            try:

                modifier_reglement_manquant(
                    reglement=reglement,
                    date_reglement=(
                        form.cleaned_data[
                            "date_reglement"
                        ]
                    ),
                    montant=form.cleaned_data[
                        "montant"
                    ],
                    utilisateur=request.user,
                )

                messages.success(
                    request,
                    "Reglement modifie avec succes."
                )

                if next_url:

                    return redirect(
                        next_url
                    )

                return redirect(
                    "situations:liste_reglements_manquants"
                )

            except Exception as e:

                form.add_error(
                    None,
                    str(e)
                )

    else:

        form = ReglementManquantForm(
            initial={
                "date_reglement": (
                    reglement.date_reglement
                ),
                "montant": reglement.montant,
            }
        )

    return render(
        request,
        "situations/regler_manquant.html",
        {
            "form": form,
            "manquant": reglement.manquant,
            "reglement": reglement,
            "titre": "Modification d'un reglement",
            "bouton_enregistrer": "Modifier le reglement",
            "next_url": next_url,
            "url_retour_direct": next_url,
        }
    )


# ==========================================================
# MODIFICATION D'UNE SITUATION CLOTUREE
# ==========================================================

@login_required
def modifier_situation_view(request, pk):
    """
    Corrige une situation journaliere cloturee.
    """

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    situation = get_object_or_404(
        situations_visibles(
            request.user
        ),
        pk=pk,
        actif=True,
    )

    next_url = _url_retour_securisee(
        request
    )

    if not peut_modifier_situation(
        request.user,
        situation
    ):

        messages.error(
            request,
            "Cette situation n'est pas modifiable. "
            "Le delai de 3 jours est depasse."
        )

        if next_url:

            return redirect(
                next_url
            )

        return redirect(
            "situations:liste_situations"
        )

    if request.method == "POST":

        try:

            modifier_situation_cloturee(
                situation=situation,
                donnees_lignes=_donnees_lignes_depuis_post(
                    situation,
                    request
                ),
                montant_total_verse=request.POST.get(
                    "montant_total_verse",
                    "0"
                ),
                coupures=_coupures_depuis_post(
                    request
                ),
                utilisateur=request.user,
            )

            messages.success(
                request,
                "Situation modifiee avec succes."
            )

            if next_url:

                return redirect(
                    next_url
                )

            return redirect(
                "situations:liste_situations"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    distributions = distributions_du_jour(
        situation.distributeur,
        situation.date_situation,
        inclure_cloturees=True,
    )

    lignes = list(
        situation.lignes.all()
        .select_related(
            "produit",
            "produit__compagnie",
        )
    )

    lignes = annoter_lignes_reliquat(
        lignes,
        situation.distributeur,
        situation.date_situation,
        distributions,
    )

    _annoter_montants_existants_situation(
        lignes
    )

    form = SelectionSituationForm(
        initial={
            "distributeur": situation.distributeur,
            "date_situation": situation.date_situation,
        },
        utilisateur=request.user,
    )

    coupures = _coupures_depuis_texte(
        situation.coupures
    )

    return render(
        request,
        "situations/selection.html",
        {
            "form": form,
            "situation": situation,
            "distributions": distributions,
            "lignes": lignes,
            "groupes_compagnies": (
                _groupes_compagnies_lignes(
                    lignes
                )
            ),
            "titre": "Modification du versement",
            "action_form": "modifier",
            "bouton_situation": "Modifier le versement",
            "mode_modification": True,
            "montant_total_verse_initial": situation.montant_total_verse,
            "coupure_10000": coupures["10000"],
            "coupure_5000": coupures["5000"],
            "coupure_2000": coupures["2000"],
            "coupure_1000": coupures["1000"],
            "coupure_500": coupures["500"],
            "next_url": next_url,
            "url_retour_direct": next_url,
        }
    )


# ==========================================================
# VALIDATION / REJET D'UN VERSEMENT GERANT
# ==========================================================

@login_required
def valider_versement_gerant_view(request, pk):
    """
    Valide un versement soumis par un gerant.
    """

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    if request.method != "POST":

        return HttpResponseForbidden()

    next_url = _url_retour_securisee(
        request
    )

    situation = get_object_or_404(
        situations_visibles(
            request.user
        ),
        pk=pk,
        actif=True,
        etat=SituationJournaliere.ETAT_ATTENTE_VALIDATION,
    )

    try:

        valider_versement_gerant(
            situation,
            request.user,
        )

        messages.success(
            request,
            "Versement valide avec succes."
        )

    except Exception as e:

        messages.error(
            request,
            str(e)
        )

    if next_url:

        return redirect(
            next_url
        )

    return redirect(
        "apercu_directeur"
    )


@login_required
def rejeter_versement_gerant_view(request, pk):
    """
    Refuse un versement soumis par un gerant.
    """

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    if request.method != "POST":

        return HttpResponseForbidden()

    next_url = _url_retour_securisee(
        request
    )

    situation = get_object_or_404(
        situations_visibles(
            request.user
        ),
        pk=pk,
        actif=True,
        etat=SituationJournaliere.ETAT_ATTENTE_VALIDATION,
    )

    try:

        rejeter_versement_gerant(
            situation,
            request.user,
        )

        messages.success(
            request,
            "Versement rejete. Le gerant peut le corriger "
            "et le resoumettre."
        )

    except Exception as e:

        messages.error(
            request,
            str(e)
        )

    if next_url:

        return redirect(
            next_url
        )

    return redirect(
        "apercu_directeur"
    )


# ==========================================================
# VERSEMENT GERANT AU DIRECTEUR
# ==========================================================

@login_required
def versement_gerant(request):
    """
    Permet a un gerant de soumettre au Directeur le
    versement des distributions qu'il a recues a une date.

    La soumission n'est pas definitive : les distributions
    restent ouvertes et le manquant n'est pas cree.
    """

    if request.user.profil.role != "GERANT":

        return HttpResponseForbidden()

    gerant = gerant_du_point_vente(
        request.user.profil.point_vente
    )

    if (
        request.method == "GET"
        and
        request.GET.get("nouveau") != "1"
    ):

        date_debut, date_fin = _filtres_dates(
            request
        )

        etat = _filtre_texte(
            request,
            "etat"
        )

        etats_versement = [
            SituationJournaliere.ETAT_ATTENTE_VALIDATION,
            SituationJournaliere.ETAT_CLOTUREE,
            SituationJournaliere.ETAT_REFUSEE,
        ]

        versements = (
            SituationJournaliere.objects
            .none()
        )

        if gerant is None:

            messages.error(
                request,
                "Aucun gerant actif n'est rattache a votre point de vente."
            )

        else:

            versements = (
                SituationJournaliere.objects
                .filter(
                    actif=True,
                    distributeur=gerant,
                    etat__in=etats_versement,
                )
                .select_related(
                    "distributeur",
                    "point_vente",
                    "utilisateur",
                )
                .prefetch_related(
                    "lignes__produit__compagnie",
                    "manquant",
                )
            )

            if date_debut:

                versements = versements.filter(
                    date_situation__gte=date_debut
                )

            if date_fin:

                versements = versements.filter(
                    date_situation__lte=date_fin
                )

            if etat in etats_versement:

                versements = versements.filter(
                    etat=etat
                )

        versements = versements.order_by(
            "-date_situation",
            "-idsituation"
        )

        totaux = versements.aggregate(
            total_distribue=Sum(
                "montant_total_distribue"
            ),
            total_verse=Sum(
                "montant_total_verse"
            ),
            total_manquant=Sum(
                "montant_manquant"
            ),
            total_surplus=Sum(
                "montant_surplus"
            ),
        )

        page = paginer(
            versements,
            request.GET.get(
                "page"
            )
        )

        _preparer_details_situations(
            page,
            request.user
        )

        return render(
            request,
            "situations/versements_gerant.html",
            {
                "versements": page,
                "gerant": gerant,
                "date_debut": date_debut,
                "date_fin": date_fin,
                "etat": etat,
                "etats_versement": (
                    SituationJournaliere.ETATS
                ),
                "pagination_querystring": (
                    _querystring_pagination(
                        request
                    )
                ),
                "total_distribue": (
                    totaux["total_distribue"]
                    or
                    Decimal("0.00")
                ),
                "total_verse": (
                    totaux["total_verse"]
                    or
                    Decimal("0.00")
                ),
                "total_manquant": (
                    totaux["total_manquant"]
                    or
                    Decimal("0.00")
                ),
                "total_surplus": (
                    totaux["total_surplus"]
                    or
                    Decimal("0.00")
                ),
            }
        )

    situation = None
    distributions = None
    lignes = None

    form = VersementGerantSelectionForm()

    if gerant is None:

        messages.error(
            request,
            "Aucun gerant actif n'est rattache a votre point de vente."
        )

    elif request.method == "POST":

        form = VersementGerantSelectionForm(
            request.POST
        )

        if form.is_valid():

            date_situation = form.cleaned_data[
                "date_situation"
            ]

            distributions = distributions_du_jour(
                gerant,
                date_situation
            )

            if not distributions.exists():

                form.add_error(
                    None,
                    _message_distributions_indisponibles(
                        gerant,
                        date_situation
                    )
                )

            else:

                situation = situation_existante(
                    gerant,
                    date_situation
                )

                if (
                    situation is not None
                    and
                    situation.etat == SituationJournaliere.ETAT_CLOTUREE
                ):

                    form.add_error(
                        None,
                        "Le versement de cette date est deja cloture."
                    )

                elif (
                    request.POST.get("action")
                    ==
                    "soumettre_versement_gerant"
                ):

                    try:

                        if situation is None:

                            situation = creer_situation_journaliere(
                                distributeur=gerant,
                                date_situation=date_situation,
                                utilisateur=request.user,
                            )

                        elif not situation.lignes.exists():

                            creer_lignes_situation(
                                situation,
                                distributions
                            )

                        soumettre_versement_gerant(
                            situation=situation,
                            donnees_lignes=(
                                _donnees_lignes_depuis_post(
                                    situation,
                                    request
                                )
                            ),
                            montant_total_verse=request.POST.get(
                                "montant_total_verse",
                                "0"
                            ),
                            coupures=_coupures_depuis_post(
                                request
                            ),
                            utilisateur=request.user,
                        )

                        messages.success(
                            request,
                            "Versement soumis au Directeur pour validation."
                        )

                        return redirect(
                            "situations:versement_gerant"
                        )

                    except Exception as e:

                        messages.error(
                            request,
                            str(e)
                        )

                        if situation is not None:

                            lignes = (
                                situation.lignes.all()
                                .select_related(
                                    "produit",
                                    "produit__compagnie",
                                )
                            )

                elif situation is not None:

                    lignes = (
                        situation.lignes.all()
                        .select_related(
                            "produit",
                            "produit__compagnie",
                        )
                    )

                    if not lignes.exists():

                        creer_lignes_situation(
                            situation,
                            distributions
                        )

                        lignes = (
                            situation.lignes.all()
                            .select_related(
                                "produit",
                                "produit__compagnie",
                            )
                        )

                    if (
                        situation.etat
                        ==
                        SituationJournaliere.ETAT_ATTENTE_VALIDATION
                    ):

                        messages.info(
                            request,
                            "Un versement est deja en attente "
                            "pour cette date. Vous pouvez le mettre a jour."
                        )

                    elif (
                        situation.etat
                        ==
                        SituationJournaliere.ETAT_REFUSEE
                    ):

                        messages.warning(
                            request,
                            "Ce versement a ete refuse. "
                            "Vous pouvez le corriger et le resoumettre."
                        )

                else:

                    lignes = construire_lignes_affichage_situation(
                        gerant,
                        date_situation,
                        distributions
                    )

                    situation = _situation_affichage_temporaire(
                        gerant,
                        date_situation,
                        distributions,
                    )

        else:

            messages.error(
                request,
                "La date selectionnee est invalide."
            )

    groupes_compagnies = []

    situation_en_base = isinstance(
        situation,
        SituationJournaliere
    )

    if situation is not None and distributions is not None:

        situation.montant_total_distribue = calculer_total_distribue(
            situation.distributeur,
            situation.date_situation
        )

        situation.montant_credit = calculer_credit(
            calculer_total_distribue_net(
                situation.distributeur,
                situation.date_situation,
            ),
            situation.fond,
        )

    if lignes:

        if distributions:

            lignes = annoter_lignes_reliquat(
                list(lignes),
                situation.distributeur,
                situation.date_situation,
                distributions
            )

        if situation_en_base:

            lignes = _annoter_montants_existants_situation(
                lignes
            )

        groupes_compagnies = _groupes_compagnies_lignes(
            lignes
        )

    coupures = (
        _coupures_depuis_texte(
            situation.coupures
        )
        if situation_en_base
        else {
            "10000": "0",
            "5000": "0",
            "2000": "0",
            "1000": "0",
            "500": "0",
        }
    )

    return render(
        request,
        "situations/selection.html",
        {
            "form": form,
            "situation": situation,
            "distributions": distributions,
            "lignes": lignes,
            "groupes_compagnies": groupes_compagnies,
            "titre": "Versement au Directeur",
            "gerant_connecte": gerant,
            "mode_versement_gerant": True,
            "action_form": "soumettre_versement_gerant",
            "bouton_situation": "Soumettre le versement",
            "url_retour_direct": reverse(
                "situations:versement_gerant"
            ),
            "montant_total_verse_initial": (
                situation.montant_total_verse
                if situation_en_base
                else 0
            ),
            "coupure_10000": coupures["10000"],
            "coupure_5000": coupures["5000"],
            "coupure_2000": coupures["2000"],
            "coupure_1000": coupures["1000"],
            "coupure_500": coupures["500"],
        }
    )


# ==========================================================
# SELECTION / PREPARATION D'UNE SITUATION
# ==========================================================

@login_required
def ajouter_situation(request):
    """
    Gestion d'une situation journalière en deux étapes
    dans un seul formulaire :

        1. Sélection du gérant/distributeur et de la date.
        2. Saisie et clôture de la situation.

    IMPORTANT :
        Le bouton Rechercher ne crée aucune situation.

        La situation est créée uniquement au moment
        de la clôture si elle n'existe pas encore.
    """

    # ======================================================
    # INITIALISATION
    # ======================================================

    situation = None
    distributions = None
    lignes = None

    form = SelectionSituationForm(
        utilisateur=request.user
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        form = SelectionSituationForm(
            request.POST,
            utilisateur=request.user
        )

        # ==================================================
        # ETAPE 2 : CLOTURE
        # ==================================================

        if request.POST.get("action") == "cloturer":

            # ----------------------------------------------
            # RECUPERATION DU CONTEXTE DE CLOTURE
            # ----------------------------------------------

            try:

                (
                    distributeur,
                    date_situation,
                    situation,
                ) = _contexte_cloture_depuis_post(
                    request
                )

            except ValueError as e:

                messages.error(
                    request,
                    str(e)
                )

                return redirect(
                    "situations:ajouter_situation"
                )

            # ----------------------------------------------
            # RECUPERATION DES DISTRIBUTIONS
            # ----------------------------------------------

            distributions = (
                distributions_du_jour(

                    distributeur,

                    date_situation

                )
            )

            if not distributions.exists():

                messages.error(
                    request,
                    _message_distributions_indisponibles(
                        distributeur,
                        date_situation
                    )
                )

                return redirect(
                    "situations:ajouter_situation"
                )

            # ----------------------------------------------
            # RECHERCHE D'UNE SITUATION EXISTANTE
            # ----------------------------------------------

            situation = situation_existante(

                distributeur,

                date_situation

            )

            # ----------------------------------------------
            # CREATION DE LA SITUATION SI NECESSAIRE
            # ----------------------------------------------

            if situation is None:

                try:

                    situation = (
                        creer_situation_journaliere(

                            distributeur=distributeur,

                            date_situation=(
                                date_situation
                            ),

                            utilisateur=request.user,

                        )
                    )

                except Exception as e:

                    messages.error(
                        request,
                        str(e)
                    )

                    return redirect(
                        "situations:ajouter_situation"
                    )

            # ----------------------------------------------
            # RECUPERATION DES LIGNES DE LA SITUATION
            # ----------------------------------------------

            lignes = (
                situation.lignes.all()
                .select_related(
                    "produit",
                    "produit__compagnie",
                )
            )

            # ----------------------------------------------
            # RECUPERATION DES MONTANTS RESTANTS
            #
            # IMPORTANT :
            # On utilise maintenant l'ID DU PRODUIT
            # et non l'ID de la ligne de situation.
            # ----------------------------------------------

            donnees_lignes = {}

            for ligne in lignes:

                donnees_lignes[
                    str(ligne.idlignesituation)
                ] = {

                    "montant_restant": request.POST.get(

                        f"montant_restant_"
                        f"{ligne.produit.idproduit}",

                        "0"

                    ),

                }

            # ----------------------------------------------
            # MONTANTS
            # ----------------------------------------------

            montant_total_verse = request.POST.get(
                "montant_total_verse",
                "0"
            )

            # ----------------------------------------------
            # COUPURES
            # ----------------------------------------------

            coupures = {

                "10000": request.POST.get(
                    "coupure_10000",
                    "0"
                ),

                "5000": request.POST.get(
                    "coupure_5000",
                    "0"
                ),

                "2000": request.POST.get(
                    "coupure_2000",
                    "0"
                ),

                "1000": request.POST.get(
                    "coupure_1000",
                    "0"
                ),

                "500": request.POST.get(
                    "coupure_500",
                    "0"
                ),

            }

            # ----------------------------------------------
            # CLOTURE
            # ----------------------------------------------

            try:

                situation = cloturer_situation(

                    situation=situation,

                    donnees_lignes=donnees_lignes,

                    montant_total_verse=montant_total_verse,

                    coupures=coupures,

                    utilisateur=request.user,

                )

                messages.success(

                    request,

                    "Situation journalière clôturée "
                    "avec succès."

                )

                return redirect(
                    "situations:ajouter_situation"
                )

            except Exception as e:

                messages.error(
                    request,
                    str(e)
                )

        # ==================================================
        # ETAPE 1 : RECHERCHE
        # ==================================================

        else:

            if form.is_valid():

                distributeur = (
                    form.cleaned_data[
                        "distributeur"
                    ]
                )

                date_situation = (
                    form.cleaned_data[
                        "date_situation"
                    ]
                )

                # ------------------------------------------
                # RECHERCHE DES DISTRIBUTIONS
                # ------------------------------------------

                distributions = (
                    distributions_du_jour(

                        distributeur,

                        date_situation

                    )
                )

                if not distributions.exists():

                    form.add_error(

                        None,

                        _message_distributions_indisponibles(
                            distributeur,
                            date_situation
                        )

                    )

                else:

                    # --------------------------------------
                    # SITUATION EXISTANTE UNIQUEMENT
                    #
                    # IMPORTANT :
                    # Nous ne la créons PAS ici.
                    # --------------------------------------

                    situation = situation_existante(

                        distributeur,

                        date_situation

                    )

                    # --------------------------------------
                    # SI UNE SITUATION EXISTE DEJA
                    # --------------------------------------

                    if situation is not None:

                        lignes = (
                            situation.lignes.all()
                            .select_related(
                                "produit",
                                "produit__compagnie",
                            )
                        )

                    else:

                        # ----------------------------------
                        # AUCUNE SITUATION :
                        #
                        # Construction temporaire du tableau
                        # directement depuis les distributions.
                        # ----------------------------------

                        lignes = (
                            construire_lignes_affichage_situation(
                                distributeur,
                                date_situation,
                                distributions
                            )
                        )

                        situation = (
                            _situation_affichage_temporaire(

                                distributeur,

                                date_situation,

                                distributions,

                            )
                        )

            # ----------------------------------------------
            # AFFICHAGE D'UNE SITUATION EXISTANTE
            # ----------------------------------------------

            if situation is not None and lignes is None:

                lignes = (
                    situation.lignes.all()
                    .select_related(
                        "produit",
                        "produit__compagnie",
                    )
                )

                distributions = (
                    distributions_du_jour(

                        situation.distributeur,

                        situation.date_situation

                    )
                )

    # ======================================================
    # PREPARATION DES DONNEES POUR L'AFFICHAGE
    # ======================================================

    groupes_compagnies = []

    if situation is not None and distributions is not None:

        situation.montant_total_distribue = calculer_total_distribue(
            situation.distributeur,
            situation.date_situation
        )

        situation.montant_credit = calculer_credit(
            calculer_total_distribue_net(
                situation.distributeur,
                situation.date_situation,
            ),
            situation.fond,
        )

    if lignes:

        # --------------------------------------------------
        # Ajout des informations de reliquat et de taux.
        # --------------------------------------------------

        if distributions:

            lignes = annoter_lignes_reliquat(
                list(lignes),
                situation.distributeur,
                situation.date_situation,
                distributions
            )

        # --------------------------------------------------
        # TRI PAR COMPAGNIE PUIS PRODUIT
        # --------------------------------------------------

        lignes_triees = sorted(

            lignes,

            key=lambda ligne: (

                ligne.produit
                .compagnie
                .designation,

                ligne.produit
                .designation,

            )

        )

        # --------------------------------------------------
        # REGROUPEMENT PAR COMPAGNIE
        # --------------------------------------------------

        for compagnie, lignes_compagnie in groupby(

            lignes_triees,

            key=lambda ligne:
                ligne.produit.compagnie

        ):

            groupes_compagnies.append({

                "compagnie": compagnie,

                "lignes": list(
                    lignes_compagnie
                ),

            })

    # ======================================================
    # CONTEXTE
    # ======================================================

    contexte = {

        "form": form,

        "situation": situation,

        "distributions": distributions,

        "lignes": lignes,

        "groupes_compagnies": (
            groupes_compagnies
        ),

        "titre": "Situation journalière",

    }

    return render(

        request,

        "situations/selection.html",

        contexte

    )
