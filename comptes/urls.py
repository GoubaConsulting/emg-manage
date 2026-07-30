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

]