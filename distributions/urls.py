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
        "gerant/ajouter/",
        views.ajouter_distribution,
        name="ajouter_distribution",
    ),

    path(
        "directeur/ajouter/",
        views.ajouter_distribution_directeur,
        name="ajouter_distribution_directeur",
    ),
    path(
        "modifier/<int:pk>/",
        views.modifier_distribution_view,
        name="modifier_distribution",
    ),
    path(
        "correction-apercu/<int:pk>/",
        views.modifier_distribution_view,
        {"correction_apercu": True},
        name="corriger_distribution_apercu",
    ),
    path(
        "directeur/distributeur/ajouter/",
        views.ajouter_distribution_directeur_distributeur,
        name="ajouter_distribution_directeur_distributeur",
    ),
    path(
        "directeur/client/ajouter/",
        views.ajouter_distribution_directeur_client,
        name="ajouter_distribution_directeur_client",
    ),
    path(
        "gerant/client/ajouter/",
        views.ajouter_distribution_client,
        name="ajouter_distribution_client",
    ),

]
