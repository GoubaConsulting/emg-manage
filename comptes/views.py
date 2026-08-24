from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
)
from tableau_bord.services import (
    donnees_apercu_directeur,
    donnees_dashboard,
    donnees_operations_directeur_gerant,
)

def connexion(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    message = None

    if request.method == "POST":

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('dashboard')

        message = "Nom d'utilisateur ou mot de passe incorrect."

    return render(
        request,
        'comptes/login.html',
        {'message': message}
    )


def deconnexion(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):

    context = donnees_dashboard(
        request.user,
        request.GET.get("personne"),
        request.GET.get("date_debut"),
        request.GET.get("date_fin"),
    )

    return render(
        request,
        'comptes/dashboard.html',
        context
    )


@login_required
def apercu_directeur(request):

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    context = donnees_apercu_directeur(
        request.user,
        request.GET.get("gerant"),
        request.GET.get("date_debut"),
        request.GET.get("date_fin"),
    )

    return render(
        request,
        "comptes/apercu.html",
        context
    )


@login_required
def operations_gerant_directeur(request):

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    context = donnees_operations_directeur_gerant(
        request.user,
        request.GET.get("gerant"),
        request.GET.get("date_debut"),
        request.GET.get("date_fin"),
    )

    return render(
        request,
        "comptes/operations_gerant.html",
        context
    )
