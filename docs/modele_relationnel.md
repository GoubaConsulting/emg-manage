# EMG Manage - proposition de modele relationnel

## Statut de l'analyse

- Le projet Django est encore le squelette genere par Django 6.0.6.
- Aucune application metier ni migration propre au projet n'existe encore.
- `settings.py` utilise SQLite et aucun pilote PostgreSQL n'est installe dans l'environnement virtuel.
- Le service PostgreSQL 18 local fonctionne sur le port 5432.
- Le contenu de la base `bd_emg` n'a pas encore pu etre audite, car la connexion locale exige un mot de passe.
- Le fichier SQL initial ne contient aucun `INSERT`, seulement la creation de la base, des tables et des index.
- Aucune suppression, recreation ou modification de base n'a ete effectuee.

## Principes retenus

1. Les modeles et migrations Django deviennent la reference du schema.
2. Les utilisateurs heritent de `AbstractUser`; aucun mot de passe brut n'est gere par le projet.
3. Les commandes fournisseur, les commandes internes, les livraisons et les distributions sont des flux distincts.
4. Le reglement du stock tampon est un transfert de stock, pas une commande.
5. Le stock courant est conserve par point de vente, produit et type; tout changement produit un mouvement immutable.
6. Les montants et les tarifs appliques sont figes sur les lignes transactionnelles afin que l'historique ne change pas lorsque le catalogue evolue.
7. Les documents valides ne sont pas supprimes: une correction passe par une annulation ou une contre-operation tracee.

## Referentiel et acces

### PointVente

- `designation` unique
- `adresse`
- `type`: `CENTRAL` ou `POINT_VENTE`
- `actif`

Contrainte: un seul point de vente de type `CENTRAL`.

### Utilisateur (`AbstractUser`)

- champs Django standards (`username`, `password`, `first_name`, `last_name`, permissions, etc.)
- `telephone`
- `role`: `ADMINISTRATEUR`, `DIRECTEUR`, `GERANT`
- `point_vente`, nullable uniquement pour un administrateur

Regles metier:

- un directeur est rattache au point `CENTRAL`;
- un gerant est rattache a un point non central;
- un administrateur peut ne pas avoir de point de vente;
- `is_active` remplace l'ancien champ `actif` de la table utilisateur.

### Revendeur

- `nom`, `prenom`, `telephone`, `actif`
- `point_vente` obligatoire
- aucun compte utilisateur

Le terme `Revendeur` remplace `distributeur`, qui prete a confusion avec l'acte de distribution.

### Compagnie, GroupeProduit et Produit

- `Compagnie`: `designation` unique, `actif`
- `GroupeProduit`: `compagnie`, `designation`, `actif`; unicite par compagnie et designation
- `Produit`: `groupe`, `designation`, `valeur_nominale`, `actif`; unicite par groupe et designation

Un produit appartient a un seul groupe. Sa compagnie est donc determinee par son groupe. Cette structure permet plusieurs objectifs pour une meme compagnie et une meme periode, un objectif par groupe de produits.

## Achats aux compagnies

### CommandeCompagnie

- `compagnie`, `date_commande`, `reference`
- `type`: `NORMALE`, `RENOUVELLEMENT_TAMPON`, `CAUTION_BANCAIRE`
- `statut`: `BROUILLON`, `VALIDEE`, `ANNULEE`
- auteur et dates de creation/validation

### LigneCommandeCompagnie

- `commande`, `produit`, `quantite`
- instantanes financiers: valeur unitaire, taux, montant brut, reduction, montant net
- un seul exemplaire d'un produit par commande

Regles:

- le produit doit appartenir a la compagnie commandee;
- quantite et montants doivent etre positifs ou nuls selon leur sens;
- la validation d'une commande normale ou sous caution entre au stock `NORMAL` du point central;
- la validation d'un renouvellement entre au stock `TAMPON` du point central;
- une commande validee ne peut plus etre modifiee directement.

## Commandes internes et livraisons

### CommandePointVente

- `point_vente`, `date_commande`, `statut`
- auteur et dates de creation/traitement

### LigneCommandePointVente

- `commande`, `produit`
- `quantite_demandee`
- `quantite_acceptee`, renseignee lors du traitement
- un seul exemplaire d'un produit par commande

### LivraisonPointVente

- `commande` optionnelle
- point source `CENTRAL`, point destinataire, date, statut
- auteur et validateur

### LigneLivraisonPointVente

- `livraison`, `produit`, `quantite`
- un seul exemplaire d'un produit par livraison

La validation cree un transfert atomique du stock `NORMAL` central vers le stock `NORMAL` du point destinataire. Une commande interne peut etre livree en plusieurs fois.

## Stocks et tracabilite

### Stock

- `point_vente`, `produit`, `type`: `NORMAL` ou `TAMPON`
- `quantite`
- unicite `(point_vente, produit, type)`
- quantite toujours positive ou nulle

Le stock `TAMPON` est reserve au point central.

### OperationStock et MouvementStock

`OperationStock` regroupe les ecritures d'une meme operation metier:

- `type_operation`: reception fournisseur, transfert tampon, livraison, distribution, ajustement ou annulation
- date, auteur, identifiant de correlation et reference metier

Chaque `MouvementStock` contient:

- operation, point de vente, produit et type de stock
- quantite avant, variation signee, quantite apres
- contrainte `quantite_apres = quantite_avant + variation`

Exemples:

