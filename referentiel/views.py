from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from uuid import uuid4
from itertools import groupby

from .models import PointVente
from .forms import PointVenteForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Compagnie
from .forms import CompagnieForm
from .models import Produit
from .forms import ProduitForm
from .models import Distributeur
from .forms import DistributeurForm
from .services import distributeurs_visibles


def generer_code_provisoire_distributeur():
    """
    Genere un code temporaire unique avant l'obtention
    de l'identifiant auto-incremente du distributeur.
    """

    while True:

        code = f"TMP{uuid4().hex[:17].upper()}"

        if not Distributeur.objects.filter(
            code=code
        ).exists():

            return code


def generer_code_distributeur(distributeur):
    """
    Genere le code final d'un distributeur.
    """

    code_point_vente = (
        distributeur.point_vente.designation[:3].upper()
    )

    return (
        f"DIST"
        f"{distributeur.iddistributeur:03d}"
        f"{code_point_vente}"
    )


# ==========================================
# POINT DE VENTES
# ==========================================

@login_required
def liste_pointvente(request):

    recherche = request.GET.get(
        'recherche',
        ''
    )

    pointventes = PointVente.objects.filter(
        actif=True
    )

    if recherche:

        pointventes = pointventes.filter(

            Q(designation__icontains=recherche) |
            Q(adresse__icontains=recherche)

        )

    pointventes = pointventes.order_by(
    'designation'
    )

    taille_page = max(
        pointventes.count(),
        1
    )

    paginator = Paginator(
        pointventes,
        taille_page
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {

        'page_obj': page_obj,
        'recherche': recherche,
        'titre': 'Points de vente',
        'corbeille': False,
        'message_vide': 'Aucun point de vente actif trouvé.'

    }

    return render(
        request,
        'referentiel/pointvente/liste.html',
        context
    )

@login_required
def ajouter_pointvente(request):

    form = PointVenteForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Point de vente enregistré avec succès."
        )

        return redirect(
            'liste_pointvente'
        )

    context = {
        'form': form
    }

    return render(
        request,
        'referentiel/pointvente/form.html',
        context
    )

@login_required
def modifier_pointvente(
    request,
    pk
):

    pointvente = get_object_or_404(
        PointVente,
        pk=pk
    )

    form = PointVenteForm(
        request.POST or None,
        instance=pointvente
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Point de vente modifié avec succès."
        )

        return redirect(
            'liste_pointvente'
        )

    context = {
        'form': form
    }

    return render(
        request,
        'referentiel/pointvente/form.html',
        context
    )

@login_required
def supprimer_pointvente(request, pk):

    pointvente = get_object_or_404(
        PointVente,
        actif=True,
        pk=pk
    )

    if request.method == 'POST':
        # Suppression logique (désactivation)
        pointvente.actif = False
        pointvente.save()

        messages.success(
            request,
            "Point de vente supprimé avec succès."
        )

        return redirect(
            'liste_pointvente'
        )

    context = {
        'pointvente': pointvente
    }

    return render(
        request,
        'referentiel/pointvente/confirmation_suppression.html',
        context
    )


@login_required
def corbeille_pointvente(request):

    recherche = request.GET.get(
        'recherche',
        ''
    )

    pointventes = PointVente.objects.filter(
        actif=False
    )

    if recherche:

        pointventes = pointventes.filter(

            Q(designation__icontains=recherche) |
            Q(adresse__icontains=recherche)

        )

    pointventes = pointventes.order_by(
    'designation'
    )

    taille_page = max(
        pointventes.count(),
        1
    )

    paginator = Paginator(
        pointventes,
        taille_page
    )

    page_obj = paginator.get_page(
        request.GET.get(
            'page'
        )
    )

    context = {

        'page_obj': page_obj,
        'recherche': recherche,
        'titre': 'Corbeille des points de vente',
        'corbeille': True,
        'message_vide': 'Aucun point de vente supprimé trouvé.'

    }

    return render(
        request,
        'referentiel/pointvente/liste.html',
        context
    )


@login_required
def reactiver_pointvente(request, pk):

    pointvente = get_object_or_404(
        PointVente,
        actif=False,
        pk=pk
    )

    if request.method == 'POST':

        pointvente.actif = True

        pointvente.save(
            update_fields=[
                'actif',
                'date_modification'
            ]
        )

        messages.success(
            request,
            "Point de vente réactivé avec succès."
        )

    return redirect(
        'corbeille_pointvente'
    )


# ==========================================
# COMPAGNIES
# ==========================================

