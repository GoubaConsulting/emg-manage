"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Vues du module Situations.

==========================================================
"""
from decimal import Decimal

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.shortcuts import (
    render,
    redirect,
)

from .forms import (
    SelectionSituationForm,
)

from .selectors import (
    distributions_du_jour,
    situation_existante,
)

from .services import (
    creer_situation_journaliere,
    cloturer_situation,
)

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from .models import (
    SituationJournaliere,
)

from itertools import groupby

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
            # RECUPERATION DU DISTRIBUTEUR ET DE LA DATE
            # ----------------------------------------------

            distributeur_id = request.POST.get(
                "distributeur"
            )

            date_situation = request.POST.get(
                "date_situation"
            )

            if not distributeur_id or not date_situation:

                messages.error(
                    request,
                    "Le distributeur et la date "
                    "sont obligatoires."
                )

                return redirect(
                    "situations:ajouter_situation"
                )

            # ----------------------------------------------
            # VALIDATION DU FORMULAIRE DE SELECTION
            # ----------------------------------------------

            form_selection = SelectionSituationForm(
                request.POST,
                utilisateur=request.user
            )

            if not form_selection.is_valid():

                messages.error(
                    request,
                    "Les informations de sélection "
                    "sont invalides."
                )

                return redirect(
                    "situations:ajouter_situation"
                )

            distributeur = (
                form_selection.cleaned_data[
                    "distributeur"
                ]
            )

            date_situation = (
                form_selection.cleaned_data[
                    "date_situation"
                ]
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

                        from types import SimpleNamespace

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