- reglement tampon: une sortie `TAMPON` et une entree `NORMAL` au central;
- livraison: une sortie `NORMAL` au central et une entree `NORMAL` au point de vente;
- distribution: une sortie `NORMAL` du point de vente pour la quantite nouvellement remise au revendeur.

Les mises a jour de stock utilisent une transaction atomique et un verrou de ligne afin d'interdire les stocks negatifs en cas d'operations simultanees.

## Distribution aux revendeurs

### DistributionRevendeur

- `revendeur`, `point_vente`, `date_distribution`, `statut`
- auteur et date de validation
- unicite recommandee `(revendeur, date_distribution)`

### LigneDistributionRevendeur

- `distribution`, `produit`
- `quantite_initiale`: restant confirme de la situation precedente
- `quantite_ajoutee`: nouvelle quantite sortie du stock du point de vente
- `quantite_totale`: calculee
- instantanes financiers: valeur unitaire, taux, reduction et montant attendu
- un seul exemplaire d'un produit par distribution

Seule `quantite_ajoutee` diminue le stock du point de vente. Le restant de la veille est deja chez le revendeur.

## Situations journalieres

Deux documents sont conserves afin de ne pas melanger les responsabilites:

### SituationRevendeur

- une situation pour une distribution revendeur
- lignes par produit avec quantite restante et valeur du restant
- total distribue, total verse, total restant, manquant et surplus

### SituationPointVente

- `point_vente`, `date_situation`
- lignes par produit avec stock initial, entrees du jour, sorties du jour et stock final
- total a justifier, total verse, valeur du stock final, manquant et surplus
- unicite `(point_vente, date_situation)`

Les totaux calculables ne doivent pas etre saisis librement. Ils sont calcules lors de la validation puis figes pour l'audit.

## Encaissements, manquants et surplus

### VersementRevendeur et VersementPointVente

Chaque versement conserve la date, le montant, le payeur, le beneficiaire/collecteur, la situation concernee et une reference eventuelle. Plusieurs versements peuvent etre rattaches a une situation.

### Manquant et ReglementManquant

- un `Manquant` est lie a une seule situation et conserve montant initial, solde et statut;
- `ReglementManquant` conserve chaque paiement, sa date, son montant et l'utilisateur qui l'enregistre;
- le solde et le statut sont recalcules dans une transaction;
- un reglement ne peut pas depasser le solde.

Le surplus reste une valeur positive figee dans la situation. Une future utilisation ou restitution du surplus devra etre modelisee par une operation distincte, et non en modifiant la situation historique.

## Tresorerie fournisseur

### Banque et VersementBancaire

- `Banque`: designation unique
- `VersementBancaire`: compagnie, banque, date, reference, motif, montant
- unicite recommandee `(banque, reference)`

### AffectationVersement

- relie un versement bancaire a une commande compagnie;
- porte le montant affecte;
- permet qu'un versement regle plusieurs commandes et qu'une commande soit reglee progressivement.

Les affectations ne peuvent depasser ni le versement disponible ni le solde de la commande.

## Objectifs commerciaux

### ObjectifCommercial

- `groupe_produit`
- `date_debut`, `date_fin`
- `montant_cible`
- unicite `(groupe_produit, date_debut, date_fin)`

Le montant realise et le taux de realisation sont calcules a partir des commandes compagnie validees des produits du groupe pendant la periode. Ils ne sont pas stockes comme sources independantes, afin d'eviter les incoherences.

## Contraintes transversales

- toutes les quantites sont entieres et non negatives, sauf la variation signee d'un mouvement;
- tous les montants utilisent `DecimalField`, jamais `float`;
- toutes les lignes ont une contrainte d'unicite sur `(document, produit)`;
- les dates de fin sont superieures ou egales aux dates de debut;
- les suppressions de referentiels deja utilises sont protegees; on les desactive avec `actif`;
- les validations metier critiques passent par des services transactionnels, pas par de simples appels `save()` disperses;
- les gerants sont filtres par leur point de vente dans les vues et les services, pas seulement dans l'interface.

## Points a valider avant les modeles Django

1. Le `taux` represente-t-il une remise/commission en pourcentage, et quelle est exactement la formule du montant net pour une commande et une distribution?
2. Les produits sont-ils toujours geres en quantites entieres, y compris les credits electroniques et Mobile Money?
3. Un produit peut-il appartenir a plusieurs groupes d'objectifs, ou un groupe unique par produit suffit-il?
4. Le stock tampon est-il strictement central et interdit aux points de vente?
5. Pour la situation du gerant, le montant a justifier est-il bien la valeur du stock initial plus les livraisons du jour, avec comme contreparties le versement et le stock final?
6. Un surplus doit-il seulement etre historise, ou peut-il etre reporte/compense sur une journee ulterieure?
7. Les versements bancaires doivent-ils etre affectes a des commandes precises, notamment pour les cautions, ou seul le solde global par compagnie est-il suivi?

## Ordre de mise en oeuvre apres validation

1. Auditer `bd_emg` en lecture seule et sauvegarder toute donnee utile.
2. Creer les applications Django et le modele utilisateur personnalise avant la premiere migration.
3. Configurer PostgreSQL par variables d'environnement et installer le pilote.
4. Generer puis relire les migrations initiales.
5. Migrer sur une base vide ou sur `bd_emg` uniquement apres accord explicite.
6. Ajouter les services transactionnels et leurs tests avant les ecrans metier.
