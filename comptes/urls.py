from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [

    path(
        "",
        RedirectView.as_view(pattern_name="login", permanent=False),
    ),

    path(
        "login/",
        views.connexion,
        name="login"
    ),

    path(
        "logout/",
        views.deconnexion,
        name="logout"
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "apercu/",
        views.apercu_directeur,
        name="apercu_directeur"
    ),

    path(
        "operations-gerants/",
        views.operations_gerant_directeur,
        name="operations_gerant_directeur"
    ),

    path(
        "mes-operations/",
        RedirectView.as_view(pattern_name="dashboard", permanent=False),
        name="mes_operations_redirect"
    ),

    path("notifications-corrections/", views.notifications_corrections,
         name="notifications_corrections"),
    path("notifications-corrections/<int:pk>/ouvrir/",
         views.ouvrir_notification_correction,
         name="ouvrir_notification_correction"),

]
