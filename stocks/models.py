from django.db import models

from django.core.validators import (
    MinValueValidator
)

from referentiel.models import (
    PointVente,
    Produit
)


# ==========================================================
# TYPES DE STOCK
# ==========================================================

TYPE_NORMAL = "NORMAL"

TYPE_TAMPON = "TAMPON"


TYPES_STOCK = [

    (TYPE_NORMAL, "Stock normal"),

    (TYPE_TAMPON, "Stock tampon"),

]


# ==========================================================
# MODELE STOCK
# ==========================================================

class Stock(models.Model):

    idstock = models.AutoField(
        primary_key=True
    )

    point_vente = models.ForeignKey(

        PointVente,

        on_delete=models.PROTECT,

        related_name="stocks",

        verbose_name="Point de vente"

    )

    produit = models.ForeignKey(

        Produit,

        on_delete=models.PROTECT,

        related_name="stocks",

        verbose_name="Produit"

    )

    type_stock = models.CharField(

        max_length=20,

        choices=TYPES_STOCK,

        default=TYPE_NORMAL,

        verbose_name="Type de stock"

    )

    quantite = models.DecimalField(

        max_digits=18,

        decimal_places=2,

        default=0,

        validators=[
            MinValueValidator(0)
        ],

        verbose_name="Quantité"

    )

    seuil_alerte = models.DecimalField(

        max_digits=18,

        decimal_places=2,

        default=0,

        validators=[
            MinValueValidator(0)
        ],

        verbose_name="Seuil d'alerte"

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

        db_table = "stock"

        verbose_name = "Stock"

        verbose_name_plural = "Stocks"

        ordering = [

            "point_vente__designation",

            "produit__designation"

        ]

        constraints = [

            models.UniqueConstraint(

                fields=[

                    "point_vente",

                    "produit",

                    "type_stock"

                ],

                name="stock_unique"

            )

        ]

        indexes = [

            models.Index(
                fields=["point_vente"]
            ),

            models.Index(
                fields=["produit"]
            ),

            models.Index(
                fields=["type_stock"]
            ),

        ]

    def __str__(self):

        return (

            f"{self.point_vente}"

            f" - "

            f"{self.produit}"

            f" ({self.type_stock})"

        )