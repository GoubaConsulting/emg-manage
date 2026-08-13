from django.contrib import admin
from django.urls import path, include
from django.urls import (
    include,
    path,
)


urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "",
        include("comptes.urls")
    ),

    path(
        "",
        include("referentiel.urls")
    ),

    path(
        "objectifs/",
        include("objectif.urls")
    ),

    path(
        "commandes/",
        include("commandes.urls")
    ),

    path(

        "stocks/",

        include("stocks.urls")

    ),

    path(

        "distributions/",
        
        include("distributions.urls"),
    ),

    path(
        "situations/",
        include("situations.urls"),
    ),

]