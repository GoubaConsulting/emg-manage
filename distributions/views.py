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
)
from django.contrib import messages

from datetime import date

from decimal import Decimal

from itertools import groupby

from django.core.paginator import Paginator

from django.db.models import Sum

from comptes.models import ProfilUtilisateur



@login_required
def ajouter_distribution(request):

    #produits = Produit.objects.filter(
    #    actif=True
    #).order_by("designation")

    profil = request.user.profil

    est_directeur = profil.role == "DIRECTEUR"

    est_gerant = profil.role == "GERANT"


    produits = (
        Produit.objects
        .filter(actif=True)
        .select_related("compagnie")
        .order_by("compagnie__designation", "designation")
    )

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

        if est_directeur:

            if post_data.get("commande"):

                commande = Commande.objects.get(
                    pk=post_data["commande"]
                )

                post_data["distributeur"] = commande.distributeur.pk

                post_data["type_distribution"] = Distribution.TYPE_COMMANDE_GERANT

                post_data["point_vente_destination"] = commande.point_vente.pk

        form = DistributionForm(post_data)
        #if not form.is_valid():
         #   print(form.errors.as_json())
        if form.is_valid():

            try:

                lignes = construire_lignes_depuis_formulaire(
                    request.POST,
                    produits
                )

                commande = form.cleaned_data["commande"]

                if est_directeur:

                    type_distribution = Distribution.TYPE_COMMANDE_GERANT

                    distributeur = commande.distributeur

                    point_vente_destination = commande.point_vente

                else:

                    distributeur = form.cleaned_data["distributeur"]

                    point_vente_destination = form.cleaned_data["point_vente_destination"]

                    if form.cleaned_data["type_operation"] == "DIST":

                        type_distribution = Distribution.TYPE_DISTRIBUTEUR

                    else:

                        type_distribution = Distribution.TYPE_CLIENT_DIRECT

                creer_distribution(
                    utilisateur=request.user,
                    type_distribution=type_distribution,
                    commande=commande,
                    point_vente_destination=point_vente_destination,
                    distributeur=distributeur,
                    date_distribution=form.cleaned_data["date_distribution"],
                    lignes=lignes,
                )

                messages.success(
                    request,
                    "Distribution enregistrée avec succès."
                )

                return redirect("liste_distributions")

            except Exception as e:

                form.add_error(None, str(e))

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

        "distributions/form.html",

        {

            "form": form,

            "produits": produits,

            "commandes": commandes,

            "titre": "Nouvelle distribution",

            "url_retour": "liste_distributions",

            "context_commandes": json.dumps(commandes_json),

            "est_gerant": est_gerant,

        }

    )


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

    aujourd_hui = date.today()

    mois = int(
        request.GET.get(
            "mois",
            aujourd_hui.month
        )
    )

    annee = int(
        request.GET.get(
            "annee",
            aujourd_hui.year
        )
    )


    point_selectionne = request.GET.get("point_vente", "")

    distributeur_selectionne = request.GET.get("distributeur", "")

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
            date_distribution__month=mois,
            date_distribution__year=annee,
        )
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

    # ==========================================
    # Contexte
    # ==========================================

    contexte = {

        "url_nouveau": "distributions:ajouter_distribution",

        "titre": "Liste des distributions",

        "est_directeur": est_directeur,

        "est_gerant": est_gerant,

        "mois": mois,

        "annee": annee,

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
