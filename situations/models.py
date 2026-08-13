"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Modèles des situations journalières,
des manquants et des règlements de manquants.

==========================================================
"""

from django.db import models

from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)

from django.contrib.auth.models import User

from referentiel.models import (
    PointVente,
    Produit,
    Distributeur,
)


# ==========================================================
# MODELE : SITUATION JOURNALIERE
# ==========================================================

class SituationJournaliere(models.Model):
    """
    Représente la situation financière et
    produit d'un distributeur pour une journée.
    """

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

    # ======================================================
    # IDENTIFICATION
    # ======================================================

    idsituation = models.AutoField(
        primary_key=True
    )

    numero = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Numéro"
    )

    # ======================================================
    # INFORMATIONS GENERALES
    # ======================================================

    date_situation = models.DateField(
        verbose_name="Date de situation"
    )

    distributeur = models.ForeignKey(
        Distributeur,
        on_delete=models.PROTECT,
        related_name="situations_journalieres",
        verbose_name="Distributeur"
    )

    point_vente = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name="situations_journalieres",
        verbose_name="Point de vente"
    )

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="situations_journalieres",
        verbose_name="Utilisateur"
    )

    # ======================================================
    # FOND
    # ======================================================

    fond = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Fond"
    )

    # ======================================================
    # DISTRIBUTIONS
    # ======================================================

    montant_total_distribue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant total distribué"
    )

    # ======================================================
    # CREDIT
    # ======================================================

    montant_credit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant crédit"
    )

    montant_credit_verse = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Crédit versé"
    )

    # ======================================================
    # VERSEMENT DES VENTES
    # ======================================================

    montant_vente_verse = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant vente versé"
    )

    montant_total_verse = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant total versé"
    )

    # ======================================================
    # MANQUANT
    # ======================================================

    montant_manquant = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant manquant"
    )

    # ======================================================
    # COUPURES
    # ======================================================

    coupures = models.TextField(
        blank=True,
        default="",
        verbose_name="Coupures"
    )

    # ======================================================
    # ETAT
    # ======================================================

    etat = models.CharField(
        max_length=20,
        choices=ETATS,
        default=ETAT_OUVERTE,
        verbose_name="Etat"
    )

    # ======================================================
    # ACTIVITE
    # ======================================================

    actif = models.BooleanField(
        default=True
    )

    # ======================================================
    # DATES
    # ======================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "situationjournaliere"

        verbose_name = "Situation journalière"

        verbose_name_plural = "Situations journalières"

        ordering = [

            "-date_situation",

            "-idsituation"

        ]

        constraints = [

            models.UniqueConstraint(

                fields=[
                    "distributeur",
                    "date_situation",
                ],

                condition=models.Q(
                    actif=True
                ),

                name="situation_unique_distributeur_date_active"

            )

        ]

        indexes = [

            models.Index(
                fields=[
                    "date_situation"
                ]
            ),

            models.Index(
                fields=[
                    "distributeur"
                ]
            ),

            models.Index(
                fields=[
                    "point_vente"
                ]
            ),

            models.Index(
                fields=[
                    "etat"
                ]
            ),

        ]

    def __str__(self):

        return self.numero


# ==========================================================
# MODELE : LIGNE SITUATION JOURNALIERE
# ==========================================================

class LigneSituationJournaliere(models.Model):
    """
    Détail des mouvements de produits
    d'une situation journalière.
    """

    idlignesituation = models.AutoField(
        primary_key=True
    )

    situation = models.ForeignKey(
        SituationJournaliere,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Situation journalière"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT,
        related_name="lignes_situations",
        verbose_name="Produit"
    )

    prix_unitaire = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Prix unitaire"
    )

    taux_remise = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        verbose_name="Taux de remise"
    )

    # ======================================================
    # QUANTITES
    # ======================================================

    quantite_distribuee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Quantité distribuée"
    )

    quantite_vendue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Quantité vendue"
    )

    quantite_restante = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Quantité restante"
    )

    class Meta:

        db_table = "lignesituationjournaliere"

        verbose_name = "Ligne situation journalière"

        verbose_name_plural = "Lignes situation journalière"

        ordering = [

            "produit__designation"

        ]

        constraints = [

            models.UniqueConstraint(

                fields=[
                    "situation",
                    "produit"
                ],

                name="produit_unique_situation"

            )

        ]

    def __str__(self):

        return (

            f"{self.situation.numero}"

            f" - "

            f"{self.produit.designation}"

        )


# ==========================================================
# MODELE : MANQUANT
# ==========================================================

class Manquant(models.Model):
    """
    Représente un montant manquant constaté
    lors d'une situation journalière.
    """

    STATUT_EN_COURS = "EN_COURS"

    STATUT_SOLDE = "SOLDE"

    STATUTS = [

        (
            STATUT_EN_COURS,
            "En cours"
        ),

        (
            STATUT_SOLDE,
            "Soldé"
        ),

    ]

    idmanquant = models.AutoField(
        primary_key=True
    )

    numero = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Numéro"
    )

    # ======================================================
    # SITUATION
    # ======================================================

    situation = models.OneToOneField(
        SituationJournaliere,
        on_delete=models.PROTECT,
        related_name="manquant",
        verbose_name="Situation journalière"
    )

    distributeur = models.ForeignKey(
        Distributeur,
        on_delete=models.PROTECT,
        related_name="manquants",
        verbose_name="Distributeur"
    )

    # ======================================================
    # MONTANTS
    # ======================================================

    montant = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant"
    )

    reste_a_payer = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Reste à payer"
    )

    # ======================================================
    # STATUT
    # ======================================================

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default=STATUT_EN_COURS,
        verbose_name="Statut"
    )

    # ======================================================
    # UTILISATEUR
    # ======================================================

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="manquants",
        verbose_name="Utilisateur"
    )

    # ======================================================
    # DATES
    # ======================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "manquant"

        verbose_name = "Manquant"

        verbose_name_plural = "Manquants"

        ordering = [

            "-date_creation",

            "-idmanquant"

        ]

        indexes = [

            models.Index(
                fields=[
                    "distributeur"
                ]
            ),

            models.Index(
                fields=[
                    "statut"
                ]
            ),

        ]

    def __str__(self):

        return self.numero


# ==========================================================
# MODELE : REGLEMENT MANQUANT
# ==========================================================

class ReglementManquant(models.Model):
    """
    Représente un règlement partiel ou total
    d'un manquant.
    """

    idreglement = models.AutoField(
        primary_key=True
    )

    numero = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Numéro"
    )

    # ======================================================
    # MANQUANT
    # ======================================================

    manquant = models.ForeignKey(
        Manquant,
        on_delete=models.PROTECT,
        related_name="reglements",
        verbose_name="Manquant"
    )

    # ======================================================
    # REGLEMENT
    # ======================================================

    date_reglement = models.DateField(
        verbose_name="Date de règlement"
    )

    montant = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ],
        verbose_name="Montant"
    )

    # ======================================================
    # UTILISATEUR
    # ======================================================

    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="reglements_manquants",
        verbose_name="Utilisateur"
    )

    # ======================================================
    # DATE DE CREATION
    # ======================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = "reglementmanquant"

        verbose_name = "Règlement manquant"

        verbose_name_plural = "Règlements manquants"

        ordering = [

            "-date_reglement",

            "-idreglement"

        ]

        indexes = [

            models.Index(
                fields=[
                    "manquant"
                ]
            ),

            models.Index(
                fields=[
                    "date_reglement"
                ]
            ),

        ]

    def __str__(self):

        return self.numero