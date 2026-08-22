"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Modèles du module Distributions.

==========================================================
"""

from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)

from django.contrib.auth.models import User

from commandes.models import Commande

from referentiel.models import (
    PointVente,
    Produit,
    Distributeur
)


# ==========================================================
# MODELE : DISTRIBUTION
# ==========================================================

class Distribution(models.Model):
    """
    Représente une distribution de produits.
    """

    # ======================================================
    # TYPES DE DISTRIBUTION
    # ======================================================

    TYPE_COMMANDE_GERANT = "COMMANDE_GERANT"

    TYPE_DISTRIBUTEUR = "DISTRIBUTEUR"

    TYPE_CLIENT_DIRECT = "CLIENT_DIRECT"

    TYPES_DISTRIBUTION = [

        (
            TYPE_COMMANDE_GERANT,
            "Commande gérant"
        ),

        (
            TYPE_DISTRIBUTEUR,
            "Distributeur"
        ),

        (
            TYPE_CLIENT_DIRECT,
            "Client direct"
        ),

    ]

    # ======================================================
    # ETATS
    # ======================================================

    ETAT_OUVERTE = "OUVERTE"

    ETAT_CLOTUREE = "CLOTUREE"

    ETATS = [

        (
            ETAT_OUVERTE,
            "Ouverte"
        ),

        (
            ETAT_CLOTUREE,
            "Clôturée"
        ),

    ]

    iddistribution = models.AutoField(
        primary_key=True
    )

    numero = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Numéro"
    )

    type_distribution = models.CharField(
        max_length=30,
        choices=TYPES_DISTRIBUTION,
        verbose_name="Type de distribution"
    )

    commande = models.ForeignKey(
        Commande,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="distributions",
        verbose_name="Commande"
    )

    point_vente_source = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name="distributions_source",
    )

    point_vente_destination = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name="distributions_destination",
        null=True,
        blank=True,
    )

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="distributions",
        verbose_name="Utilisateur"
    )

    distributeur = models.ForeignKey(
        Distributeur,
        on_delete=models.PROTECT,
        related_name="distributions",
        verbose_name="Distributeur"
    )

    date_distribution = models.DateField(
        verbose_name="Date de distribution"
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

    etat = models.CharField(
        max_length=20,
        choices=ETATS,
        default=ETAT_OUVERTE,
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

    class Meta:

        db_table = "distribution"

        verbose_name = "Distribution"

        verbose_name_plural = "Distributions"

        ordering = [

            "-date_distribution",

            "-iddistribution"

        ]

        indexes = [

            models.Index(
                fields=[
                    "date_distribution"
                ]
            ),

            models.Index(
                fields=[
                    "point_vente_source"
                ]
            ),

            models.Index(
                fields=[
                    "point_vente_destination"
                ]
            ),

            models.Index(
                fields=[
                    "type_distribution"
                ]
            ),

            models.Index(
                fields=[
                    "distributeur"
                ]
            ),

            models.Index(
                fields=[
                    "etat"
                ],
                name="distribution_etat_idx"
            ),

        ]

    def __str__(self):

        return self.numero


# ==========================================================
# MODELE : LIGNE DISTRIBUTION
# ==========================================================

class LigneDistribution(models.Model):
    """
    Ligne d'une distribution.
    """

    idlignedistribution = models.AutoField(
        primary_key=True
    )

    distribution = models.ForeignKey(
        Distribution,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT,
        related_name="lignes_distribution"
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

        db_table = "lignedistribution"

        verbose_name = "Ligne distribution"

        verbose_name_plural = "Lignes distribution"

        ordering = [

            "produit__designation"

        ]

        constraints = [

            models.UniqueConstraint(

                fields=[
                    "distribution",
                    "produit"
                ],

                name="produit_unique_distribution"

            )

        ]

    def __str__(self):

        return (

            f"{self.distribution.numero}"

            f" - "

            f"{self.produit.designation}"

        )
