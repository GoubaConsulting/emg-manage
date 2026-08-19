from django import forms
from .models import PointVente, Compagnie, Produit, Distributeur

class PointVenteForm(forms.ModelForm):

    class Meta:

        model = PointVente

        fields = [
            'designation',
            'adresse'
        ]

        widgets = {

            'designation': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'adresse': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

        }


class CompagnieForm(forms.ModelForm):
    """
    Formulaire Compagnie
    """

    class Meta:

        model = Compagnie

        fields = [
            'designation'
        ]

        widgets = {

            'designation': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Désignation de la compagnie'
                }
            )

        }


# ==========================================
# FORMULAIRE PRODUIT
# ==========================================

class ProduitForm(forms.ModelForm):
    """
    Formulaire Produit
    """

    class Meta:

        model = Produit

        fields = [
            'designation',
            'prix',
            'compagnie'
        ]

        widgets = {

            'designation': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Désignation du produit'
                }
            ),

            'prix': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Prix'
                }
            ),

            'compagnie': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            )

        }


# ==========================================
# FORMULAIRE DISTRIBUTEUR
# ==========================================

class DistributeurForm(forms.ModelForm):
    """
    Formulaire Distributeur
    """

    class Meta:

        model = Distributeur

        fields = [
            'nom',
            'prenom',
            'telephone',
            'fond',
            'categorie',
            'point_vente'
        ]

        widgets = {


            'nom': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'prenom': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'telephone': forms.TextInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'fond': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'step': '0.01',
                    'placeholder': 'Fond'
                }
            ),

            'categorie': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'point_vente': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            )

        }

    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.fields["point_vente"].queryset = (
            PointVente.objects.filter(
                actif=True
            ).order_by(
                "designation"
            )
        )

    def clean_fond(self):

        fond = self.cleaned_data.get(
            'fond'
        )

        if fond is not None and fond < 0:

            raise forms.ValidationError(
                "Le fond ne peut pas être négatif."
            )

        return fond
