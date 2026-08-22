"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Vues du module Commandes.

==========================================================
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import (
    render,
    redirect
)

from referentiel.models import (
    Produit,
    Distributeur

)
from .forms import CommandeForm

from .permissions import (
    peut_consulter,
    peut_creer,
    peut_modifier
)

from .selectors import (
    rechercher_commandes,
    paginer,
    commande_par_id,
    commande_gerant_en_attente_par_id,
    commandes_en_attente,
)

from .services import (
    creer_commande,
    modifier_commande,
    construire_lignes_depuis_formulaire,
    creer_commande_stock_tampon,
    creer_commande_caution,
    creer_reglement_stock_tampon,
    modifier_commande_stock_tampon,
    modifier_commande_caution,
    modifier_reglement_stock_tampon,
    valider_commande_gerant,
    rejeter_commande_gerant,
    
)

from .presentation import (
    preparer_affichage_commande,
)

from django.shortcuts import get_object_or_404

from .models import Commande
from .presentation import preparer_affichage_commande
from decimal import Decimal
from calendar import monthrange
from datetime import date

from .services import valider_commande_directeur_service

type_commande=Commande.TYPE_DIRECTEUR,


# ==========================================================
# FILTRES DE DATES
# ==========================================================

def filtres_dates_recherche(
    request,
    champ_date
):
    """
    Retourne une date exacte ou un intervalle.
    Par defaut, l'intervalle couvre le mois courant.
    """

    date_exacte = request.GET.get(
        champ_date,
        ""
    )

    date_debut = request.GET.get(
        "date_debut",
        ""
    )

    date_fin = request.GET.get(
        "date_fin",
        ""
    )

    if date_debut or date_fin:

        date_exacte = ""

    if not date_exacte and not date_debut and not date_fin:

        aujourd_hui = date.today()

        date_debut = aujourd_hui.replace(
            day=1
        ).isoformat()

        date_fin = aujourd_hui.replace(
            day=monthrange(
                aujourd_hui.year,
                aujourd_hui.month
            )[1]
        ).isoformat()

    return (
        date_exacte,
        date_debut,
        date_fin,
    )


def querystring_pagination(request):
    """
    Conserve les filtres lors du changement de page.
    """

    params = request.GET.copy()

    params.pop(
        "page",
        None
    )

    return params.urlencode()


def filtre_texte(request, nom):
    """
    Retourne un filtre texte propre pour l'affichage.
    """

    valeur = str(
        request.GET.get(
            nom,
            ""
        )
        or
        ""
    ).strip()

    if valeur.lower() == "none":

        return ""

    return valeur


# ==========================================================
# PRODUITS ACTIFS
# ==========================================================

def produits_actifs():
    """
    Retourne la liste des produits actifs
    classés par compagnie puis désignation.
    """

    return (

        Produit.objects

        .filter(
            actif=True
        )

        .select_related(
            "compagnie"
        )

        .order_by(
            "compagnie__designation",
            "designation"
        )

    )


# ==========================================================
# LISTE DES COMMANDES
# ==========================================================

