from django.shortcuts import (
    render,
    redirect,
)
from commandes.selectors import commandes_en_attente
from commandes.presentation import preparer_affichage_commande
from commandes.models import Commande
from referentiel.models import Produit

from .forms import DistributionForm
from .models import Distribution
from django.contrib.auth.decorators import login_required
from .permissions import verifier_creation_distribution
from referentiel.models import (
    Produit,
    PointVente,
    Distributeur,
)
from .services import (
    construire_lignes_depuis_formulaire,
    creer_distribution,
    creer_distribution_gerant,
)
from django.contrib import messages

from calendar import monthrange
from datetime import date

from decimal import Decimal

from itertools import groupby

from django.core.paginator import Paginator

from django.db.models import Sum

from comptes.models import ProfilUtilisateur

from stocks.models import Stock


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


def querystring_pagination(
    request,
    *pages
):
    """
    Conserve les filtres lors du changement de page.
    """

    params = request.GET.copy()

    for page in pages:

        params.pop(
            page,
            None
        )

    return params.urlencode()


def filtre_texte(
    request,
    nom
):
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


@login_required
def ajouter_distribution(request):

    #produits = Produit.objects.filter(
    #    actif=True
    #).order_by("designation")

    profil = request.user.profil

    est_directeur = profil.role == "DIRECTEUR"

    est_gerant = profil.role == "GERANT"


    stocks = (

        Stock.objects

        .filter(

            point_vente=profil.point_vente,

            produit__actif=True,

            quantite__gt=0,

        )

        .select_related(

            "produit",

            "produit__compagnie",

        )

        .order_by(

            "produit__compagnie__designation",

            "produit__designation",

        )

    )

    produits = []

    for stock in stocks:

        stock.produit.stock_disponible = stock.quantite

        produits.append(stock.produit)

    compagnies = []

    for compagnie, liste in groupby(

        produits,

        key=lambda produit: produit.compagnie

    ):

        compagnies.append({

            "grouper": compagnie,

            "list": list(liste),

        })

    commandes = commandes_en_attente(request.user)

    for commande in commandes:
        commande.groupes_compagnies = preparer_affichage_commande(
            commande
        )

    import json

    commandes_json = {}

    for commande in commandes:

        lignes = {}

        for ligne in commande.lignes.select_related("produit"):

            lignes[str(ligne.produit.idproduit)] = {

                "montant": float(ligne.montant),

                "taux": float(ligne.taux_remise),

                "quantite": float(ligne.quantite),

                "net": float(ligne.montant_net),

            }

        commandes_json[str(commande.idcommande)] = lignes

    if request.method == "POST":

        post_data = request.POST.copy()

        form = DistributionForm(post_data)
        #if not form.is_valid():
         #   print(form.errors.as_json())
        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(

                    request.POST

                )

                distributeur = form.cleaned_data["distributeur"]

                type_distribution = Distribution.TYPE_DISTRIBUTEUR

                creer_distribution_gerant(

                    utilisateur=request.user,

                    type_distribution=type_distribution,

                    distributeur=distributeur,

                    date_distribution=form.cleaned_data["date_distribution"],

                    lignes=lignes,

                )

                messages.success(

                    request,

                    "Distribution enregistrée avec succès."

                )

                return redirect(

                    "distributions:liste_distributions"

                )

            except Exception as e:

                form.add_error(

                    None,

                    str(e)

                )

    else:

        form = DistributionForm()

        if est_directeur:

            form.fields.pop("distributeur", None)
            form.fields.pop("type_destinataire", None)
            form.fields.pop("nom_client", None)

        elif est_gerant:

            form.fields["distributeur"].queryset = (
                Distributeur.objects.filter(
                    actif=True,
                    point_vente=profil.point_vente,
                    code__startswith="DIST",
                ).order_by(
                    "nom",
                    "prenom",
                )
            )

    return render(

        request,

        "distributions/gerant/form.html",

        {

            "form": form,

            "produits": produits,

            "compagnies": compagnies,

            "commandes": commandes,

            "titre": "Nouvelle distribution",

            "url_retour": "liste_distributions",

            "context_commandes": json.dumps(commandes_json),

            "est_gerant": est_gerant,

        }

    )


@login_required
def ajouter_distribution_client(request):
    """
    Distribution du gérant vers
    un client direct.
    """
    pass


