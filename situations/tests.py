from decimal import Decimal
from datetime import date

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from comptes.models import ProfilUtilisateur
from distributions.models import Distribution, LigneDistribution
from distributions.views import montants_initiaux_destinataire
from referentiel.models import Compagnie, Distributeur, PointVente, Produit

from .models import SituationJournaliere
from .selectors import distributions_du_jour
from .services import (
    cloturer_situation,
    creer_situation_journaliere,
    montants_initiaux_commande_gerant,
    soumettre_versement_gerant,
    valider_versement_gerant,
)

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


class VersementsMultiplesMemeJourTests(TestCase):

    def setUp(self):
        self.date_situation = date(2026, 10, 1)
        self.direction = PointVente.objects.create(
            designation="Direction", adresse="Centre"
        )
        self.point_vente = PointVente.objects.create(
            designation="Agence", adresse="Centre"
        )
        self.directeur = User.objects.create_user(username="directeur")
        ProfilUtilisateur.objects.create(
            utilisateur=self.directeur,
            nom="Directeur",
            prenom="Test",
            telephone="1",
            role="DIRECTEUR",
            point_vente=self.direction,
        )
        self.utilisateur_gerant = User.objects.create_user(username="gerant")
        ProfilUtilisateur.objects.create(
            utilisateur=self.utilisateur_gerant,
            nom="Gerant",
            prenom="Test",
            telephone="2",
            role="GERANT",
            point_vente=self.point_vente,
        )
        self.gerant = Distributeur.objects.create(
            nom="Gerant", prenom="Test", categorie=Distributeur.CATEGORIE_GERANT,
            point_vente=self.point_vente,
        )
        compagnie = Compagnie.objects.create(designation="Compagnie test")
        self.produit = Produit.objects.create(
            designation="Carte test", prix=Decimal("500.00"), compagnie=compagnie
        )

    def creer_distribution(
        self, numero, quantite, date_distribution=None, destinataire=None,
    ):
        montant = Decimal("500.00") * quantite
        destinataire = destinataire or self.gerant
        distribution = Distribution.objects.create(
            numero=numero,
            type_distribution=(
                Distribution.TYPE_COMMANDE_GERANT
                if destinataire.categorie == Distributeur.CATEGORIE_GERANT
                else Distribution.TYPE_DISTRIBUTEUR
            ),
            point_vente_source=self.direction,
            point_vente_destination=destinataire.point_vente,
            utilisateur=self.directeur,
            distributeur=destinataire,
            date_distribution=date_distribution or self.date_situation,
            montant_brut=montant,
            montant_net=montant,
        )
        LigneDistribution.objects.create(
            distribution=distribution,
            produit=self.produit,
            prix_unitaire=Decimal("500.00"),
            montant=montant,
            quantite=quantite,
            taux_remise=Decimal("0.00"),
            montant_net=montant,
        )
        return distribution

    def verser_total(self, situation, utilisateur, soumettre):
        donnees = {
            str(ligne.pk): {"montant_restant": "0"}
            for ligne in situation.lignes.all()
        }
        fonction = soumettre_versement_gerant if soumettre else cloturer_situation
        return fonction(
            situation=situation,
            donnees_lignes=donnees,
            montant_total_verse=situation.montant_total_distribue,
            coupures={},
            utilisateur=utilisateur,
        )

    def test_versement_direct_accepte_un_montant_restant_non_multiple(self):
        self.creer_distribution("DIS-TEST-LIBRE-1", Decimal("2"))
        situation = creer_situation_journaliere(
            self.gerant, self.date_situation, self.directeur
        )
        ligne = situation.lignes.get()

        cloturer_situation(
            situation=situation,
            donnees_lignes={str(ligne.pk): {"montant_restant": "501"}},
            montant_total_verse="499",
            coupures={},
            utilisateur=self.directeur,
        )

        ligne.refresh_from_db()
        self.assertEqual(ligne.montant_restant_brut, Decimal("501"))
        self.assertEqual(ligne.brut_restant_effectif, Decimal("501"))
        self.assertEqual(situation.montant_manquant, 0)
        self.assertEqual(
            montants_initiaux_commande_gerant(self.utilisateur_gerant)[self.produit.pk],
            Decimal("501"),
        )
        initiaux_distribution = montants_initiaux_destinataire(
            self.gerant, date(2026, 10, 2)
        )
        self.assertEqual(
            initiaux_distribution[str(self.produit.pk)]["brut"], 501.0
        )

    def test_versement_gerant_accepte_un_montant_restant_non_multiple(self):
        self.creer_distribution("DIS-TEST-LIBRE-2", Decimal("2"))
        situation = creer_situation_journaliere(
            self.gerant, self.date_situation, self.utilisateur_gerant
        )
        ligne = situation.lignes.get()

        soumettre_versement_gerant(
            situation=situation,
            donnees_lignes={str(ligne.pk): {"montant_restant": "501"}},
            montant_total_verse="499",
            coupures={},
            utilisateur=self.utilisateur_gerant,
        )

        ligne.refresh_from_db()
        self.assertEqual(ligne.montant_restant_brut, Decimal("501"))
        self.assertEqual(situation.montant_manquant, 0)
        valider_versement_gerant(situation, self.directeur)
        self.assertEqual(
            montants_initiaux_commande_gerant(self.utilisateur_gerant)[self.produit.pk],
            Decimal("501"),
        )

    def test_deux_versements_en_attente_ont_des_distributions_distinctes(self):
        premiere = self.creer_distribution("DIS-TEST-1", Decimal("2"))
        versement_1 = creer_situation_journaliere(
            self.gerant, self.date_situation, self.utilisateur_gerant
        )
        self.verser_total(versement_1, self.utilisateur_gerant, soumettre=True)

        deuxieme = self.creer_distribution("DIS-TEST-2", Decimal("1"))
        troisieme = self.creer_distribution("DIS-TEST-3", Decimal("3"))
        libres = list(distributions_du_jour(self.gerant, self.date_situation))
        self.assertEqual({item.pk for item in libres}, {deuxieme.pk, troisieme.pk})

        versement_2 = creer_situation_journaliere(
            self.gerant, self.date_situation, self.utilisateur_gerant
        )
        self.verser_total(versement_2, self.utilisateur_gerant, soumettre=True)

        self.assertNotEqual(versement_1.pk, versement_2.pk)
        self.assertEqual(versement_1.montant_total_distribue, Decimal("1000"))
        self.assertEqual(versement_2.montant_total_distribue, Decimal("2000"))
        self.assertEqual(Distribution.objects.filter(situation=versement_1).count(), 1)
        self.assertEqual(Distribution.objects.filter(situation=versement_2).count(), 2)

        valider_versement_gerant(versement_1, self.directeur)
        premiere.refresh_from_db()
        deuxieme.refresh_from_db()
        self.assertEqual(premiere.etat, Distribution.ETAT_CLOTUREE)
        self.assertEqual(deuxieme.etat, Distribution.ETAT_OUVERTE)

        valider_versement_gerant(versement_2, self.directeur)
        deuxieme.refresh_from_db()
        troisieme.refresh_from_db()
        self.assertEqual(deuxieme.etat, Distribution.ETAT_CLOTUREE)
        self.assertEqual(troisieme.etat, Distribution.ETAT_CLOTUREE)

    def test_deux_versements_directs_le_meme_jour(self):
        premiere = self.creer_distribution("DIS-TEST-4", Decimal("2"))
        versement_1 = creer_situation_journaliere(
            self.gerant, self.date_situation, self.directeur
        )
        self.verser_total(versement_1, self.directeur, soumettre=False)

        deuxieme = self.creer_distribution("DIS-TEST-5", Decimal("1"))
        versement_2 = creer_situation_journaliere(
            self.gerant, self.date_situation, self.directeur
        )
        self.verser_total(versement_2, self.directeur, soumettre=False)

        premiere.refresh_from_db()
        deuxieme.refresh_from_db()
        self.assertEqual(versement_1.etat, versement_1.ETAT_CLOTUREE)
        self.assertEqual(versement_2.etat, versement_2.ETAT_CLOTUREE)
        self.assertEqual(premiere.situation_id, versement_1.pk)
        self.assertEqual(deuxieme.situation_id, versement_2.pk)

    def test_distributeur_peut_avoir_deux_versements_le_meme_jour(self):
        distributeur = Distributeur.objects.create(
            nom="Distributeur", prenom="Test",
            code="DIST-TEST",
            categorie=Distributeur.CATEGORIE_DISTRIBUTEUR,
            point_vente=self.direction,
        )
        premiere = self.creer_distribution(
            "DIS-TEST-D1", Decimal("2"), destinataire=distributeur
        )
        versement_1 = creer_situation_journaliere(
            distributeur, self.date_situation, self.directeur
        )
        self.verser_total(versement_1, self.directeur, soumettre=False)

        deuxieme = self.creer_distribution(
            "DIS-TEST-D2", Decimal("1"), destinataire=distributeur
        )
        versement_2 = creer_situation_journaliere(
            distributeur, self.date_situation, self.directeur
        )
        self.verser_total(versement_2, self.directeur, soumettre=False)

        premiere.refresh_from_db()
        deuxieme.refresh_from_db()
        self.assertEqual(premiere.situation_id, versement_1.pk)
        self.assertEqual(deuxieme.situation_id, versement_2.pk)
        self.assertEqual(versement_2.montant_total_distribue, Decimal("500"))

    def test_refuse_un_lot_change_depuis_la_recherche(self):
        premiere = self.creer_distribution("DIS-TEST-LOT1", Decimal("2"))
        self.client.force_login(self.utilisateur_gerant)
        recherche = self.client.post(
            reverse("situations:versement_gerant") + "?nouveau=1",
            {"date_situation": self.date_situation.isoformat()},
        )
        self.assertEqual(recherche.status_code, 200)

        deuxieme = self.creer_distribution("DIS-TEST-LOT2", Decimal("1"))
        soumission = self.client.post(
            reverse("situations:versement_gerant"),
            {
                "action": "soumettre_versement_gerant",
                "date_situation": self.date_situation.isoformat(),
                "distribution_ids": [str(premiere.pk)],
                f"montant_restant_{self.produit.pk}": "0",
                "montant_total_verse": "1000",
            },
        )

        self.assertEqual(soumission.status_code, 200)
        self.assertEqual(SituationJournaliere.objects.count(), 0)
        premiere.refresh_from_db()
        deuxieme.refresh_from_db()
        self.assertIsNone(premiere.situation_id)
        self.assertIsNone(deuxieme.situation_id)

    def test_recherche_gerant_affiche_uniquement_les_nouvelles_distributions(self):
        premiere = self.creer_distribution("DIS-TEST-6", Decimal("2"))
        versement_1 = creer_situation_journaliere(
            self.gerant, self.date_situation, self.utilisateur_gerant
        )
        self.verser_total(versement_1, self.utilisateur_gerant, soumettre=True)
        deuxieme = self.creer_distribution("DIS-TEST-7", Decimal("1"))

        self.client.force_login(self.utilisateur_gerant)
        reponse = self.client.post(
            reverse("situations:versement_gerant") + "?nouveau=1",
            {"date_situation": self.date_situation.isoformat()},
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            [item.pk for item in reponse.context["distributions"]],
            [deuxieme.pk],
        )
        self.assertEqual(reponse.context["situation"].idsituation, "")
        premiere.refresh_from_db()
        self.assertEqual(premiere.situation_id, versement_1.pk)

        soumission = self.client.post(
            reverse("situations:versement_gerant"),
            {
                "action": "soumettre_versement_gerant",
                "idsituation": "",
                "date_situation": self.date_situation.isoformat(),
                "distribution_ids": [str(deuxieme.pk)],
                f"montant_restant_{self.produit.pk}": "0",
                "montant_total_verse": "500",
            },
        )
        self.assertEqual(soumission.status_code, 302)
        deuxieme.refresh_from_db()
        versement_1.refresh_from_db()
        self.assertEqual(versement_1.montant_total_verse, Decimal("1000"))
        self.assertEqual(versement_1.etat, versement_1.ETAT_ATTENTE_VALIDATION)
        self.assertNotEqual(deuxieme.situation_id, versement_1.pk)
        self.assertEqual(
            deuxieme.situation.etat, deuxieme.situation.ETAT_ATTENTE_VALIDATION
        )

    def test_gerant_peut_soumettre_apres_un_versement_valide(self):
        self.creer_distribution("DIS-TEST-VAL1", Decimal("2"))
        premier = creer_situation_journaliere(
            self.gerant, self.date_situation, self.utilisateur_gerant
        )
        self.verser_total(premier, self.utilisateur_gerant, soumettre=True)
        valider_versement_gerant(premier, self.directeur)
        deuxieme = self.creer_distribution("DIS-TEST-VAL2", Decimal("1"))

        self.client.force_login(self.utilisateur_gerant)
        recherche = self.client.post(
            reverse("situations:versement_gerant") + "?nouveau=1",
            {"date_situation": self.date_situation.isoformat()},
        )
        self.assertEqual(recherche.status_code, 200)
        self.assertEqual(
            [item.pk for item in recherche.context["distributions"]],
            [deuxieme.pk],
        )

        soumission = self.client.post(
            reverse("situations:versement_gerant"),
            {
                "action": "soumettre_versement_gerant",
                "date_situation": self.date_situation.isoformat(),
                "distribution_ids": [str(deuxieme.pk)],
                f"montant_restant_{self.produit.pk}": "0",
                "montant_total_verse": "500",
            },
        )
        self.assertEqual(soumission.status_code, 302)
        deuxieme.refresh_from_db()
        premier.refresh_from_db()
        self.assertEqual(premier.etat, premier.ETAT_CLOTUREE)
        self.assertNotEqual(deuxieme.situation_id, premier.pk)
        self.assertEqual(deuxieme.situation.etat, premier.ETAT_ATTENTE_VALIDATION)

    def test_recherche_directeur_apres_un_versement_cloture(self):
        self.creer_distribution("DIS-TEST-8", Decimal("2"))
        versement_1 = creer_situation_journaliere(
            self.gerant, self.date_situation, self.directeur
        )
        self.verser_total(versement_1, self.directeur, soumettre=False)
        deuxieme = self.creer_distribution("DIS-TEST-9", Decimal("1"))

        self.client.force_login(self.directeur)
        reponse = self.client.post(
            reverse("situations:ajouter_situation"),
            {
                "distributeur": self.gerant.pk,
                "date_situation": self.date_situation.isoformat(),
            },
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            [item.pk for item in reponse.context["distributions"]],
            [deuxieme.pk],
        )
        self.assertEqual(reponse.context["situation"].idsituation, "")

    def test_restants_de_deux_versements_repris_une_fois_le_lendemain(self):
        veille = date(2026, 9, 30)
        self.creer_distribution("DIS-TEST-10", Decimal("2"), veille)
        premier = creer_situation_journaliere(
            self.gerant, veille, self.directeur
        )
        ligne = premier.lignes.get()
        cloturer_situation(
            situation=premier,
            donnees_lignes={str(ligne.pk): {"montant_restant": "500"}},
            montant_total_verse="500",
            coupures={},
            utilisateur=self.directeur,
        )

        self.creer_distribution("DIS-TEST-11", Decimal("2"), veille)
        second = creer_situation_journaliere(self.gerant, veille, self.directeur)
        ligne = second.lignes.get()
        cloturer_situation(
            situation=second,
            donnees_lignes={str(ligne.pk): {"montant_restant": "500"}},
            montant_total_verse="500",
            coupures={},
            utilisateur=self.directeur,
        )

        self.assertEqual(
            montants_initiaux_commande_gerant(self.utilisateur_gerant)[self.produit.pk],
            Decimal("1000"),
        )

        self.creer_distribution("DIS-TEST-12", Decimal("1"))
        nouveau = creer_situation_journaliere(
            self.gerant, self.date_situation, self.directeur
        )
        self.assertEqual(nouveau.montant_total_distribue, Decimal("1500"))
        self.assertEqual(nouveau.lignes.get().quantite_distribuee, Decimal("3"))

        self.creer_distribution("DIS-TEST-13", Decimal("1"))
        suivant = creer_situation_journaliere(
            self.gerant, self.date_situation, self.directeur
        )
        self.assertEqual(suivant.montant_total_distribue, Decimal("500"))
