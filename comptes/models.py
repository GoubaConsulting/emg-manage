from django.db import models
from django.contrib.auth.models import User
from referentiel.models import PointVente
from referentiel.models import Distributeur


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


class CorrectionApercu(models.Model):
    operation_type = models.CharField(max_length=40)
    operation_numero = models.CharField(max_length=30)
    gerant = models.ForeignKey(Distributeur, on_delete=models.PROTECT)
    directeur = models.ForeignKey(User, on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)
    motif = models.TextField()
    anciennes_valeurs = models.JSONField()
    nouvelles_valeurs = models.JSONField()
    lien_operation = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-date_creation", "-pk"]


class NotificationCorrection(models.Model):
    correction = models.ForeignKey(
        CorrectionApercu, on_delete=models.CASCADE, related_name="notifications"
    )
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE)
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-correction__date_creation", "-pk"]
    

