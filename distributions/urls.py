from django.urls import path

from . import views

app_name = "distributions"

urlpatterns = [

    path(
        "",
        views.liste_distributions,
        name="liste_distributions",
    ),

    path(
        "ajouter/",
        views.ajouter_distribution,
        name="ajouter_distribution",
    ),

    path(
        "directeur/ajouter/",
        views.ajouter_distribution_directeur,
        name="ajouter_distribution_directeur",
    ),

]
