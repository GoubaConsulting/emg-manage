from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)

from referentiel.models import (
    PointVente,
    Compagnie,
    Produit
)


# ==========================================================
# MODELE : OBJECTIF
# ==========================================================
class Objectif(models.Model):
    """
    Représente un objectif commercial mensuel.

    Un objectif est obligatoirement lié à :
        - une compagnie
        - un point de vente
        - une période (mois + année)

    Il concerne un ou plusieurs produits appartenant
    à cette même compagnie.
    """

    # -----------------------------
    # Clé primaire
    # -----------------------------
    idobjectif = models.AutoField(
        primary_key=True
    )

    # -----------------------------
    # Informations principales
    # -----------------------------
    designation = models.CharField(
        max_length=150,
        editable=False,
        verbose_name="Désignation"
    )

    compagnie = models.ForeignKey(
        Compagnie,
        on_delete=models.PROTECT,
        related_name="objectifs",
        verbose_name="Compagnie"
    )

    mois = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(12)
        ],
        verbose_name="Mois"
    )

    annee = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(2025),
            MaxValueValidator(2100)
        ],
        verbose_name="Année"
    )

    montant_cible = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="Montant cible"
    )

    montant_realise = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        verbose_name="Montant réalisé"
    )

    taux_realise = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="Taux réalisé"
    )

    # -----------------------------
    # Relations
    # -----------------------------
    point_vente = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name="objectifs",
        verbose_name="Point de vente"
    )

    # -----------------------------
    # Audit
    # -----------------------------
    actif = models.BooleanField(
        default=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    # -----------------------------
    # Paramètres du modèle
    # -----------------------------
    class Meta:

        db_table = "objectif"

        verbose_name = "Objectif"

        verbose_name_plural = "Objectifs"

        ordering = [
            "-annee",
            "-mois",
            "designation"
        ]

    # -----------------------------
    # Affichage
    # -----------------------------
    def __str__(self):

        return (
            f"{self.designation}"
            f" ({self.periode})"
        )

    # -----------------------------
    # Propriétés calculées
    # -----------------------------
    @property
    def periode(self):
        """
        Retourne la période au format MM/AAAA.
        """

        return f"{self.mois:02d}/{self.annee}"

    @property
    def objectif_atteint(self):
        """
        Retourne True si l'objectif est atteint.
        """

        return self.taux_realise >= 100


# ==========================================================
# MODELE : LIGNE OBJECTIF
# ==========================================================
class LigneObjectif(models.Model):
    """
    Contient les produits concernés
    par un objectif.
    """

    # -----------------------------
    # Clé primaire
    # -----------------------------
    idligneobjectif = models.AutoField(
        primary_key=True
    )

    # -----------------------------
    # Relations
    # -----------------------------
    objectif = models.ForeignKey(
        Objectif,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Objectif"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT,
        related_name="lignes_objectifs",
        verbose_name="Produit"
    )

    # -----------------------------
    # Paramètres
    # -----------------------------
    class Meta:

        db_table = "ligneobjectif"

        verbose_name = "Ligne objectif"

        verbose_name_plural = "Lignes objectifs"

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "objectif",
                    "produit"
                ],
                name="produit_unique_objectif"
            )

        ]

    # -----------------------------
    # Affichage
    # -----------------------------
    def __str__(self):

        return (
            f"{self.objectif.designation}"
            f" - "
            f"{self.produit.designation}"
        )
    


class Meta:

    indexes = [

        models.Index(
            fields=[
                "point_vente",
                "mois",
                "annee"
            ]
        ),

        models.Index(
            fields=[
                "designation"
            ]
        ),

    ]
