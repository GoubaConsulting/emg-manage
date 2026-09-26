from decimal import Decimal

from django.test import SimpleTestCase

from .calculs import calculer_credit, ventiler_versement


class VersementUniqueTests(SimpleTestCase):

    def test_vente_complete_le_credit_est_inclus_dans_le_versement(self):
        resultat = ventiler_versement(
            Decimal("1500000"), Decimal("500000"), Decimal("1500000")
        )

        self.assertEqual(resultat["montant_credit_verse"], Decimal("500000"))
        self.assertEqual(resultat["montant_vente_verse"], Decimal("1000000"))
        self.assertEqual(resultat["montant_total_verse"], Decimal("1500000"))
        self.assertEqual(resultat["montant_manquant"], 0)
        self.assertEqual(resultat["montant_surplus"], 0)

    def test_vente_partielle_peut_laisser_un_credit_sans_manquant(self):
        resultat = ventiler_versement(200000, 500000, 200000)

        self.assertEqual(resultat["montant_credit_restant"], 300000)
        self.assertEqual(resultat["montant_vente_verse"], 0)
        self.assertEqual(resultat["montant_manquant"], 0)

    def test_versement_inferieur_au_net_vendu_cree_un_manquant(self):
        resultat = ventiler_versement(1200000, 500000, 1500000)

        self.assertEqual(resultat["montant_manquant"], 300000)
        self.assertEqual(resultat["montant_surplus"], 0)

    def test_versement_superieur_au_net_vendu_cree_un_surplus(self):
        resultat = ventiler_versement(1550000, 500000, 1500000)

        self.assertEqual(resultat["montant_manquant"], 0)
        self.assertEqual(resultat["montant_surplus"], 50000)

    def test_credit_se_base_sur_les_montants_nets(self):
        self.assertEqual(
            calculer_credit(Decimal("1350000"), Decimal("1000000")),
            Decimal("350000"),
        )

    def test_un_versement_negatif_est_refuse(self):
        with self.assertRaises(ValueError):
            ventiler_versement(-1, 0, 0)
