from django import forms
from django.utils import timezone

from referentiel.models import (
    Compagnie,
    Produit
)

from .models import Objectif


class ObjectifForm(forms.Form):
    """
    Formulaire de création d'un objectif.

    Ce formulaire ne correspond pas directement
    au modèle Objectif car il permet également
    de sélectionner plusieurs produits.
    """

    # ============================
    # Compagnie
    # ============================

    compagnie = forms.ModelChoiceField(

        queryset=Compagnie.objects.filter(
            actif=True
        ).order_by(
            "designation"
        ),

        empty_label="Sélectionner une compagnie",

        widget=forms.Select(

            attrs={
                "class": "form-select",
                "id": "id_compagnie"
            }

        )

    )

    # ============================
    # Mois
    # ============================

    MOIS = (

        (1, "Janvier"),
        (2, "Février"),
        (3, "Mars"),
        (4, "Avril"),
        (5, "Mai"),
        (6, "Juin"),
        (7, "Juillet"),
        (8, "Août"),
        (9, "Septembre"),
        (10, "Octobre"),
        (11, "Novembre"),
        (12, "Décembre"),

    )

    mois = forms.ChoiceField(

        choices=MOIS,

        widget=forms.Select(

            attrs={
                "class": "form-select"
            }

        )

    )

    # ============================
    # Année
    # ============================

    ANNEES = [

        (annee, annee)

        for annee in range(
            timezone.now().year,
            timezone.now().year + 6
        )

    ]

    annee = forms.ChoiceField(

        choices=ANNEES,

        widget=forms.Select(

            attrs={
                "class": "form-select"
            }

        )

    )

    # ============================
    # Montant cible
    # ============================

    montant_cible = forms.DecimalField(

        max_digits=18,

        decimal_places=2,

        min_value=1,

        widget=forms.NumberInput(

            attrs={

                "class": "form-control",

                "placeholder":
                "Montant cible"

            }

        )

    )

    # ============================
    # Produits
    # ============================

    produits = forms.ModelMultipleChoiceField(

        queryset=Produit.objects.none(),

        required=False,

        widget=forms.CheckboxSelectMultiple

    )

    # ===================================================
    # Constructeur
    # ===================================================

    def __init__(

        self,

        *args,

        **kwargs

    ):

        super().__init__(*args, **kwargs)

        compagnie = None

        # -------------------------------
        # Cas POST
        # -------------------------------

        if "compagnie" in self.data:

            try:

                compagnie = int(

                    self.data.get(
                        "compagnie"
                    )

                )

            except Exception:

                compagnie = None

        # -------------------------------
        # Cas Modification
        # -------------------------------

        elif self.initial.get("compagnie"):

            compagnie = self.initial[
                "compagnie"
            ]

        # -------------------------------
        # Chargement des produits
        # -------------------------------

        if compagnie:

            self.fields[
                "produits"
            ].queryset = (

                Produit.objects.filter(

                    compagnie_id=compagnie,

                    actif=True

                ).order_by(

                    "designation"

                )

            )

    