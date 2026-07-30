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
    supprimer_objectif
)


# ==========================================================
# Liste
# ==========================================================

@login_required
def liste_objectif(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    designation = request.GET.get(
        "designation"
    )

    mois = request.GET.get(
        "mois"
    )

    annee = request.GET.get(
        "annee"
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