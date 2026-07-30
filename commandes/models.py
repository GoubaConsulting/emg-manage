from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)

from django.contrib.auth.models import User

from referentiel.models import (
    PointVente,
    Produit
)

    

# ==========================================================
# MODELE : COMMANDE
# ==========================================================

class Commande(models.Model):
    """
    Représente une commande enregistrée
    par un point de vente.
    """
    TYPE_DIRECTEUR = "DIRECTEUR"
    TYPE_GERANT = "GERANT"

    TYPES_COMMANDE = [
        (TYPE_DIRECTEUR, "Commande Directeur"),
        (TYPE_GERANT, "Commande Gérant"),
    ]

    # ==========================================================
    # CATEGORIE DE COMMANDE
    # ==========================================================

    CATEGORIE_NORMALE = "NORMALE"

    CATEGORIE_STOCK_TAMPON = "STOCK_TAMPON"

    CATEGORIE_CAUTION = "CAUTION"

    CATEGORIE_REGLEMENT_STOCK = "REGLEMENT_STOCK"

    CATEGORIES_COMMANDE = [

        (CATEGORIE_NORMALE, "Commande normale"),

        (CATEGORIE_STOCK_TAMPON, "Commande stock tampon"),

        (CATEGORIE_CAUTION, "Commande caution bancaire"),

        (CATEGORIE_REGLEMENT_STOCK, "Règlement stock tampon"),

    ]

    EN_ATTENTE = "ATTENTE"
    VALIDEE = "VALIDEE"
    REFUSEE = "REFUSEE"
    VALIDEE_PARTIELLEMENT = "VALIDEE_PARTIELLEMENT"

    ETATS = [
        (EN_ATTENTE, "En attente"),
        (VALIDEE_PARTIELLEMENT, "Validée partiellement"),
        (VALIDEE, "Validée"),
        (REFUSEE, "Refusée"),
    ]


    idcommande = models.AutoField(
        primary_key=True
    )

    numero = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Numéro"
    )

    type_commande = models.CharField(
        max_length=20,
        choices=TYPES_COMMANDE,
        default=TYPE_GERANT,
        verbose_name="Type de commande"
    )

    categorie_commande = models.CharField(

        max_length=30,

        choices=CATEGORIES_COMMANDE,

        default=CATEGORIE_NORMALE,

        verbose_name="Catégorie"

    )

    date_commande = models.DateField(
        verbose_name="Date de la commande"
    )

    montant_brut = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        verbose_name="Montant brut"
    )

    montant_net = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        verbose_name="Montant net"
    )

    point_vente = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name="commandes",
        verbose_name="Point de vente"
    )

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="commandes",
        verbose_name="Utilisateur"
    )
    # ==========================================================
    # ETAT DE LA COMMANDE
    # ==========================================================

    etat = models.CharField(

        max_length=30,

        choices=ETATS,

        default=EN_ATTENTE,

        verbose_name="Etat"

    )
    actif = models.BooleanField(
        default=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )


    date_validation = models.DateTimeField(

        null=True,

        blank=True,

        verbose_name="Date de validation"

    )

    utilisateur_validation = models.ForeignKey(

        User,

        null=True,

        blank=True,

        on_delete=models.PROTECT,

        related_name="commandes_validees",

        verbose_name="Validée par"

    )

    class Meta:

        db_table = "commande"

        verbose_name = "Commande"

        verbose_name_plural = "Commandes"

        ordering = [
            "-date_commande",
            "-idcommande"
        ]
        indexes = [

            models.Index(
                fields=[
                    "etat"
                ]
            ),

            models.Index(
                fields=[
                    "type_commande"
                ]
            ),

            models.Index(
                fields=[
                    "date_commande"
                ]
            ),

            models.Index(
                fields=[
                    "point_vente"
                ]
            ),

        ]

    def __str__(self):

        return self.numero


# ==========================================================
# MODELE : LIGNE COMMANDE
# ==========================================================

class LigneCommande(models.Model):
    """
    Ligne d'une commande.
    """

    idlignecommande = models.AutoField(
        primary_key=True
    )

    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT,
        related_name="lignes_commande"
    )

    prix_unitaire = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    montant = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    quantite = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    quantite_distribuee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    taux_remise = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )

    montant_remise = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    montant_net = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    class Meta:

        db_table = "lignecommande"

        verbose_name = "Ligne commande"

        verbose_name_plural = "Lignes commande"

        ordering = [
            "produit__designation"
        ]

        constraints = [

            models.UniqueConstraint(

                fields=[
                    "commande",
                    "produit"
                ],

                name="produit_unique_commande"

            )

        ]

    def __str__(self):

        return f"{self.commande.numero} - {self.produit.designation}"