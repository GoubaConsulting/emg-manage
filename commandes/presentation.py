from collections import OrderedDict
from decimal import Decimal


def preparer_affichage_commande(commande):
    """
    Prépare une commande pour son affichage.

    Les lignes sont regroupées par compagnie
    avec calcul des sous-totaux.
    """

    groupes = OrderedDict()

    for ligne in (
        commande.lignes
        .select_related(
            "produit",
            "produit__compagnie"
        )
        .order_by(
            "produit__compagnie__designation",
            "produit__designation"
        )
    ):

        compagnie = ligne.produit.compagnie

        if compagnie.idcompagnie not in groupes:

            groupes[compagnie.idcompagnie] = {

                "compagnie": compagnie,

                "lignes": [],

                "sous_total_brut": Decimal("0"),

                "sous_total_net": Decimal("0"),

            }

        groupes[compagnie.idcompagnie]["lignes"].append(ligne)

        groupes[compagnie.idcompagnie]["sous_total_brut"] += ligne.montant

        groupes[compagnie.idcompagnie]["sous_total_net"] += ligne.montant_net

    return list(groupes.values())