@login_required
def liste_commandes(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    numero = filtre_texte(
        request,
        "numero"
    )

    etat = filtre_texte(
        request,
        "etat"
    )

    if etat not in dict(
        Commande.ETATS
    ):

        etat = ""

    (
        date_commande,
        date_debut,
        date_fin,
    ) = filtres_dates_recherche(
        request,
        "date_commande"
    )

    commandes = rechercher_commandes(

        utilisateur=request.user,

        categorie_commande=Commande.CATEGORIE_NORMALE,

        numero=numero,

        date_commande=date_commande,

        date_debut=date_debut,

        date_fin=date_fin,

        etat=etat

    )

    
    page = paginer(

        commandes,

        request.GET.get("page")

    )

    

    total_brut = Decimal("0")

    total_net = Decimal("0")

    for commande in page:

        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

        total_brut += commande.montant_brut

        total_net += commande.montant_net

    return render(

        request,

        "commandes/liste.html",

        {

            "commandes": page,

            "numero": numero,

            "date_commande": date_commande,

            "date_debut": date_debut,

            "date_fin": date_fin,

            "etat": etat,

            "etats_commande": Commande.ETATS,

            "afficher_filtre_etat": True,

            "pagination_querystring": querystring_pagination(request),

            "titre": "Commandes normales",

            "url_nouveau": "ajouter_commande",

            "url_modifier": "modifier_commande",

            "total_brut": total_brut,

            "total_net": total_net,

        }

    )



# ==========================================================
# LISTE DES COMMANDES STOCK TAMPON
# ==========================================================

@login_required
def liste_commandes_stock_tampon(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    numero = filtre_texte(
        request,
        "numero"
    )

    (
        date_commande,
        date_debut,
        date_fin,
    ) = filtres_dates_recherche(
        request,
        "date_commande"
    )

    commandes = rechercher_commandes(

        utilisateur=request.user,

        categorie_commande=Commande.CATEGORIE_STOCK_TAMPON,

        numero=numero,

        date_commande=date_commande,

        date_debut=date_debut,

        date_fin=date_fin

    )

    page = paginer(

        commandes,

        request.GET.get("page")

    )


    total_brut = Decimal("0")

    total_net = Decimal("0")

    for commande in page:

        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

        total_brut += commande.montant_brut

        total_net += commande.montant_net

    return render(

        request,

        "commandes/liste_stock_tampon.html",

        {

            "commandes": page,

            "numero": numero,

            "date_commande": date_commande,

            "date_debut": date_debut,

            "date_fin": date_fin,

            "pagination_querystring": querystring_pagination(request),

            "titre": "Commandes Stock Tampon",

            "url_nouveau": "ajouter_commande_stock_tampon",

            "url_modifier": "modifier_commande_stock_tampon",

            "total_brut": total_brut,

            "total_net": total_net

        }

    )


# ==========================================================
# LISTE DES REGLEMENTS STOCK TAMPON
# ==========================================================

@login_required
def liste_reglement_stock(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    numero = filtre_texte(
        request,
        "numero"
    )

    (
        date_commande,
        date_debut,
        date_fin,
    ) = filtres_dates_recherche(
        request,
        "date_commande"
    )

    commandes = rechercher_commandes(

        utilisateur=request.user,

        categorie_commande=Commande.CATEGORIE_REGLEMENT_STOCK,

        numero=numero,

        date_commande=date_commande,

        date_debut=date_debut,

        date_fin=date_fin

    )

    page = paginer(

        commandes,

        request.GET.get("page")

    )


    total_brut = Decimal("0")

    total_net = Decimal("0")

    for commande in page:

        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

        total_brut += commande.montant_brut

        total_net += commande.montant_net

    return render(

        request,

        "commandes/liste.html",

        {

            "commandes": page,

            "numero": numero,

            "date_commande": date_commande,

            "titre": "Règlement Stock Tampon",

            "date_debut": date_debut,

            "date_fin": date_fin,

            "pagination_querystring": querystring_pagination(request),

            "url_nouveau": "ajouter_reglement_stock",

            "url_retour": "liste_reglement_stock",

            "url_modifier": "modifier_reglement_stock_tampon",

            "total_brut": total_brut,

            "total_net": total_net

        }

    )


# ==========================================================
# LISTE DES COMMANDES CAUTION
# ==========================================================

@login_required
def liste_commandes_caution(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    numero = filtre_texte(
        request,
        "numero"
    )

    (
        date_commande,
        date_debut,
        date_fin,
    ) = filtres_dates_recherche(
        request,
        "date_commande"
    )

    commandes = rechercher_commandes(

        utilisateur=request.user,

        categorie_commande=Commande.CATEGORIE_CAUTION,

        numero=numero,

        date_commande=date_commande,

        date_debut=date_debut,

        date_fin=date_fin

    )

    page = paginer(

        commandes,

        request.GET.get("page")

    )


    total_brut = Decimal("0")

    total_net = Decimal("0")

    for commande in page:

        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

        total_brut += commande.montant_brut

        total_net += commande.montant_net

    return render(

        request,

        "commandes/liste.html",

        {

            "commandes": page,

            "numero": numero,

            "date_commande": date_commande,

            "titre": "Commandes Caution Bancaire",

            "date_debut": date_debut,

            "date_fin": date_fin,

            "pagination_querystring": querystring_pagination(request),

            "url_nouveau": "ajouter_commande_caution",

            "url_modifier": "modifier_commande_caution",

            "total_brut": total_brut,

            "total_net": total_net

        }

    )


# ==========================================================
# AJOUT DIRECTEUR
# ==========================================================

@login_required
def ajouter_commande(request):

    if not peut_creer(request.user):

        return HttpResponseForbidden()

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                creer_commande(

                    utilisateur=request.user,

                    type_commande=Commande.TYPE_DIRECTEUR,

                    categorie_commande=Commande.CATEGORIE_NORMALE,

                    date_commande=form.cleaned_data["date_commande"],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande enregistrée avec succès."

                )

                return redirect(

                    "liste_commandes"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm()

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "produits": produits,

            "titre": "Nouvelle commande Directeur",

            "url_retour": "liste_commandes",

        }

    )


# ==========================================================
# AJOUT DIRECTEUR STOCK TAMPON
# ==========================================================

@login_required
def ajouter_commande_stock_tampon(request):

    if not peut_creer(request.user):

        return HttpResponseForbidden()

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                creer_commande_stock_tampon(

                    utilisateur=request.user,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande enregistrée avec succès."

                )

                return redirect(

                    "liste_commandes"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm()

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "produits": produits,

            "titre": "Commande Stock Tampon",

            "url_retour": "liste_commandes_stock_tampon",

        }

    )



# ==========================================================
# AJOUT REGLEMENT STOCK TAMPON
# ==========================================================

@login_required
def ajouter_reglement_stock(request):

    if not peut_creer(request.user):

        return HttpResponseForbidden()

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                creer_reglement_stock_tampon(

                    utilisateur=request.user,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Règlement du stock tampon enregistré avec succès."

                )

                return redirect(
                    "liste_reglement_stock"
                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm()

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "produits": produits,

            "titre": "Nouveau règlement du stock tampon",

            "url_retour": "liste_reglement_stock",

        }

    )



# ==========================================================
# AJOUT CAUTION
# ==========================================================

@login_required
def ajouter_commande_caution(request):

    if not peut_creer(request.user):

        return HttpResponseForbidden()

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                creer_commande_caution(

                    utilisateur=request.user,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande enregistrée avec succès."

                )

                return redirect(

                    "liste_commandes_caution"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm()

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "produits": produits,

            "titre": "Nouvelle commande Caution bancaire",

            "url_retour": "liste_commandes_caution",

        }

    )