@login_required
def liste_distributions(request):
    """
    Liste des distributions.

    Directeur :
        - voit uniquement ses distributions.

    Gérant :
        - voit uniquement les distributions
          de son point de vente.
    """

    profil = request.user.profil

    est_directeur = (
        profil.role == "DIRECTEUR"
    )

    est_gerant = (
        profil.role == "GERANT"
    )

    # ==========================================
    # Mois courant par défaut
    # ==========================================

    (
        date_distribution,
        date_debut,
        date_fin,
    ) = filtres_dates_recherche(
        request,
        "date_distribution"
    )

    aujourd_hui = date.today()

    mois = aujourd_hui.month

    annee = aujourd_hui.year


    point_selectionne = request.GET.get("point_vente", "")

    distributeur_selectionne = request.GET.get("distributeur", "")

    numero = filtre_texte(
        request,
        "numero"
    )

    # ==========================================
    # Base des distributions
    # ==========================================

    distributions = (
        Distribution.objects
        .select_related(
            "commande",
            "point_vente_source",
            "point_vente_destination",
            "distributeur",
            "utilisateur",
        )
        .prefetch_related(
            "lignes__produit__compagnie"
        )
        .filter(
            actif=True,
            utilisateur=request.user,
        )
    )

    if date_distribution:

        distributions = distributions.filter(
            date_distribution=date_distribution
        )

    else:

        if date_debut:

            distributions = distributions.filter(
                date_distribution__gte=date_debut
            )

        if date_fin:

            distributions = distributions.filter(
                date_distribution__lte=date_fin
            )

    if numero:

        distributions = distributions.filter(
            numero__icontains=numero
        )
    

    # ==========================================
    # Directeur
    # ==========================================

    if est_directeur:

        distributions = distributions.filter(

            utilisateur=request.user

        )

        if point_selectionne:

            distributions = distributions.filter(

                point_vente_source_id=point_selectionne

            )

    # ==========================================
    # Gérant
    # ==========================================

    elif est_gerant:

        distributions = distributions.filter(

            point_vente_source=profil.point_vente,

            type_distribution__in=[

                Distribution.TYPE_DISTRIBUTEUR,

                Distribution.TYPE_CLIENT_DIRECT,

            ]

        )

        if distributeur_selectionne:

            distributions = distributions.filter(

                distributeur_id=distributeur_selectionne

            )
    # ==========================================
    # Répartition par type
    # ==========================================

    distributions_sous = distributions.filter(

        type_distribution=Distribution.TYPE_DISTRIBUTEUR

    )

    distributions_clients = distributions.filter(

        type_distribution=Distribution.TYPE_CLIENT_DIRECT

    )

    # ==========================================
    # Statistiques Directeur
    # ==========================================

    total_brut = (

        distributions.aggregate(

            total=Sum("montant_brut")

        )["total"]

        or Decimal("0")

    )

    total_net = (

        distributions.aggregate(

            total=Sum("montant_net")

        )["total"]

        or Decimal("0")

    )

    # ==========================================
    # Statistiques Sous-distributeurs
    # ==========================================

    total_brut_sous = (

        distributions_sous.aggregate(

            total=Sum("montant_brut")

        )["total"]

        or Decimal("0")

    )

    total_net_sous = (

        distributions_sous.aggregate(

            total=Sum("montant_net")

        )["total"]

        or Decimal("0")

    )

    # ==========================================
    # Statistiques Clients directs
    # ==========================================

    total_brut_clients = (

        distributions_clients.aggregate(

            total=Sum("montant_brut")

        )["total"]

        or Decimal("0")

    )

    total_net_clients = (

        distributions_clients.aggregate(

            total=Sum("montant_net")

        )["total"]

        or Decimal("0")

    )

    # ==========================================
    # Pagination
    # ==========================================

    distributions = Paginator(

        distributions,

        20

    ).get_page(

        request.GET.get("page")

    )

    distributions_sous = Paginator(

        distributions_sous,

        20

    ).get_page(

        request.GET.get("page_sous")

    )

    distributions_clients = Paginator(

        distributions_clients,

        20

    ).get_page(

        request.GET.get("page_client")

    )


    # ==========================================
    # Préparation de l'affichage
    # ==========================================

    def preparer_groupes(distributions_page):
        """
        Prépare les groupes de produits
        par compagnie pour chaque distribution.
        """

        for distribution in distributions_page:

            lignes = sorted(

                distribution.lignes.all(),

                key=lambda ligne: (
                    ligne.produit.compagnie.designation,
                    ligne.produit.designation,
                )

            )

            groupes = []

            for compagnie, lignes_compagnie in groupby(

                lignes,

                key=lambda ligne: ligne.produit.compagnie

            ):

                lignes_compagnie = list(
                    lignes_compagnie
                )

                groupes.append({

                    "compagnie": compagnie,

                    "lignes": lignes_compagnie,

                    "total_net": sum(

                        (
                            ligne.montant_net
                            for ligne in lignes_compagnie
                        ),

                        Decimal("0")

                    )

                })

            distribution.groupes_compagnies = groupes


    preparer_groupes(distributions)

    preparer_groupes(distributions_sous)

    preparer_groupes(distributions_clients)

    # ==========================================
    # Listes pour les filtres
    # ==========================================

    points_vente = (
        PointVente.objects
        .filter(actif=True)
        .order_by("designation")
    )

    distributeurs = (
        Distributeur.objects
        .filter(
            actif=True,
            point_vente=profil.point_vente,
            code__startswith="DIST",
        )
        .order_by("nom", "prenom")
    )

    profil = request.user.profil

    if profil.role == "DIRECTEUR":

        url_nouveau = "distributions:ajouter_distribution_directeur"

    else:

        url_nouveau = "distributions:ajouter_distribution"


    # ==========================================
    # Contexte
    # ==========================================

    contexte = {

        "url_nouveau": url_nouveau,

        "titre": "Liste des distributions",

        "est_directeur": est_directeur,

        "est_gerant": est_gerant,

        "mois": mois,

        "annee": annee,

        "date_distribution": date_distribution,

        "date_debut": date_debut,

        "date_fin": date_fin,

        "numero": numero,

        "pagination_querystring": querystring_pagination(
            request,
            "page",
            "page_sous",
            "page_client",
        ),

        "distributions": distributions,

        "distributions_sous": distributions_sous,

        "distributions_clients": distributions_clients,

        "total_brut": total_brut,

        "total_net": total_net,

        "total_brut_sous": total_brut_sous,

        "total_net_sous": total_net_sous,

        "total_brut_clients": total_brut_clients,

        "total_net_clients": total_net_clients,

        "points_vente": points_vente,

        "distributeurs": distributeurs,

        "point_selectionne": int(point_selectionne) if point_selectionne else None,

        "distributeur_selectionne": int(distributeur_selectionne) if distributeur_selectionne else None,

    }

    return render(

        request,

        "distributions/liste.html",

        contexte

    )

