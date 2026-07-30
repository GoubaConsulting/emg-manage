# Schema SQL EMG Manage

## Fichier principal

`schema_emg_v2.sql` contient le schema metier PostgreSQL propose pour EMG Manage.

Il cree 31 tables dans un schema PostgreSQL separe nomme `emg`. Les anciennes tables du schema `public` ne sont ni modifiees ni supprimees. Cette separation est volontaire tant que le contenu reel de `bd_emg` n'a pas ete audite et sauvegarde.

## Ce que le nouveau schema corrige

- `utilisateur.idpointvente` est nullable pour l'administrateur et obligatoire pour le directeur et le gerant.
- Le directeur est rattache au point `CENTRAL`; le gerant a un point non central.
- `distributeur` devient `revendeur` et ne possede pas de compte utilisateur.
- Les commandes aux compagnies et les commandes des points de vente sont separees.
- Une livraison central vers point de vente est distincte d'une distribution point de vente vers revendeur.
- Le reglement du stock tampon devient un transfert `TAMPON` vers `NORMAL`.
- Le stock courant est unique par point de vente, produit et type.
- Chaque variation de stock produit une ecriture immutable avec quantites avant et apres.
- Les situations revendeur et point de vente sont separees.
- Les paiements de manquants sont historises et ne peuvent pas depasser le solde.
- Les versements bancaires peuvent etre affectes progressivement aux commandes.
- Les objectifs portent sur un groupe de produits et une periode; la realisation est calculee.

## Tables de l'ancien schema remplacees

| Ancien objet | Nouveau modele |
| --- | --- |
| `distributeur` | `emg.revendeur` |
| `commande`, `lignecommande` | `commande_compagnie` et `commande_point_vente`, avec leurs lignes |
| reglement tampon dans `commande.type` | `transfert_stock_tampon` et ses mouvements |
| `distribution` direction/terrain ambigue | `livraison_point_vente` et `distribution_revendeur` |
| `stock` sans unicite ni historique | `stock`, `operation_stock`, `mouvement_stock` |
| situation unique | `situation_revendeur` et `situation_point_vente` |
| `objectif`, `ligneobjectif` | `groupe_produit`, `objectif_commercial`, vue de realisation |
| banque en texte libre | `banque`, `versement_bancaire`, `affectation_versement` |

## Hypotheses encore a confirmer

1. `taux_remise_pct` est traite comme un pourcentage retranche du montant brut.
2. Toutes les quantites sont des entiers, y compris le credit electronique et Mobile Money.
3. Un produit appartient a un seul groupe de produits.
4. Le stock tampon existe uniquement au point central.
5. La realisation d'un objectif est la somme nette des commandes compagnie validees.
6. La situation du point de vente justifie le stock initial et les entrees du jour par le versement et le stock final.
7. Un revendeur ne possede qu'une distribution par jour, qui regroupe tous ses produits.

Ces hypotheses doivent etre confirmees avant la creation des modeles Django.

## Relation avec Django

Le script est une reference SQL et un outil de revue. Il ne doit pas etre execute puis double par des migrations Django initiales, car Django tenterait de recreer les memes tables.

La procedure recommandee est :

1. valider ce schema et les hypotheses metier;
2. auditer et sauvegarder l'ancienne base;
3. traduire le schema en modeles Django, dont `Utilisateur(AbstractUser)`;
4. laisser Django produire et appliquer les migrations sur un schema vide;
5. ecrire ensuite une migration de donnees distincte pour les anciennes tables utiles;
6. supprimer les anciennes tables uniquement apres verification et accord explicite.

## Securite d'execution

Le fichier contient une commande `DROP SCHEMA` commentee. Elle ne doit etre activee que pour reinitialiser volontairement une base de developpement sans donnee utile.

Le script n'a pas ete applique a `bd_emg`. Son execution sur un PostgreSQL temporaire isole a ete tentee, mais Windows a refuse le demarrage du cluster temporaire dans le bac a sable. Une validation dynamique finale reste donc a faire avec un acces PostgreSQL autorise.