# ==========================================================
# AJOUT Gerant
# ==========================================================

@login_required
def ajouter_commande_gerant(request):

    if not peut_creer(request.user):

        return HttpResponseForbidden()

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                creer_commande(

                    utilisateur=request.user,

                    type_commande=Commande.TYPE_GERANT,

                    categorie_commande=Commande.CATEGORIE_NORMALE,

                    date_commande=form.cleaned_data["date_commande"],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande enregistrée avec succès."

                )

                return redirect(

                    "liste_commandes"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm()

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "produits": produits,

            "titre": "Nouvelle commande gérant"

        }

    )


# ==========================================================
# MODIFICATION
# ==========================================================

@login_required
def modifier_commande_view(
    request,
    pk
):

    commande = commande_par_id(

        request.user,

        pk

    )

    if not peut_modifier(

        request.user,

        commande

    ):

        messages.error(

            request,

            "Impossible de modifier cette commande. "
            "Les commandes Directeur ne sont modifiables "
            "que pendant les 3 jours suivant leur création."

        )

        return redirect("liste_commandes")

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                modifier_commande(

                    commande=commande,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande modifiée avec succès."

                )

                return redirect(

                    "liste_commandes"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm(

            initial={

                "date_commande": commande.date_commande

            }

        )

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "commande": commande,

            "produits": produits,

            "titre": "Modification d'une commande",

            "url_retour": "liste_commandes",

        }

    )



# ==========================================================
# MODIFICATION CAUTION
# ==========================================================

@login_required
def modifier_commande_caution_view(
    request,
    pk
):

    commande = commande_par_id(

        request.user,

        pk

    )

    if not peut_modifier(

        request.user,

        commande

    ):

        messages.error(

            request,

            "Impossible de modifier cette commande. "
            "Les commandes Directeur ne sont modifiables "
            "que pendant les 3 jours suivant leur création."

        )

        return redirect("liste_commandes_caution")

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                modifier_commande_caution(

                    commande=commande,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande modifiée avec succès."

                )

                return redirect(

                    "liste_commandes_caution"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm(

            initial={

                "date_commande": commande.date_commande

            }

        )

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "commande": commande,

            "produits": produits,

            "titre": "Modification d'une commande Caution bancaire",

            "url_retour": "liste_commandes_caution",

        }

    )


# ==========================================================
# MODIFICATION STOCK TAMPON
# ==========================================================

@login_required
def modifier_commande_stock_tampon_view(
    request,
    pk
):

    commande = commande_par_id(

        request.user,

        pk

    )

    if not peut_modifier(

        request.user,

        commande

    ):

        return HttpResponseForbidden()

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                modifier_commande_stock_tampon(

                    commande=commande,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande de stock tampon modifiée avec succès."

                )

                return redirect(
                    "liste_commandes_stock_tampon"
                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm(

            initial={

                "date_commande": commande.date_commande

            }

        )

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "commande": commande,

            "produits": produits,

            "titre": "Modification d'une commande de stock tampon",

            "url_retour": "liste_commandes_stock_tampon"

        }

    )


# ==========================================================
# MODIFICATION REGLEMENT STOCK TAMPON
# ==========================================================