@login_required
def liste_compagnie(request):
    """
    Liste des compagnies
    Recherche + pagination
    """

    recherche = request.GET.get(
        'recherche',
        ''
    )

    compagnies = Compagnie.objects.filter(
        actif=True
    )

    if recherche:

        compagnies = compagnies.filter(
            designation__icontains=recherche
        )

    compagnies = compagnies.order_by(
        'designation'
    )

    paginator = Paginator(
        compagnies,
        10
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {

        'page_obj': page_obj,
        'recherche': recherche

    }

    return render(
        request,
        'referentiel/compagnie/liste.html',
        context
    )


@login_required
def ajouter_compagnie(request):
    """
    Ajout d'une compagnie
    """

    if request.method == 'POST':

        form = CompagnieForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Compagnie enregistrée avec succès."
            )

            return redirect(
                'liste_compagnie'
            )

    else:

        form = CompagnieForm()

    context = {

        'form': form,
        'titre': 'Ajouter une compagnie'

    }

    return render(
        request,
        'referentiel/compagnie/form.html',
        context
    )


@login_required
def modifier_compagnie(request, pk):
    """
    Modification d'une compagnie
    """

    compagnie = get_object_or_404(
        Compagnie,
        pk=pk
    )

    if request.method == 'POST':

        form = CompagnieForm(
            request.POST,
            instance=compagnie
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Compagnie modifiée avec succès."
            )

            return redirect(
                'liste_compagnie'
            )

    else:

        form = CompagnieForm(
            instance=compagnie
        )

    context = {

        'form': form,
        'titre': 'Modifier une compagnie'

    }

    return render(
        request,
        'referentiel/compagnie/form.html',
        context
    )


@login_required
def supprimer_compagnie(request, pk):
    """
    Suppression logique
    """

    compagnie = get_object_or_404(
        Compagnie,
        pk=pk
    )

    if request.method == 'POST':

        compagnie.actif = False

        compagnie.save()

        messages.success(
            request,
            "Compagnie supprimée avec succès."
        )

        return redirect(
            'liste_compagnie'
        )

    context = {

        'compagnie': compagnie

    }

    return render(
        request,
        'referentiel/compagnie/confirmation_suppression.html',
        context
    )


# ==========================================
# PRODUITS
# ==========================================

@login_required
def liste_produit(request):
    """
    Liste des produits
    Recherche par produit ou compagnie
    """

    recherche = request.GET.get(
        'recherche',
        ''
    )

    produits = (
        Produit.objects
        .filter(
            actif=True
        )
        .select_related(
            'compagnie'
        )
    )

    if recherche:

        produits = produits.filter(

            Q(designation__icontains=recherche) |
            Q(compagnie__designation__icontains=recherche)

        )

    produits = produits.order_by(
        'compagnie__designation',
        'designation'
    )

    paginator = Paginator(
        produits,
        10
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    produits_page = list(
        page_obj.object_list
    )

    for index, produit in enumerate(
        produits_page,
        start=page_obj.start_index()
    ):

        produit.rang = index

    groupes_produits = []

    for compagnie, produits_compagnie in groupby(
        produits_page,
        key=lambda produit: produit.compagnie
    ):

        groupes_produits.append({

            'compagnie': compagnie,
            'produits': list(
                produits_compagnie
            )

        })

    context = {

        'page_obj': page_obj,
        'groupes_produits': groupes_produits,
        'recherche': recherche

    }

    return render(
        request,
        'referentiel/produit/liste.html',
        context
    )


@login_required
def ajouter_produit(request):
    """
    Ajout d'un produit
    """

    if request.method == 'POST':

        form = ProduitForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Produit enregistré avec succès."
            )

            return redirect(
                'liste_produit'
            )

    else:

        form = ProduitForm()

    context = {

        'form': form,
        'titre': 'Ajouter un produit'

    }

    return render(
        request,
        'referentiel/produit/form.html',
        context
    )


@login_required
def modifier_produit(request, pk):
    """
    Modification d'un produit
    """

    produit = get_object_or_404(
        Produit,
        pk=pk
    )

    if request.method == 'POST':

        form = ProduitForm(
            request.POST,
            instance=produit
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Produit modifié avec succès."
            )

            return redirect(
                'liste_produit'
            )

    else:

        form = ProduitForm(
            instance=produit
        )

    context = {

        'form': form,
        'titre': 'Modifier un produit'

    }

    return render(
        request,
        'referentiel/produit/form.html',
        context
    )


@login_required
def supprimer_produit(request, pk):
    """
    Suppression logique
    """

    produit = get_object_or_404(
        Produit,
        pk=pk
    )

    if request.method == 'POST':

        produit.actif = False

        produit.save()

        messages.success(
            request,
            "Produit supprimé avec succès."
        )

        return redirect(
            'liste_produit'
        )

    context = {

        'produit': produit

    }

    return render(
        request,
        'referentiel/produit/confirmation_suppression.html',
        context
    )

