"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Formulaires du module Situations.

==========================================================
"""

from django import forms

from referentiel.models import Distributeur

from distributions.models import Distribution


# ==========================================================
# FORMULAIRE : SELECTION D'UNE SITUATION
# ==========================================================

class SelectionSituationForm(forms.Form):
    """
    Permet de sélectionner la personne concernée
    et la date de la situation journalière.

    Directeur :
        sélectionne un gérant auquel il a fait
        une ou plusieurs distributions.

    Gérant :
        sélectionne un distributeur de son
        point de vente.
    """

    distributeur = forms.ModelChoiceField(

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
            ].label = "Gérant"

            gerants_ids = (

                Distribution.objects

                .filter(

                    utilisateur=utilisateur,

                    distributeur__categorie=(
                        Distributeur.CATEGORIE_GERANT
                    ),

                    actif=True,

                )

                .values_list(

                    "distributeur_id",

                    flat=True

                )

                .distinct()

            )

            self.fields[
                "distributeur"
            ].queryset = (

                Distributeur.objects

                .filter(

                    iddistributeur__in=gerants_ids,

                    actif=True,

                    categorie=(
                        Distributeur.CATEGORIE_GERANT
                    ),

                )

                .select_related(
                    "point_vente"
                )

                .order_by(

                    "point_vente__designation",

                    "nom",

                    "prenom",

                )

            )