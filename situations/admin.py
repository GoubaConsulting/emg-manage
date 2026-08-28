from django.contrib import admin

from .models import (
    SituationGerant,
    LigneSituationGerant,
)


class LigneSituationGerantInline(admin.TabularInline):

    model = LigneSituationGerant

    extra = 0

    readonly_fields = (
        "produit",
        "prix_unitaire",
        "montant_residuel_j_1",
        "montant_du_jour",
        "total_du_jour",
        "montant_distribue",
        "montant_vendu",
        "montant_retour",
        "total_vendu",
        "total_restant",
    )


@admin.register(SituationGerant)
class SituationGerantAdmin(admin.ModelAdmin):

    list_display = (
        "numero",
        "date_situation",
        "point_vente",
        "gerant",
        "total_du_jour",
        "total_vendu",
        "total_restant",
    )

    list_filter = (
        "date_situation",
        "point_vente",
    )

    search_fields = (
        "numero",
        "point_vente__designation",
        "gerant__nom",
        "gerant__prenom",
    )

    inlines = [
        LigneSituationGerantInline,
    ]