# ==========================================
# DISTRIBUTEURS
# ==========================================

def filtrer_distributeurs(
    distributeurs,
    recherche
):

    if not recherche:

        return distributeurs

    return distributeurs.filter(

        Q(code__icontains=recherche) |
        Q(nom__icontains=recherche) |
        Q(prenom__icontains=recherche) |
        Q(point_vente__designation__icontains=recherche)

    )


def paginer_distributeurs(
    distributeurs,
    page_number
):

    paginator = Paginator(
        distributeurs.order_by(
            'nom',
            'prenom'
        ),
        10
    )

    return paginator.get_page(
        page_number
    )


@login_required
def liste_distributeur(request):

    recherche = request.GET.get(
        'recherche',
        ''
    )

    distributeurs = distributeurs_visibles(
        request.user
    )

    distributeurs = filtrer_distributeurs(
        distributeurs,
        recherche
    )

    page_obj = paginer_distributeurs(
        distributeurs,
        request.GET.get(
            'page'
        )
    )

    return render(
        request,
        'referentiel/distributeur/liste.html',
        {
            'page_obj': page_obj,
            'recherche': recherche,
            'titre': 'Distributeurs et gérants',
            'corbeille': False,
            'message_vide': 'Aucun distributeur ou gérant actif trouvé.'
        }
    )


@login_required
def corbeille_distributeur(request):

    recherche = request.GET.get(
        'recherche',
        ''
    )

    distributeurs = distributeurs_visibles(
        request.user,
        actif=False
    )

    distributeurs = filtrer_distributeurs(
        distributeurs,
        recherche
    )

    page_obj = paginer_distributeurs(
        distributeurs,
        request.GET.get(
            'page'
        )
    )

    return render(
        request,
        'referentiel/distributeur/liste.html',
        {
            'page_obj': page_obj,
            'recherche': recherche,
            'titre': 'Corbeille des distributeurs et gérants',
            'corbeille': True,
            'message_vide': (
                'Aucun distributeur ou gérant supprimé trouvé.'
            )
        }
    )


@login_required
def ajouter_distributeur(request):

    if request.method == 'POST':

        form = DistributeurForm(
            request.POST
        )

        if form.is_valid():

            with transaction.atomic():

                distributeur = form.save(commit=False)

                distributeur.code = generer_code_provisoire_distributeur()

                distributeur.save()

                distributeur.code = generer_code_distributeur(
                    distributeur
                )

                distributeur.save(
                    update_fields=["code"]
                )

            messages.success(
                request,
                "Distributeur enregistré avec succès."
            )

            return redirect(
                'liste_distributeur'
            )

    else:

        form = DistributeurForm()

    return render(
        request,
        'referentiel/distributeur/form.html',
        {
            'form': form,
            'titre': 'Ajouter un distributeur'
        }
    )


@login_required
def modifier_distributeur(request, pk):

    distributeur = get_object_or_404(
        Distributeur,
        pk=pk
    )

    if request.method == 'POST':

        form = DistributeurForm(
            request.POST,
            instance=distributeur
        )

        if form.is_valid():

            distributeur = form.save()

            distributeur.code = generer_code_distributeur(
                distributeur
            )

            distributeur.save(
                update_fields=["code"]
            )

            messages.success(
                request,
                "Distributeur enregistré avec succès."
            )

            return redirect(
                'liste_distributeur'
            )

    else:

        form = DistributeurForm(
            instance=distributeur
        )

    return render(
        request,
        'referentiel/distributeur/form.html',
        {
            'form': form,
            'titre': 'Modifier un distributeur'
        }
    )


@login_required
def supprimer_distributeur(request, pk):

    distributeur = get_object_or_404(
        distributeurs_visibles(
            request.user
        ),
        pk=pk
    )

    if request.method == 'POST':

        distributeur.actif = False

        distributeur.save()

        messages.success(
            request,
            "Distributeur supprimé avec succès."
        )

        return redirect(
            'liste_distributeur'
        )

    return render(
        request,
        'referentiel/distributeur/confirmation_suppression.html',
        {
            'distributeur': distributeur
        }
    )


@login_required
def reactiver_distributeur(request, pk):

    distributeur = get_object_or_404(
        distributeurs_visibles(
            request.user,
            actif=False
        ),
        pk=pk
    )

    if request.method == 'POST':

        distributeur.actif = True

        distributeur.save(
            update_fields=[
                'actif',
                'date_modification'
            ]
        )

        messages.success(
            request,
            "Distributeur réactivé avec succès."
        )

    return redirect(
        'corbeille_distributeur'
    )
