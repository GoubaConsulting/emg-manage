"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Formulaire de création et de modification
des distributions.

==========================================================
"""

from django import forms
from django.utils import timezone

from .models import Distribution


class DistributionForm(forms.ModelForm):
    """
    Formulaire de l'en-tête d'une distribution.

    Les lignes de distribution (produits)
    sont générées dynamiquement
    dans le template.
    """

    TYPE_OPERATION = (
        ("DIST", "Distribution"),
        ("VENTE", "Vente"),
    )

    type_operation = forms.ChoiceField(
        choices=TYPE_OPERATION,
        widget=forms.RadioSelect,
        initial="DIST",
        required=False,
    )

    class Meta:

        model = Distribution

        fields = [

            "commande",

            "distributeur",

            "date_distribution",

        ]

        widgets = {

            "date_distribution": forms.DateInput(

                attrs={

                    "class": "form-control",

                    "type": "date"

                }

            ),

            "type_distribution": forms.Select(

                attrs={

                    "class": "form-select"

                }

            ),

            "commande": forms.Select(

                attrs={

                    "class": "form-select"

                }

            ),

            "point_vente_destination": forms.Select(

                attrs={

                    "class": "form-select"

                }

            ),

            "distributeur": forms.Select(

                attrs={

                    "class": "form-select"

                }

            ),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if not self.instance.pk:

            self.fields["date_distribution"].initial = timezone.now().date()