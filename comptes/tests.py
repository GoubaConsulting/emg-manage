from django.test import TestCase
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from commandes.models import Commande, LigneCommande
from distributions.models import Distribution, LigneDistribution
from referentiel.models import Compagnie, Distributeur, PointVente, Produit
from situations.models import Manquant, ReglementManquant, SituationJournaliere
from situations.services import creer_situation_journaliere, cloturer_situation
from situations.services import synchroniser_situation_vente_directe
from stocks.models import Stock

from .models import CorrectionApercu, NotificationCorrection, ProfilUtilisateur


class CorrectionCommandeApercuTests(TestCase):
    def setUp(self):
        direction = PointVente.objects.create(designation="Direction", adresse="Centre")
        agence = PointVente.objects.create(designation="Agence", adresse="Centre")
        self.directeur = User.objects.create_user(username="directeur-test")
        self.gerant_user = User.objects.create_user(username="gerant-test")
        ProfilUtilisateur.objects.create(
            utilisateur=self.directeur, nom="Directeur", prenom="Test",
            telephone="1", role="DIRECTEUR", point_vente=direction,
        )
        ProfilUtilisateur.objects.create(
            utilisateur=self.gerant_user, nom="Gerant", prenom="Test",
            telephone="2", role="GERANT", point_vente=agence,
        )
        self.gerant = Distributeur.objects.create(
            nom="Gerant", prenom="Test", categorie=Distributeur.CATEGORIE_GERANT,
            point_vente=agence, fond=Decimal("1000"),
        )
        compagnie = Compagnie.objects.create(designation="Test")
        self.produit = Produit.objects.create(
            designation="Carte", prix=Decimal("500"), compagnie=compagnie,
        )
        self.commande = Commande.objects.create(
            numero="CMD-APERCU-1", type_commande=Commande.TYPE_GERANT,
            categorie_commande=Commande.CATEGORIE_NORMALE,
            date_commande=timezone.localdate(), point_vente=agence,
            utilisateur=self.gerant_user, montant_brut=Decimal("500"),
            montant_net=Decimal("500"),
        )
        LigneCommande.objects.create(
            commande=self.commande, produit=self.produit,
            prix_unitaire=Decimal("500"), montant=Decimal("500"),
            quantite=Decimal("1"), montant_net=Decimal("500"),
            montant_total_brut=Decimal("500"), montant_total_net=Decimal("500"),
        )
        self.url = reverse("corriger_commande_directeur", args=[self.commande.pk])
        self.apercu = reverse("apercu_directeur")

    def test_bouton_et_formulaire_premplis(self):
        self.client.force_login(self.directeur)
        reponse = self.client.get(self.apercu, {"gerant": self.gerant.pk})
        self.assertContains(reponse, self.url)
        formulaire = self.client.get(self.url)
        self.assertEqual(formulaire.status_code, 200)
        self.assertContains(formulaire, 'name="motif_correction"')
        self.assertContains(formulaire, 'name="montant_%s"' % self.produit.pk)
        self.assertContains(formulaire, 'value="500.00"')

    def test_motif_obligatoire_et_notification_apres_succes(self):
        self.client.force_login(self.directeur)
        donnees = {
            "date_commande": self.commande.date_commande.isoformat(),
            f"produit_{self.produit.pk}": "1",
            f"montant_{self.produit.pk}": "1000",
            f"taux_{self.produit.pk}": "0",
            "next": f"{self.apercu}?gerant={self.gerant.pk}#commandes",
        }
        invalide = self.client.post(self.url, donnees)
        self.assertEqual(invalide.status_code, 200)
        self.assertEqual(CorrectionApercu.objects.count(), 0)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_brut, Decimal("500"))

        donnees["motif_correction"] = "Erreur de saisie du montant"
        valide = self.client.post(self.url, donnees)
        self.assertEqual(valide.status_code, 302)
        self.assertEqual(valide["Location"], donnees["next"])
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_brut, Decimal("1000"))
        correction = CorrectionApercu.objects.get()
        self.assertEqual(Decimal(correction.anciennes_valeurs["operation"]["montant_brut"]), Decimal("500"))
        self.assertEqual(Decimal(correction.nouvelles_valeurs["operation"]["montant_brut"]), Decimal("1000"))
        notification = NotificationCorrection.objects.get(
            correction=correction, destinataire=self.gerant_user,
        )
        self.client.force_login(self.gerant_user)
        self.assertContains(self.client.get(reverse("notifications_corrections")), correction.motif)
        self.client.post(reverse("ouvrir_notification_correction", args=[notification.pk]))
        notification.refresh_from_db()
        self.assertIsNotNone(notification.date_lecture)

    def test_commande_validee_et_acces_gerant_refuses(self):
        self.client.force_login(self.gerant_user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"motif_correction": "Non"}).status_code, 403)

        self.commande.etat = Commande.VALIDEE
        self.commande.save(update_fields=["etat"])
        self.client.force_login(self.directeur)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        reponse = self.client.get(self.apercu, {"gerant": self.gerant.pk})
        self.assertNotContains(reponse, self.url)

    def creer_distribution_terrain(self):
        distributeur = Distributeur.objects.create(
            nom="Sous", prenom="Test", code="SOUS-APERCU",
            categorie=Distributeur.CATEGORIE_DISTRIBUTEUR,
            point_vente=self.gerant.point_vente,
        )
        distribution = Distribution.objects.create(
            numero="DIS-APERCU-1",
            type_distribution=Distribution.TYPE_DISTRIBUTEUR,
            point_vente_source=self.gerant.point_vente,
            point_vente_destination=self.gerant.point_vente,
            utilisateur=self.gerant_user,
            distributeur=distributeur,
            date_distribution=timezone.localdate(),
            montant_brut=Decimal("1000"),
            montant_net=Decimal("1000"),
        )
        LigneDistribution.objects.create(
            distribution=distribution, produit=self.produit,
            prix_unitaire=Decimal("500"), montant=Decimal("1000"),
            quantite=Decimal("2"), montant_net=Decimal("1000"),
        )
        return distributeur, distribution

    def test_distribution_ouverte_visible_et_cloturee_bloquee(self):
        _, distribution = self.creer_distribution_terrain()
        url = reverse("distributions:corriger_distribution_apercu", args=[distribution.pk])
        self.client.force_login(self.directeur)
        self.assertContains(self.client.get(self.apercu, {"gerant": self.gerant.pk}), url)
        self.assertEqual(self.client.get(url).status_code, 200)
        distribution.etat = Distribution.ETAT_CLOTUREE
        distribution.save(update_fields=["etat"])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertNotContains(self.client.get(self.apercu, {"gerant": self.gerant.pk}), url)
        self.client.force_login(self.gerant_user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_distribution_corrige_stock_et_historise(self):
        distributeur, distribution = self.creer_distribution_terrain()
        stock = Stock.objects.create(
            point_vente=self.gerant.point_vente, produit=self.produit,
            quantite=Decimal("8"),
        )
        url = reverse("distributions:corriger_distribution_apercu", args=[distribution.pk])
        self.client.force_login(self.directeur)
        donnees = {
            "date_distribution": timezone.localdate().isoformat(),
            "distributeur": distributeur.pk,
            f"produit_{self.produit.pk}": "1",
            f"montant_{self.produit.pk}": "1500",
            f"taux_{self.produit.pk}": "0",
        }
        self.assertEqual(self.client.post(url, donnees).status_code, 200)
        self.assertEqual(CorrectionApercu.objects.count(), 0)
        donnees["motif_correction"] = "Quantité rectifiée"
        self.assertEqual(self.client.post(url, donnees).status_code, 302)
        distribution.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(distribution.montant_brut, Decimal("1500"))
        self.assertEqual(stock.quantite, Decimal("7"))
        self.assertEqual(CorrectionApercu.objects.count(), 1)
        self.assertEqual(NotificationCorrection.objects.count(), 1)

    def test_vente_directe_corrige_situation_automatique(self):
        client = Distributeur.objects.create(
            nom="Client", prenom="Direct", code="CLIENT-APERCU",
            categorie=Distributeur.CATEGORIE_CLIENT,
            point_vente=self.gerant.point_vente,
        )
        distribution = Distribution.objects.create(
            numero="DIS-CLIENT-APERCU", type_distribution=Distribution.TYPE_CLIENT_DIRECT,
            point_vente_source=self.gerant.point_vente,
            point_vente_destination=self.gerant.point_vente,
            utilisateur=self.gerant_user, distributeur=client,
            date_distribution=timezone.localdate(), montant_brut=Decimal("1000"),
            montant_net=Decimal("1000"),
        )
        LigneDistribution.objects.create(
            distribution=distribution, produit=self.produit,
            prix_unitaire=Decimal("500"), montant=Decimal("1000"),
            quantite=Decimal("2"), montant_net=Decimal("1000"),
        )
        stock = Stock.objects.create(
            point_vente=self.gerant.point_vente, produit=self.produit,
            quantite=Decimal("8"),
        )
        synchroniser_situation_vente_directe(distribution, self.gerant_user)
        url = reverse("distributions:corriger_distribution_apercu", args=[distribution.pk])
        self.client.force_login(self.directeur)
        self.assertContains(self.client.get(self.apercu, {"gerant": self.gerant.pk}), url)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {
            "date_reglement": timezone.localdate().isoformat(), "montant": "150",
        }).status_code, 200)
        self.assertEqual(CorrectionApercu.objects.count(), 0)
        reponse = self.client.post(url, {
            "date_distribution": timezone.localdate().isoformat(),
            f"produit_{self.produit.pk}": "1",
            f"montant_{self.produit.pk}": "1500",
            f"taux_{self.produit.pk}": "0",
            "motif_correction": "Vente rectifiée",
        })
        self.assertEqual(reponse.status_code, 302)
        stock.refresh_from_db()
        distribution.refresh_from_db()
        situation = SituationJournaliere.objects.get(distributeur=client, actif=True)
        self.assertEqual(stock.quantite, Decimal("7"))
        self.assertEqual(distribution.montant_brut, Decimal("1500"))
        self.assertEqual(situation.montant_total_verse, Decimal("1500"))
        self.assertEqual(CorrectionApercu.objects.count(), 1)

    def test_reglement_recalcule_reste_et_notifie(self):
        distributeur, _ = self.creer_distribution_terrain()
        situation = SituationJournaliere.objects.create(
            numero="SIT-APERCU-1", date_situation=timezone.localdate(),
            distributeur=distributeur, point_vente=self.gerant.point_vente,
            utilisateur=self.gerant_user, etat=SituationJournaliere.ETAT_CLOTUREE,
        )
        manquant = Manquant.objects.create(
            numero="MAN-APERCU-1", situation=situation, distributeur=distributeur,
            utilisateur=self.gerant_user, montant=Decimal("200"),
            reste_a_payer=Decimal("100"),
        )
        reglement = ReglementManquant.objects.create(
            numero="REG-APERCU-1", manquant=manquant,
            date_reglement=timezone.localdate(), montant=Decimal("100"),
            utilisateur=self.gerant_user,
        )
        url = reverse("situations:corriger_reglement_apercu", args=[reglement.pk])
        self.client.force_login(self.directeur)
        self.assertContains(self.client.get(self.apercu, {"gerant": self.gerant.pk}), url)
        self.assertEqual(self.client.get(url).status_code, 200)
        reponse = self.client.post(url, {
            "date_reglement": timezone.localdate().isoformat(),
            "montant": "150", "motif_correction": "Règlement corrigé",
        })
        self.assertEqual(reponse.status_code, 302)
        manquant.refresh_from_db()
        self.assertEqual(manquant.reste_a_payer, Decimal("50"))
        self.assertEqual(CorrectionApercu.objects.count(), 1)
        self.assertEqual(NotificationCorrection.objects.count(), 1)
        self.client.force_login(self.gerant_user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_versement_cloture_corrige_et_notifie(self):
        distributeur, _ = self.creer_distribution_terrain()
        situation = creer_situation_journaliere(
            distributeur, timezone.localdate(), self.gerant_user
        )
        ligne = situation.lignes.get()
        cloturer_situation(
            situation, {str(ligne.pk): {"montant_restant": "0"}},
            "1000", {}, self.gerant_user,
        )
        url = reverse("situations:corriger_situation_apercu", args=[situation.pk])
        self.client.force_login(self.directeur)
        self.assertContains(self.client.get(self.apercu, {"gerant": self.gerant.pk}), url)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {
            f"montant_restant_{self.produit.pk}": "500",
            "montant_total_verse": "500",
        }).status_code, 200)
        self.assertEqual(CorrectionApercu.objects.count(), 0)
        reponse = self.client.post(url, {
            f"montant_restant_{self.produit.pk}": "500",
            "montant_total_verse": "500",
            "motif_correction": "Retour rectifié",
        })
        self.assertEqual(reponse.status_code, 302)
        ligne.refresh_from_db()
        self.assertEqual(ligne.brut_restant_effectif, Decimal("500"))
        self.assertEqual(CorrectionApercu.objects.count(), 1)
        self.assertEqual(NotificationCorrection.objects.count(), 1)
        self.client.force_login(self.gerant_user)
        self.assertEqual(self.client.get(url).status_code, 403)
