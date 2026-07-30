from django.db import models
from django.contrib.auth.models import User
from referentiel.models import PointVente


class ProfilUtilisateur(models.Model):

    ROLE_CHOICES = (
        ('ADMIN', 'Administrateur'),
        ('DIRECTEUR', 'Directeur'),
        ('GERANT', 'Gérant'),
    )

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil'
    )

    nom = models.CharField(
        max_length=100
    )

    prenom = models.CharField(
        max_length=100
    )

    telephone = models.CharField(
        max_length=30
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    point_vente = models.ForeignKey(
        PointVente,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "profilutilisateur"

    def __str__(self):
        return f"{self.nom} {self.prenom}"
    

