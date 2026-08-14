"""
==========================================================
Projet : EMG MANAGE

Module : Objectif

Description :
Vues du module Objectif.

==========================================================
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import (
    redirect,
    render
)
from django.urls import reverse

from datetime import date
from urllib.parse import urlencode

from referentiel.models import PointVente

from .forms import ObjectifForm

from .permissions import (
    peut_consulter,
    peut_creer,
    peut_modifier,
    peut_supprimer
)

from .selectors import (
    rechercher_objectifs,
    paginer,
    objectif_par_id
)

from .services import (
    creer_objectif,
    modifier_objectif,
    supprimer_objectif,
    recalculer_objectifs,
    existe_commandes_periode
)


NOMS_MOIS = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


def filtre_texte(request, nom):
    """
    Retourne un filtre texte propre pour l'affichage.
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


def redirection_liste_avec_filtres(request):
    """
    Retourne vers la liste en conservant les filtres POST.
    """

    filtres = {}

    for nom in (
        "designation",
        "mois",
        "annee",
        "point_vente"
    ):

        valeur = request.POST.get(
            nom,
            ""
        )

        if valeur:

            filtres[nom] = valeur

    url = reverse(
        "liste_objectif"
    )

    if filtres:

        url = (
            f"{url}?"
            f"{urlencode(filtres)}"
        )

    return redirect(
        url
    )


def periode_depuis_requete(request):
    """
    Valide le mois et l'annee recus depuis le formulaire.
    """

    try:

        mois = int(
            request.POST.get(
                "mois",
                ""
            )
        )

        annee = int(
            request.POST.get(
                "annee",
                ""
            )
        )

    except ValueError as exc:

        raise ValidationError(
            "Veuillez selectionner un mois et une annee valides."
        ) from exc

    if mois < 1 or mois > 12:

        raise ValidationError(
            "Veuillez selectionner un mois valide."
        )

    return mois, annee


def libelle_periode(mois, annee):
    """
    Retourne le libelle lisible d'une periode.
    """

    return (
        f"{NOMS_MOIS.get(mois, mois)} "
        f"{annee}"
    )


def point_ventes_actualisation(request):
    """
    Retourne les points de vente concernes
    par l'actualisation demandee.
    """

    point_ventes = PointVente.objects.filter(
        actif=True
    )

    if request.user.profil.role == "GERANT":

        return point_ventes.filter(
            pk=request.user.profil.point_vente_id
        )

    point_vente = request.POST.get(
        "point_vente"
    )

    if point_vente:

        return point_ventes.filter(
            pk=point_vente
        )

    return point_ventes


# ==========================================================
# Liste
# ==========================================================