@login_required
def ajouter_distribution_directeur(request):

    profil = request.user.profil

    produits = (

        Produit.objects
        .filter(actif=True)
        .select_related("compagnie")
        .order_by(
            "compagnie__designation",
            "designation"
        )

    )

    commandes = commandes_en_attente(request.user)

    for commande in commandes:

        commande.groupes_compagnies = (

            preparer_affichage_commande(
                commande
            )

        )

    import json

    commandes_json = {}

    for commande in commandes:

        lignes = {}

        for ligne in commande.lignes.select_related(

            "produit__compagnie"

        ):

            lignes[str(ligne.produit.idproduit)] = {

                "id": ligne.produit.idproduit,

                "designation": ligne.produit.designation,

                "compagnie": ligne.produit.compagnie.designation,

                "compagnie_id": ligne.produit.compagnie.idcompagnie,

                "prix": float(ligne.prix_unitaire),

                "montant": float(ligne.montant),

                "quantite": float(ligne.quantite),

                "taux": float(ligne.taux_remise),

                "montant_remise": float(

                    ligne.montant_remise

                ),

                "net": float(

                    ligne.montant_net

                ),

            }

        commandes_json[str(commande.idcommande)] = lignes

    if request.method == "POST":

        try:

            commande = Commande.objects.get(

                pk=request.POST.get(

                    "commande"

                )

            )

            lignes = construire_lignes_depuis_formulaire(

                request.POST

            )

            distributeur = Distributeur.objects.get(
            
                point_vente=commande.point_vente,

                categorie=Distributeur.CATEGORIE_GERANT,

                actif=True,

            )

            creer_distribution(

                utilisateur=request.user,

                type_distribution=Distribution.TYPE_COMMANDE_GERANT,

                commande=commande,

                point_vente_destination=commande.point_vente,

                distributeur=distributeur,

                date_distribution=date.today(),

                lignes=lignes,

            )

            messages.success(

                request,

                "Distribution enregistrée avec succès."

            )

            return redirect(

                "distributions:liste_distributions"

            )

        except Exception as e:

            messages.error(

                request,

                str(e)

            ) 

    return render(

        request,

        "distributions/directeur/form.html",

        {

            "titre": "Distribution Directeur → Gérant",

            "commandes": commandes,

            "context_commandes": json.dumps(

                commandes_json

            ),

        }

    )
