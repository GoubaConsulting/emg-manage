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
from .permissions import peut_consulter
from .selectors import (
    stocks_point_vente,
    paginer
)
from .services import valoriser_stocks


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

    stocks_valorises = valoriser_stocks(

        page.object_list

    )

    page.object_list = stocks_valorises

    stocks_tries = sorted(

        stocks_valorises,

        key=lambda stock: (
            stock.produit.compagnie.designation,
            stock.produit.designation,
        )

    )

    groupes_compagnies = []

    total_general = {

        "quantite": sum(
            (
                stock.quantite
                for stock in stocks_tries
            ),
            Decimal("0.00")
        ),

        "montant_brut": sum(
            (
                stock.montant_brut
                for stock in stocks_tries
            ),
            Decimal("0.00")
        ),

        "montant_net": sum(
            (
                stock.montant_net
                for stock in stocks_tries
            ),
            Decimal("0.00")
        ),

    }

    for compagnie, lignes in groupby(

        stocks_tries,

        key=lambda stock: stock.produit.compagnie

    ):

        lignes = list(lignes)

        totaux = {

            "quantite": sum(
                (
                    stock.quantite
                    for stock in lignes
                )
            ),

            "montant_brut": sum(
                (
                    stock.montant_brut
                    for stock in lignes
                )
            ),

            "montant_net": sum(
                (
                    stock.montant_net
                    for stock in lignes
                )
            ),

        }

        groupes_compagnies.append({

            "compagnie": compagnie,

            "stocks": lignes,

            "totaux": totaux,

        })

    return render(

        request,

        "stocks/liste.html",

        {
            "stocks": page,

            "groupes_compagnies": groupes_compagnies,

            "total_general": total_general,

            "est_directeur": est_directeur,

            "type_stock": type_stock,
        }

    )
