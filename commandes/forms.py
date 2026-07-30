"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Formulaire de création et de modification
des commandes.

==========================================================
"""

from django import forms
from django.utils import timezone


class CommandeForm(forms.Form):
    """
    Formulaire de l'en-tête d'une commande.

    Les lignes de commande (produits)
    sont générées dynamiquement
    dans le template.
    """

    date_commande = forms.DateField(

        label="Date de la commande",

        initial=timezone.now,

        widget=forms.DateInput(

            attrs={

                "class": "form-control",

                "type": "date"

            }

        )

    )