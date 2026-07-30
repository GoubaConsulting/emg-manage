from django.db import models




# model point de vente
class PointVente(models.Model):

    # Clé primaire
    idpointvente = models.AutoField(
        primary_key=True
    )

    designation = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Désignation"
    )

    adresse = models.CharField(
        max_length=255,
        verbose_name="Adresse"
    )

    # Suppression logique
    actif = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )

    # Audit
    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "pointvente"
        ordering = ['designation']
        verbose_name = "Point de vente"
        verbose_name_plural = "Points de vente"

    def __str__(self):
        return self.designation

# model compagnie
class Compagnie(models.Model):
    """
    Référentiel des compagnies.
    Une compagnie possède plusieurs produits.
    """

    idcompagnie = models.AutoField(
        primary_key=True
    )

    designation = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Désignation"
    )

    # Suppression logique
    actif = models.BooleanField(
        default=True
    )

    # Audit
    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = 'compagnie'

        ordering = [
            'designation'
        ]

        verbose_name = 'Compagnie'

        verbose_name_plural = 'Compagnies'

    def __str__(self):
        return self.designation

# ==========================================
# MODELE PRODUIT
# ==========================================

class Produit(models.Model):
    """
    Référentiel des produits.

    Chaque produit appartient à une seule compagnie.
    """

    # Clé primaire
    idproduit = models.AutoField(
        primary_key=True
    )

    designation = models.CharField(
        max_length=150,
        verbose_name="Désignation"
    )

    prix = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Prix"
    )

    compagnie = models.ForeignKey(
        Compagnie,
        on_delete=models.PROTECT,
        related_name='produits',
        verbose_name="Compagnie"
    )

    # Suppression logique
    actif = models.BooleanField(
        default=True
    )

    # Audit
    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "produit"

        ordering = [
            'designation'
        ]

        verbose_name = "Produit"

        verbose_name_plural = "Produits"

    def __str__(self):

        return self.designation
    
# ==========================================
# MODELE DISTRIBUTEUR
# ==========================================

class Distributeur(models.Model):

    CATEGORIE_GERANT = "GERANT"

    CATEGORIE_DISTRIBUTEUR = "DISTRIBUTEUR"

    CATEGORIE_CLIENT = "CLIENT"

    CATEGORIES = [

        (
            CATEGORIE_GERANT,
            "Gérant"
        ),

        (
            CATEGORIE_DISTRIBUTEUR,
            "Distributeur"
        ),

        (
            CATEGORIE_CLIENT,
            "Client"
        ),

    ]

    """
    Référentiel des distributeurs.
    Chaque distributeur est rattaché à un point de vente.
    """
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIES,
        default=CATEGORIE_DISTRIBUTEUR,
        verbose_name="Catégorie"
    )

    iddistributeur = models.AutoField(
        primary_key=True
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    nom = models.CharField(
        max_length=100,
        verbose_name="Nom"
    )

    prenom = models.CharField(
        max_length=100,
        verbose_name="Prénom"
    )

    telephone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Téléphone"
    )

    point_vente = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        related_name='distributeurs',
        verbose_name="Point de vente"
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

        db_table = "distributeur"

        ordering = [
            'nom',
            'prenom'
        ]

        verbose_name = "Distributeur"

        verbose_name_plural = "Distributeurs"

   
    def __str__(self):

        return f"{self.code} - {self.nom} {self.prenom}"


