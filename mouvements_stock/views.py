"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Vues du module.

==========================================================
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import (
    redirect,
    render,
)

from stocks.models import (
    TYPE_NORMAL,
    TYPE_TAMPON,
    TYPES_STOCK,
)

from .forms import MouvementStockForm
from .models import MouvementStock
from .permissions import (
    peut_consulter,
    peut_creer,
)
from .selectors import (
    mouvements_visibles,
    paginer,
    produits_actifs,
    stock_par_produit,
)
from .services import (
    construire_lignes_depuis_formulaire,
    creer_mouvement_stock,
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
    Retourne les bornes de dates. Par defaut,
    l'intervalle couvre le mois courant.
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


def _preparer_groupes_lignes(mouvements_page):
    """
    Regroupe les lignes de chaque mouvement par compagnie.
    """

    for mouvement in mouvements_page:

        lignes = sorted(
            mouvement.lignes.all(),
            key=lambda ligne: (
                ligne.produit.compagnie.designation,
                ligne.produit.designation,
            )
        )

        groupes = []

        for compagnie, lignes_compagnie in groupby(
            lignes,
            key=lambda ligne: ligne.produit.compagnie
        ):

            lignes_compagnie = list(
                lignes_compagnie
            )

            groupes.append({
                "compagnie": compagnie,
                "lignes": lignes_compagnie,
                "total_quantite": sum(
                    (
                        ligne.quantite
                        for ligne in lignes_compagnie
                    ),
                    Decimal("0.00")
                ),
            })

        mouvement.groupes_compagnies = groupes


def _produits_formulaire(point_vente):
    """
    Prepare les produits avec les stocks visibles dans le formulaire.
    """

    stocks = stock_par_produit(
        point_vente
    )

    produits = list(
        produits_actifs()
    )

    for produit in produits:

        donnees_stock = stocks.get(
            produit.pk,
            {}
        )

        produit.stock_normal = donnees_stock.get(
            TYPE_NORMAL,
            Decimal("0.00")
        )

        produit.stock_tampon = donnees_stock.get(
            TYPE_TAMPON,
            Decimal("0.00")
        )

    groupes = []

    for compagnie, produits_compagnie in groupby(
        produits,
        key=lambda produit: produit.compagnie
    ):

        groupes.append({
            "compagnie": compagnie,
            "produits": list(
                produits_compagnie
            ),
        })

    return groupes


@login_required
def liste_mouvements(request):
    """
    Liste des entrees et sorties de stock.
    """

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    numero = _filtre_texte(
        request,
        "numero"
    )

    type_mouvement = request.GET.get(
        "type_mouvement",
        ""
    )

    type_stock = request.GET.get(
        "type_stock",
        ""
    )

    produit = request.GET.get(
        "produit",
        ""
    )

    date_debut, date_fin = _filtres_dates(
        request
    )

    mouvements = mouvements_visibles(
        request.user
    )

    if numero:

        mouvements = mouvements.filter(
            numero__icontains=numero
        )

    if type_mouvement:

        mouvements = mouvements.filter(
            type_mouvement=type_mouvement
        )

    if type_stock:

        mouvements = mouvements.filter(
            type_stock=type_stock
        )

    if date_debut:

        mouvements = mouvements.filter(
            date_mouvement__gte=date_debut
        )

    if date_fin:

        mouvements = mouvements.filter(
            date_mouvement__lte=date_fin
        )

    if produit:

        mouvements = mouvements.filter(
            lignes__produit_id=produit
        ).distinct()

    mouvements = mouvements.order_by(
        "-date_mouvement",
        "-idmouvementstock"
    )

    total_entrees = (
        mouvements
        .filter(
            type_mouvement=MouvementStock.TYPE_ENTREE
        )
        .aggregate(
            total=Sum("total_quantite")
        )["total"]
        or
        Decimal("0.00")
    )

    total_sorties = (
        mouvements
        .filter(
            type_mouvement=MouvementStock.TYPE_SORTIE
        )
        .aggregate(
            total=Sum("total_quantite")
        )["total"]
        or
        Decimal("0.00")
    )

    page = paginer(
        mouvements,
        request.GET.get(
            "page"
        )
    )

    _preparer_groupes_lignes(
        page
    )

    return render(
        request,
        "mouvements_stock/liste.html",
        {
            "mouvements": page,
            "numero": numero,
            "type_mouvement": type_mouvement,
            "type_stock": type_stock,
            "produit_selectionne": produit,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "types_mouvement": MouvementStock.TYPES_MOUVEMENT,
            "types_stock": TYPES_STOCK,
            "produits": produits_actifs(),
            "pagination_querystring": (
                _querystring_pagination(
                    request
                )
            ),
            "total_entrees": total_entrees,
            "total_sorties": total_sorties,
            "peut_creer": peut_creer(
                request.user
            ),
        }
    )


@login_required
def ajouter_mouvement(request):
    """
    Creation d'une entree ou sortie de stock.
    """

    if not peut_creer(request.user):

        return HttpResponseForbidden()

    point_vente = request.user.profil.point_vente

    if request.method == "POST":

        form = MouvementStockForm(
            request.POST
        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(
                    request.POST
                )

                creer_mouvement_stock(
                    utilisateur=request.user,
                    type_mouvement=form.cleaned_data[
                        "type_mouvement"
                    ],
                    type_stock=form.cleaned_data[
                        "type_stock"
                    ],
                    date_mouvement=form.cleaned_data[
                        "date_mouvement"
                    ],
                    motif=form.cleaned_data[
                        "motif"
                    ],
                    observation=form.cleaned_data[
                        "observation"
                    ],
                    lignes=lignes,
                )

                messages.success(
                    request,
                    "Mouvement de stock enregistre avec succes."
                )

                return redirect(
                    "mouvements_stock:liste_mouvements"
                )

            except Exception as e:

                form.add_error(
                    None,
                    str(e)
                )

    else:

        form = MouvementStockForm()

    return render(
        request,
        "mouvements_stock/form.html",
        {
            "form": form,
            "point_vente": point_vente,
            "groupes_compagnies": _produits_formulaire(
                point_vente
            ),
        }
    )
