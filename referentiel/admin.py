from django.contrib import admin
from .models import PointVente, Compagnie, Produit, Distributeur

admin.site.register(PointVente)
admin.site.register(Compagnie)
admin.site.register(Produit)
admin.site.register(Distributeur)