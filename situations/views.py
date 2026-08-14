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

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from referentiel.models import Distributeur

from .forms import (
    SelectionSituationForm,
    ReglementManquantForm,
)

from .selectors import (
    distributions_du_jour,
    situation_existante,
    situations_visibles,
    manquants_visibles,
    paginer,
)

from .services import (
    creer_situation_journaliere,
    cloturer_situation,
    regler_manquant,
)

from .models import (
    SituationJournaliere,
    Manquant,
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

    montant_total_distribue = Decimal(
        "0.00"
    )

    point_vente = None

    for distribution in distributions:

        montant_total_distribue += (
            distribution.montant_net
            or
            Decimal("0.00")
        )

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
            montant_total_distribue,
            fond,
        ),

        etat=SituationJournaliere.ETAT_OUVERTE,

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


def _preparer_details_situations(situations_page):
    """
    Prépare les groupes affichés dans les collapses.
    """

    for situation in situations_page:

        lignes = []

        total_vendu = Decimal(
            "0.00"
        )

        total_restant = Decimal(
            "0.00"
        )

        for ligne in situation.lignes.all():

            ligne.montant_vendu = (
                ligne.quantite_vendue
                *
                ligne.prix_unitaire
            )

            ligne.montant_restant = (
                ligne.quantite_restante
                *
                ligne.prix_unitaire
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
    )

    page = paginer(
        situations,
        request.GET.get(
            "page"
        )
    )

    _preparer_details_situations(
        page
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
                    "Aucune distribution n'a été "
                    "enregistrée pour cette personne "
                    "à la date sélectionnée."
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
            # RECUPERATION DES MONTANTS VENDUS
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

                    "montant_vendu": request.POST.get(

                        f"montant_vendu_"
                        f"{ligne.produit.idproduit}",

                        "0"

                    ),

                }

            # ----------------------------------------------
            # MONTANTS
            # ----------------------------------------------

            montant_credit_verse = request.POST.get(
                "montant_credit_verse",
                "0"
            )

            montant_vente_verse = request.POST.get(
                "montant_vente_verse",
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

                    montant_credit_verse=(
                        montant_credit_verse
                    ),

                    montant_vente_verse=(
                        montant_vente_verse
                    ),

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

                        "Aucune distribution n'a été "
                        "enregistrée pour cette personne "
                        "à la date sélectionnée."

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

                        produits = {}

                        for distribution in distributions:

                            for ligne_distribution in (
                                distribution.lignes
                                .select_related(
                                    "produit",
                                    "produit__compagnie",
                                )
                            ):

                                produit_id = (
                                    ligne_distribution
                                    .produit
                                    .idproduit
                                )

                                if produit_id not in produits:

                                    produits[
                                        produit_id
                                    ] = {

                                        "produit": (
                                            ligne_distribution
                                            .produit
                                        ),

                                        "prix_unitaire": (
                                            ligne_distribution
                                            .prix_unitaire
                                        ),

                                        "quantite_distribuee": (
                                            Decimal("0.00")
                                        ),

                                        "taux_distribution": (
                                            ligne_distribution
                                            .taux_remise
                                        ),

                                    }

                                produits[
                                    produit_id
                                ][
                                    "quantite_distribuee"
                                ] += (
                                    ligne_distribution
                                    .quantite
                                )

                        # ----------------------------------
                        # CONSTRUCTION DES LIGNES
                        # ----------------------------------

                        lignes = []

                        for donnees in produits.values():

                            lignes.append(

                                SimpleNamespace(

                                    idlignesituation=(
                                        None
                                    ),

                                    produit=(
                                        donnees[
                                            "produit"
                                        ]
                                    ),

                                    prix_unitaire=(
                                        donnees[
                                            "prix_unitaire"
                                        ]
                                    ),

                                    quantite_distribuee=(
                                        donnees[
                                            "quantite_distribuee"
                                        ]
                                    ),

                                    quantite_vendue=(
                                        Decimal("0.00")
                                    ),

                                    quantite_restante=(
                                        donnees[
                                            "quantite_distribuee"
                                        ]
                                    ),

                                    taux_distribution=(
                                        donnees[
                                            "taux_distribution"
                                        ]
                                    ),

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

    if lignes:

        # --------------------------------------------------
        # SI UNE SITUATION EXISTE :
        # récupérer le premier taux directement
        # depuis les distributions.
        # --------------------------------------------------

        if distributions:

            for ligne in lignes:

                ligne.taux_distribution = (
                    Decimal("0.00")
                )

                taux_trouve = False

                for distribution in distributions:

                    for ligne_dist in (
                        distribution.lignes.all()
                    ):

                        if (
                            ligne_dist.produit_id
                            ==
                            ligne.produit.idproduit
                        ):

                            ligne.taux_distribution = (
                                ligne_dist.taux_remise
                            )

                            taux_trouve = True

                            break

                    if taux_trouve:

                        break

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
