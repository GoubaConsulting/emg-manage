"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Vues du module Stocks.

==========================================================
"""
from itertools import groupby
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import Stock
from .permissions import peut_consulter
from .selectors import (
    stocks_point_vente,
    paginer
)


@login_required
def liste_stock(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    profil = request.user.profil

    est_directeur = (
        profil.role == "DIRECTEUR"
    )

    type_stock = request.GET.get(
        "type_stock",
        ""
    )

    stocks = stocks_point_vente(

        point_vente=profil.point_vente,

        type_stock=type_stock if est_directeur else None,

    )

    profil = request.user.profil

    est_directeur = (
        profil.role == "DIRECTEUR"
    )

    type_stock = request.GET.get(
        "type_stock",
        ""
    )

    page = paginer(

        stocks,

        request.GET.get("page")

    )

    # ==========================================================
    # Préparation des groupes par compagnie
    # ==========================================================

    stocks_tries = sorted(

        page.object_list,

        key=lambda stock: (
            stock.produit.compagnie.designation,
            stock.produit.designation,
        )

    )

    groupes_compagnies = []

    for compagnie, lignes in groupby(

        stocks_tries,

        key=lambda stock: stock.produit.compagnie

    ):

        lignes = list(lignes)

        groupes_compagnies.append({

            "compagnie": compagnie,

            "stocks": lignes,

        })

    return render(

        request,

        "stocks/liste.html",

        {
            "stocks": page,

            "groupes_compagnies": groupes_compagnies,

            "est_directeur": est_directeur,

            "type_stock": type_stock,
        }

    )