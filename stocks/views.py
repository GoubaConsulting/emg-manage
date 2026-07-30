"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Vues du module Stocks.

==========================================================
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from .permissions import peut_consulter
from .selectors import (
    stocks_point_vente,
    paginer
)


@login_required
def liste_stock(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    stocks = stocks_point_vente(

        request.user.profil.point_vente

    )

    page = paginer(

        stocks,

        request.GET.get("page")

    )

    return render(

        request,

        "stocks/liste.html",

        {

            "stocks": page

        }

    )