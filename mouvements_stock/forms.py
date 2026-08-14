"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Formulaires du module.

==========================================================
"""

from django import forms
from django.utils import timezone

from .models import MouvementStock


class MouvementStockForm(forms.ModelForm):
    """
    Formulaire de l'en-tete d'un mouvement.
    Les lignes produits sont saisies dans le template.
    """

    class Meta:

        model = MouvementStock

        fields = [
            "type_mouvement",
            "type_stock",
            "date_mouvement",
            "motif",
            "observation",
        ]

        widgets = {
            "type_mouvement": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
            "type_stock": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
            "date_mouvement": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "motif": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if not self.instance.pk:

            self.fields["date_mouvement"].initial = (
                timezone.localdate()
            )