@login_required
def liste_objectif(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    designation = filtre_texte(
        request,
        "designation"
    )

    aujourd_hui = date.today()

    mois = request.GET.get(
        "mois",
        str(aujourd_hui.month)
    )

    annee = request.GET.get(
        "annee",
        str(aujourd_hui.year)
    )

    point_vente = request.GET.get(
        "point_vente"
    )

    objectifs = rechercher_objectifs(

        utilisateur=request.user,

        designation=designation,

        mois=mois,

        annee=annee,

        point_vente=point_vente

    )

    page = paginer(

        objectifs,

        request.GET.get("page")

    )

    context = {

        "objectifs": page,

        "designation": designation,

        "mois": mois,

        "annee": annee,

        "point_ventes": PointVente.objects.filter(
            actif=True
        ).order_by(
            "designation"
        ),

        "point_vente_selectionne": point_vente,

        "mois_liste": [

            (1, "Janvier"),
            (2, "Février"),
            (3, "Mars"),
            (4, "Avril"),
            (5, "Mai"),
            (6, "Juin"),
            (7, "Juillet"),
            (8, "Août"),
            (9, "Septembre"),
            (10, "Octobre"),
            (11, "Novembre"),
            (12, "Décembre"),

        ]

    }

    return render(

        request,

        "objectif/liste.html",

        context

    )


# ==========================================================
# Actualisation
# ==========================================================

@login_required
def actualiser_objectifs_view(request):

    if request.method != "POST":

        return redirect(
            "liste_objectif"
        )

    if not peut_creer(
        request.user
    ):

        return HttpResponseForbidden()

    try:

        mois, annee = periode_depuis_requete(
            request
        )

    except ValidationError as e:

        messages.error(
            request,
            e.message
        )

        return redirection_liste_avec_filtres(
            request
        )

    point_vente = request.POST.get(
        "point_vente"
    )

    objectifs = rechercher_objectifs(

        utilisateur=request.user,

        mois=mois,

        annee=annee,

        point_vente=point_vente

    )

    commandes_existantes = existe_commandes_periode(
        mois,
        annee,
        point_ventes_actualisation(
            request
        )
    )

    nombre = recalculer_objectifs(
        objectifs
    )

    if not commandes_existantes:

        messages.warning(
            request,
            (
                "Il n'y a pas eu de commandes durant "
                f" {libelle_periode(mois, annee)}."
            )
        )

    elif nombre == 0:

        messages.warning(
            request,
            (
                "Aucun objectif à actualiser pour "
                f"{libelle_periode(mois, annee)}."
            )
        )

    else:

        messages.success(
            request,
            f"{nombre} objectif(s) actualisé(s)."
        )

    return redirection_liste_avec_filtres(
        request
    )


# ==========================================================
# Ajout
# ==========================================================

@login_required
def ajouter_objectif(request):

    if not peut_creer(request.user):
        return HttpResponseForbidden()

    form = ObjectifForm(request.POST or None)

    if request.method == "POST":

        if request.POST.get("action") == "charger":

            return render(
                request,
                "objectif/form.html",
                {
                    "form": form,
                    "titre": "Nouvel objectif"
                }
            )

        # Si les produits ne sont pas encore sélectionnés,
        # le formulaire est simplement réaffiché avec
        # les produits de la compagnie.

        if form.is_valid():

            try:

                creer_objectif(
                    request.user,
                    form.cleaned_data
                )

                messages.success(
                    request,
                    "Objectif enregistré avec succès."
                )

                return redirect("liste_objectif")

            except ValidationError as e:

                form.add_error(None, e)

            except Exception as e:

                messages.error(
                    request,
                    str(e)
                )

    return render(

        request,

        "objectif/form.html",

        {

            "form": form,

            "titre": "Nouvel objectif"

        }

    )


# ==========================================================
# Modification
# ==========================================================

@login_required
def modifier_objectif_view(request, pk):

    objectif = objectif_par_id(
        request.user,
        pk
    )

    if not peut_modifier(
        request.user,
        objectif
    ):

        return HttpResponseForbidden()

    if request.method == "POST":

        if request.POST.get("action") == "charger":

            return render(
                request,
                "objectif/form.html",
                {
                    "form": form,
                    "titre": "Nouvel objectif"
                }
            )

        form = ObjectifForm(
            request.POST
        )

        if form.is_valid():

            try:

                modifier_objectif(

                    objectif,

                    form.cleaned_data

                )

                messages.success(

                    request,

                    "Objectif modifié."

                )

                return redirect(
                    "liste_objectif"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e
                )

            except Exception as e:

                messages.error(

                    request,

                    f"Erreur : {e}"

                )

    else:

        initial = {

            "compagnie": objectif.compagnie_id,

            "mois": objectif.mois,

            "annee": objectif.annee,

            "montant_cible": objectif.montant_cible,

            "produits": list(

                objectif.lignes.values_list(

                    "produit_id",

                    flat=True

                )

            )

        }

        form = ObjectifForm(
            initial=initial
        )

        form.fields["produits"].queryset = (
            objectif.compagnie.produits.filter(
                actif=True
            ).order_by("designation")
        )                                                                              

    return render(

        request,

        "objectif/form.html",

        {

            "form": form,

            "titre": "Modifier l'objectif"

        }

    )


# ==========================================================
# Suppression
# ==========================================================

@login_required
def supprimer_objectif_view(request, pk):

    objectif = objectif_par_id(
        request.user,
        pk
    )

    if not peut_supprimer(
        request.user,
        objectif
    ):

        return HttpResponseForbidden()

    if request.method == "POST":

        supprimer_objectif(
            objectif
        )

        messages.success(

            request,

            "Objectif supprimé."

        )

        return redirect(
            "liste_objectif"
        )

    return render(

        request,

        "objectif/confirm_delete.html",

        {

            "objectif": objectif

        }

    )
