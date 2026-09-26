from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .services import construire_lignes_depuis_formulaire


class ConstructionLignesCommandeTests(SimpleTestCase):

    def setUp(self):
        self.produit = SimpleNamespace(
            idproduit=1,
            designation="Carte 500F",
            prix=Decimal("500.00"),
        )

    def test_accepte_les_decimaux_au_format_francais(self):
        lignes = construire_lignes_depuis_formulaire(
            {
                "produit_1": "1",
                "montant_1": "5 000,00",
                "montant_initial_1": "132\u202f250,00",
                "taux_1": "10,00",
                "taux_initial_1": "5,00",
            },
            [self.produit],
        )

        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["montant"], Decimal("5000.00"))
        self.assertEqual(
            lignes[0]["montant_initial"],
            Decimal("132250.00"),
        )
        self.assertEqual(lignes[0]["taux_remise"], Decimal("10.00"))
        self.assertEqual(lignes[0]["taux_initial"], Decimal("5.00"))

    def test_signale_clairement_une_valeur_invalide(self):
        with self.assertRaisesMessage(
            ValidationError,
            "montant du produit « Carte 500F »",
        ):
            construire_lignes_depuis_formulaire(
                {
                    "produit_1": "1",
                    "montant_1": "montant-invalide",
                },
                [self.produit],
            )
