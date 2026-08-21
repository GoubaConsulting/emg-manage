"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Formulaires du module Situations.

==========================================================
"""

from django import forms
from django.db.models import Q
from django.utils import timezone

from referentiel.models import Distributeur


# ==========================================================
# FORMULAIRE : SELECTION D'UNE SITUATION
# ==========================================================


class DistributeurSituationChoiceField(forms.ModelChoiceField):
    """
    Affiche les personnes selectionnables avec leur categorie.
    """

    def label_from_instance(self, obj):

        return (
            f"{obj.nom} {obj.prenom} - "
            f"{obj.get_categorie_display()}"
        )


class SelectionSituationForm(forms.Form):
    """
    Permet de sélectionner la personne concernée
    et la date de la situation journalière.

    Directeur :
        sélectionne tous les gérants actifs et les
        distributeurs actifs de son point de vente,
        hors clients directs.

    Gérant :
        sélectionne un distributeur de son
        point de vente.
    """

    distributeur = DistributeurSituationChoiceField(

        queryset=Distributeur.objects.none(),

        empty_label="Sélectionner",

        label="Distributeur / Gérant",

        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        )

    )

    date_situation = forms.DateField(

        label="Date",

        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        )

    )

    def __init__(
        self,
        *args,
        utilisateur=None,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        if utilisateur is None:
            return

        profil = utilisateur.profil

        # ==================================================
        # GERANT
        # ==================================================

        if profil.role == "GERANT":

            self.fields[
                "distributeur"
            ].label = "Distributeur"

            self.fields[
                "distributeur"
            ].queryset = (

                Distributeur.objects

                .filter(

                    actif=True,

                    categorie=(
                        Distributeur.CATEGORIE_DISTRIBUTEUR
                    ),

                    point_vente=profil.point_vente,

                )

                .order_by(
                    "nom",
                    "prenom",
                )

            )

        # ==================================================
        # DIRECTEUR
        # ==================================================

        elif profil.role == "DIRECTEUR":

            self.fields[
                "distributeur"
            ].label = "Gérant / Distributeur"

            self.fields[
                "distributeur"
            ].queryset = (

                Distributeur.objects

                .filter(

                    actif=True,

                )

                .filter(
                    Q(
                        categorie=(
                            Distributeur.CATEGORIE_GERANT
                        )
                    )
                    |
                    Q(
                        categorie=(
                            Distributeur.CATEGORIE_DISTRIBUTEUR
                        ),
                        point_vente=profil.point_vente,
                    )
                )

                .select_related(
                    "point_vente"
                )

                .order_by(

                    "nom",

                    "prenom",

                )

            )


# ==========================================================
# FORMULAIRE : REGLEMENT D'UN MANQUANT
# ==========================================================

class ReglementManquantForm(forms.Form):
    """
    Permet d'enregistrer un règlement partiel ou total
    d'un manquant.
    """

    date_reglement = forms.DateField(

        label="Date de règlement",

        initial=timezone.localdate,

        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        )

    )

    montant = forms.DecimalField(

        label="Montant versé",

        max_digits=18,

        decimal_places=2,

        min_value=1,

        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
                "step": "0.01",
            }
        )

    )
