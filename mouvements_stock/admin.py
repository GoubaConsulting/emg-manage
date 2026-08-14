from django.contrib import admin

from .models import (
    LigneMouvementStock,
    MouvementStock,
)


class LigneMouvementStockInline(admin.TabularInline):

    model = LigneMouvementStock

    extra = 0


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):

    list_display = (
        "numero",
        "date_mouvement",
        "type_mouvement",
        "type_stock",
        "point_vente",
        "total_quantite",
        "utilisateur",
    )

    list_filter = (
        "type_mouvement",
        "type_stock",
        "date_mouvement",
        "point_vente",
    )

    search_fields = (
        "numero",
        "observation",
    )

    inlines = [
        LigneMouvementStockInline
    ]
