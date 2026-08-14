"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Modeles des entrees et sorties manuelles de stock.

==========================================================
"""

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models

from referentiel.models import (
    PointVente,
    Produit,
)

from stocks.models import TYPES_STOCK, TYPE_NORMAL


# ==========================================================
# MODELE : MOUVEMENT STOCK
# ==========================================================

class MouvementStock(models.Model):
    """
    Document d'entree ou de sortie manuelle de stock.
    """

    TYPE_ENTREE = "ENTREE"

    TYPE_SORTIE = "SORTIE"

    TYPES_MOUVEMENT = [
        (
            TYPE_ENTREE,
            "Entree de stock"
        ),
        (
            TYPE_SORTIE,
            "Sortie de stock"
        ),
    ]

    MOTIF_APPROVISIONNEMENT = "APPROVISIONNEMENT"

    MOTIF_RETOUR = "RETOUR"

    MOTIF_AJUSTEMENT = "AJUSTEMENT"

    MOTIF_CASSE_PERTE = "CASSE_PERTE"

    MOTIF_AUTRE = "AUTRE"

    MOTIFS = [
        (
            MOTIF_APPROVISIONNEMENT,
            "Approvisionnement"
        ),
        (
            MOTIF_RETOUR,
            "Retour"
        ),
        (
            MOTIF_AJUSTEMENT,
            "Ajustement"
        ),
        (
            MOTIF_CASSE_PERTE,
            "Casse / perte"
        ),
        (
            MOTIF_AUTRE,
            "Autre"
        ),
    ]

    idmouvementstock = models.AutoField(
        primary_key=True
    )

    numero = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Numero"
    )

    type_mouvement = models.CharField(
        max_length=20,
        choices=TYPES_MOUVEMENT,
        verbose_name="Type de mouvement"
    )

    type_stock = models.CharField(
        max_length=20,
        choices=TYPES_STOCK,
        default=TYPE_NORMAL,
        verbose_name="Type de stock"
    )

    date_mouvement = models.DateField(
        verbose_name="Date du mouvement"
    )

    point_vente = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name="mouvements_stock",
        verbose_name="Point de vente"
    )

    motif = models.CharField(
        max_length=40,
        choices=MOTIFS,
        default=MOTIF_AJUSTEMENT,
        verbose_name="Motif"
    )

    observation = models.TextField(
        blank=True,
        default="",
        verbose_name="Observation"
    )

    total_quantite = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Quantite totale"
    )

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="mouvements_stock",
        verbose_name="Utilisateur"
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

        db_table = "mouvementstock"

        verbose_name = "Mouvement de stock"

        verbose_name_plural = "Mouvements de stock"

        ordering = [
            "-date_mouvement",
            "-idmouvementstock",
        ]

        indexes = [
            models.Index(
                fields=[
                    "date_mouvement"
                ]
            ),
            models.Index(
                fields=[
                    "point_vente"
                ]
            ),
            models.Index(
                fields=[
                    "type_mouvement"
                ]
            ),
            models.Index(
                fields=[
                    "type_stock"
                ]
            ),
        ]

    def __str__(self):

        return self.numero


# ==========================================================
# MODELE : LIGNE MOUVEMENT STOCK
# ==========================================================

class LigneMouvementStock(models.Model):
    """
    Ligne produit d'un mouvement de stock.
    """

    idlignemouvementstock = models.AutoField(
        primary_key=True
    )

    mouvement = models.ForeignKey(
        MouvementStock,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Mouvement"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT,
        related_name="lignes_mouvements_stock",
        verbose_name="Produit"
    )

    quantite = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Quantite"
    )

    stock_avant = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Stock avant"
    )

    stock_apres = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Stock apres"
    )

    class Meta:

        db_table = "lignemouvementstock"

        verbose_name = "Ligne mouvement de stock"

        verbose_name_plural = "Lignes mouvements de stock"

        ordering = [
            "produit__designation"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "mouvement",
                    "produit",
                ],
                name="produit_unique_mouvement_stock"
            )
        ]

    def __str__(self):

        return (
            f"{self.mouvement.numero}"
            f" - "
            f"{self.produit.designation}"
        )
