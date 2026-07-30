"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Validations métier des distributions.

==========================================================
"""

from django.core.exceptions import ValidationError

from .models import Distribution

from stocks.services import stock_disponible

# ==========================================================
# COMMANDE SELECTIONNEE
# ==========================================================

def verifier_commande_selectionnee(commande):
    """
    Vérifie qu'une commande a été sélectionnée.
    """

    if commande is None:

        raise ValidationError(
            "Aucune commande n'a été sélectionnée. "
            "Veuillez sélectionner une commande avant d'enregistrer la distribution."
        )

# ==========================================================
# DATE DE DISTRIBUTION
# ==========================================================

def verifier_date_distribution(date_distribution):
    """
    Vérifie que la date de distribution est renseignée.
    """

    if date_distribution is None:

        raise ValidationError(
            "La date de distribution est obligatoire."
        )


# ==========================================================
# STOCK DISPONIBLE
# ==========================================================

def verifier_stock_distribution(
    point_vente,
    lignes
):
    """
    Vérifie que le stock est suffisant
    pour tous les produits distribués.
    """

    for ligne in lignes:

        stock = stock_disponible(

            point_vente=point_vente,

            produit=ligne["produit"]

        )

        if ligne["quantite"] > stock.quantite:

            raise ValidationError(

                f"Stock insuffisant pour le produit "
                f"'{ligne['produit'].designation}'. "
                f"Stock disponible : {stock.quantite}. "
                f"Quantité demandée : {ligne['quantite']}."

            )

# ==========================================================
# VALIDATION DU TYPE DE DISTRIBUTION
# ==========================================================

def valider_type_distribution(type_distribution):
    """
    Vérifie que le type de distribution est valide.
    """

    types_valides = [

        Distribution.TYPE_COMMANDE_GERANT,

        Distribution.TYPE_DISTRIBUTEUR,

        Distribution.TYPE_CLIENT_DIRECT,

    ]

    if type_distribution not in types_valides:

        raise ValidationError(
            "Le type de distribution est invalide."
        )


# ==========================================================
# VALIDATION DU DISTRIBUTEUR
# ==========================================================

def valider_distributeur(distributeur):
    """
    Vérifie qu'un distributeur est renseigné.
    """

    if distributeur is None:

        raise ValidationError(
            "Le distributeur est obligatoire."
        )


# ==========================================================
# VALIDATION DE LA QUANTITE
# ==========================================================

def valider_quantite(quantite):
    """
    Vérifie que la quantité est strictement positive.
    """

    if quantite <= 0:

        raise ValidationError(
            "La quantité doit être supérieure à zéro."
        )


# ==========================================================
# VALIDATION DU PRIX
# ==========================================================

def valider_prix(prix):
    """
    Vérifie que le prix est valide.
    """

    if prix < 0:

        raise ValidationError(
            "Le prix ne peut pas être négatif."
        )


# ==========================================================
# VALIDATION DU TAUX DE REMISE
# ==========================================================

def valider_taux_remise(taux):
    """
    Vérifie que le taux de remise est compris entre 0 et 100.
    """

    if taux < 0 or taux > 100:

        raise ValidationError(
            "Le taux de remise doit être compris entre 0 et 100."
        )

# ==========================================================
# COMMANDE DISTRIBUABLE
# ==========================================================

def verifier_commande_distribuable(commande):
    """
    Vérifie qu'une commande
    peut recevoir une distribution.
    """

    from .models import Distribution

    if Distribution.objects.filter(
        commande=commande,
        actif=True
    ).exists():

        raise ValidationError(
            "Cette commande possède déjà une distribution."
        )

# ==========================================================
# PRODUITS DE LA COMMANDE
# ==========================================================

def verifier_produits_distribution(
    commande,
    lignes
):
    """
    Vérifie que tous les produits sélectionnés
    existent dans la commande.
    """

    produits_commande = {
        ligne.produit_id
        for ligne in commande.lignes.all()
    }

    for ligne in lignes:

        if ligne["produit"].idproduit not in produits_commande:

            raise ValidationError(
                f"Le produit '{ligne['produit'].designation}' "
                "ne fait pas partie de la commande sélectionnée."
            )

# ==========================================================
# QUANTITES DISTRIBUEES
# ==========================================================

def verifier_quantites_distribution(
    commande,
    lignes
):
    """
    Vérifie que les quantités
    distribuées ne dépassent
    jamais les quantités commandées.
    """

    lignes_commande = {

        ligne.produit_id: ligne

        for ligne in commande.lignes.all()

    }

    for ligne in lignes:

        ligne_commande = lignes_commande.get(

            ligne["produit"].pk

        )

        if ligne_commande is None:

            continue

        if ligne["quantite"] > ligne_commande.quantite:

            raise ValidationError(

                f"La quantité distribuée du produit "

                f"{ligne['produit'].designation} "

                f"dépasse la quantité commandée."

            )

# ==========================================================
# PRESENCE DES LIGNES
# ==========================================================

def verifier_presence_ligne(lignes):
    """
    Vérifie qu'au moins une ligne
    est présente dans la distribution.
    """

    if not lignes:

        raise ValidationError(
            "La distribution doit contenir au moins un produit."
        )


# ==========================================================
# VALIDATION DU MONTANT
# ==========================================================

def verifier_montant(montant):
    """
    Vérifie que le montant est valide.
    """

    if montant < 0:

        raise ValidationError(
            "Le montant ne peut pas être négatif."
        )