@login_required
def modifier_reglement_stock_tampon_view(
    request,
    pk
):

    commande = commande_par_id(

        request.user,

        pk

    )

    if not peut_modifier(

        request.user,

        commande

    ):

        messages.error(

            request,

            "Impossible de modifier ce règlement. "
            "Les règlements de stock tampon ne sont modifiables "
            "que pendant les 3 jours suivant leur création."

        )

        return redirect(

            "liste_reglement_stock"

        )

    produits = produits_actifs()

    if request.method == "POST":

        form = CommandeForm(

            request.POST

        )

        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST,

                    produits

                )

                modifier_reglement_stock_tampon(

                    commande=commande,

                    date_commande=form.cleaned_data[
                        "date_commande"
                    ],

                    lignes=lignes

                )

                messages.success(

                    request,

                    "Commande de stock tampon modifiée avec succès."

                )

                return redirect(
                    "liste_reglement_stock"
                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = CommandeForm(

            initial={

                "date_commande": commande.date_commande

            }

        )

    return render(

        request,

        "commandes/form.html",

        {

            "form": form,

            "commande": commande,

            "produits": produits,

            "titre": "Modification d'un règlement de Stock Tampon",

            "url_retour": "liste_reglement_stock",

        }

    )


# ==========================================================
# COMMANDES EN ATTENTE
# ==========================================================

@login_required
def commandes_en_attente_view(request):

    if request.user.profil.role != "DIRECTEUR":

        return HttpResponseForbidden()

    commandes = commandes_en_attente(
        request.user
    )

    for commande in commandes:

        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

    gerants = Distributeur.objects.filter(
        categorie=Distributeur.CATEGORIE_GERANT,
        actif=True
    ).order_by(
        "nom",
        "prenom"
    )

    return render(

        request,

        "commandes/en_attente.html",

        {

            "commandes": commandes,
            "gerants": gerants,

        }

    )


# ==========================================================
# LISTE VALIDATIONS
# ==========================================================

@login_required
def liste_validation_commandes(request):

    if not peut_consulter(request.user):

        return HttpResponseForbidden()

    numero = filtre_texte(
        request,
        "numero"
    )

    (
        date_commande,
        date_debut,
        date_fin,
    ) = filtres_dates_recherche(
        request,
        "date_commande"
    )

    commandes = rechercher_commandes(

        utilisateur=request.user,

        categorie_commande=Commande.CATEGORIE_NORMALE,

        numero=numero,

        date_commande=date_commande,

        date_debut=date_debut,

        date_fin=date_fin,

        etat=Commande.EN_ATTENTE

    )

    page = paginer(

        commandes,

        request.GET.get("page")

    )

    total_brut = Decimal("0")

    total_net = Decimal("0")

    for commande in page:

        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

        total_brut += commande.montant_brut

        total_net += commande.montant_net

    return render(

        request,

        "commandes/liste.html",

        {
            "commandes": page,
            "numero": numero,
            "date_commande": date_commande,
            "titre": "Validation des commandes Gérant",
            "total_brut": total_brut,
            "total_net": total_net,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "pagination_querystring": querystring_pagination(request),
            "mode_validation": True,
            "url_nouveau": "liste_validation_commandes",
        }

    )




# ==========================================================
# VALIDER UNE COMMANDE GERANT
# ==========================================================

@login_required
def valider_commande_gerant_view(request, pk):

    commande = commande_gerant_en_attente_par_id(
        request.user,
        pk
    )

    try:

        from distributions.services import (
            creer_distribution_depuis_commande
        )

        # Création de la distribution
        distribution = creer_distribution_depuis_commande(

            commande=commande,

            utilisateur=request.user

        )

        # Validation de la commande
        valider_commande_gerant(

            commande

        )

        messages.success(

            request,

            f"La commande {commande.numero} a été validée "
            f"et la distribution {distribution.numero} "
            f"a été créée avec succès."

        )

    except Exception as e:

        messages.error(

            request,

            str(e)

        )

    return redirect(
        "liste_validation_commandes"
    )


# ==========================================================
# REJETER UNE COMMANDE GERANT
# ==========================================================

@login_required
def rejeter_commande_gerant_view(request, pk):

    commande = commande_gerant_en_attente_par_id(
        request.user,
        pk
    )

    retour = request.POST.get(
        "retour",
        ""
    )

    if retour not in [
        "commandes_en_attente",
        "liste_validation_commandes",
    ]:

        retour = "liste_validation_commandes"

    try:

        rejeter_commande_gerant(commande)

        messages.success(
            request,
            "La commande a été rejetée."
        )

    except Exception as e:

        messages.error(request, str(e))

    return redirect(retour)


@login_required
def valider_commande_directeur(request, commande_id):

    if request.method != "POST":

        return redirect("commandes_en_attente")

    gerant_id = request.POST.get("gerant")

    try:
        
        valider_commande_directeur_service(
            commande_id=commande_id,
            utilisateur=request.user,
            gerant_id=gerant_id,
        )

        messages.success(
            request,
            "La commande a été validée avec succès."
        )

    except Exception as e:

        messages.error(
            request,
            str(e)
        )

    return redirect("commandes_en_attente")
