# MonEsti44 : mise en ligne

Le site est une page autonome. Une fois en ligne, il fonctionne tout seul :
- il cherche l'adresse avec l'API gratuite de l'IGN ;
- il lit les ventes DVF (prix net vendeur) rangées dans le dossier `data`, mises à jour chaque mois par un robot GitHub ;
- il envoie chaque demande dans une Google Sheet et vous prévient par e-mail.

Aucun abonnement, aucun coût par estimation. Seul le nom de domaine est payant (environ 10 € par an).

## 1. Réserver le nom de domaine
Chez OVH, Gandi ou IONOS, vérifier et réserver `monesti44.fr`.

## 2. Mettre le site sur GitHub (gratuit)
1. Créer un compte sur github.com, puis un dépôt public nommé `monesti44`.
2. « Add file › Upload files » : glisser tout le contenu de ce dossier, puis valider.
3. Onglet **Actions** › « Mise à jour des ventes DVF 44 » › **Run workflow**. Au bout de 5 à 10 minutes, le dossier `data` contient les ventes de Loire-Atlantique. Ensuite, le robot repasse seul le 5 de chaque mois.
4. **Settings › Pages** : Source « Deploy from a branch », branche `main`, dossier `/ (root)`.
5. Toujours dans Pages, « Custom domain » : `www.monesti44.fr`, puis cocher « Enforce HTTPS ».
6. Chez le registraire du domaine, dans la zone DNS :
   - `www` en CNAME vers `VOTRE-COMPTE.github.io`
   - le domaine nu en A vers `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`

## 3. Recevoir les demandes (Google Sheet + e-mail)
1. Créer une Google Sheet « Prospects MonEsti44 ».
2. Menu **Extensions › Apps Script**, coller le contenu de `google-apps-script/Code.gs`, enregistrer.
3. Choisir la fonction `testerReception` et cliquer sur **Exécuter** (accepter les autorisations). Une ligne de test et un e-mail arrivent.
4. **Déployer › Nouveau déploiement › Application Web** : exécuter en tant que « Moi », accès « Tout le monde ». Copier l'URL obtenue.
5. Sur GitHub, ouvrir `index.html` (crayon pour modifier) et coller l'URL entre les guillemets de `LEAD_URL: ""`.

## 4. Compléter les mentions légales
Dans `index.html`, bloc `CFG` en haut du script : numéro RSAC et numéro de carte professionnelle de l'agence. Le nom du partenaire affiché dans la case de consentement se règle aussi là (`PARTENAIRE`).

## 5. Tester
Ouvrir `https://www.monesti44.fr/?rapide=1` : l'analyse dure 10 secondes au lieu de 3 minutes. Vérifier qu'une ligne arrive dans la Google Sheet.

## Liens à mettre dans les stories et les bios
- Instagram : `https://www.monesti44.fr/?utm_source=instagram`
- TikTok : `https://www.monesti44.fr/?utm_source=tiktok`
- YouTube : `https://www.monesti44.fr/?utm_source=youtube`
- Facebook : `https://www.monesti44.fr/?utm_source=facebook`

La colonne « Source » de la Google Sheet indique alors d'où vient chaque prospect.

## Réglages utiles (bloc `CFG` de `index.html`)
- `ANALYSE_SECONDES` : durée de l'analyse (180 = 3 minutes).
- `RAYON` : 500 m.
- `AJUSTEMENT_MARCHE` : correction de la médiane des 2 dernières années (−4 % aujourd'hui, marché baissier). Non appliquée quand les ventes 2018 sont utilisées. À remettre à 0 ou en positif quand le marché repart.
- `MIN_COMPARABLES` : en dessous de ce nombre de ventes du même type à 500 m sur 24 mois, les ventes 2018 sont ajoutées, puis le rayon passe à 1 000 m et 1 500 m.

## Capacité
GitHub Pages sert le site depuis un réseau mondial : plusieurs dizaines de milliers de visites par jour passent sans problème (limite indicative de 100 Go par mois, soit plusieurs centaines de milliers d'estimations). Si le trafic explose, le même dossier peut être déplacé sur Cloudflare Pages (gratuit, sans limite de bande passante).
