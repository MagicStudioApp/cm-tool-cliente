# CM Tool - Version cliente

Outil de gestion de contenus avec tableau de bord, planning, analyse,
creation et fiches entreprises.

## Developpement local

Python 3.9 ou plus recent, sans dependance externe :

```sh
python3 server.py
```

Application : http://localhost:8127/

Editeur de tendances : http://localhost:8127/editeur/tendances

Les tendances sont conservees dans `../cm-tool-trends.sqlite3`, hors du
repertoire servi. Les autres donnees sont actuellement dans le navigateur.

## Etat du deploiement

Cette version fonctionne localement. GitHub Pages ne peut pas executer
`server.py` : les routes `/api/news` et `/api/trends` necessitent un serveur.

Avant livraison publique : authentification, autorisation administratrice
sur toutes les routes editeur, isolation des donnees par cliente, stockage
persistant heberge et sauvegardes. L'adresse cachee de l'editeur ne constitue
pas une protection. Le serveur actuel ecoute uniquement sur la boucle locale.

La generation d'idees utilise Make. Ne pas publier d'identifiants ou de
webhook actif dans un depot public. Les appels payants devront passer par
un serveur authentifie pour la version hebergee.
La connexion Make est configuree uniquement cote serveur : variable
`CM_IDEAS_WEBHOOK_URL`, ou fichier local `../cm-tool-client.private.json`
contenant un objet avec la propriete `ideasWebhookUrl`. Ce fichier doit rester
hors du depot et hors du repertoire servi. Ne jamais y copier une cle API.
Le navigateur appelle `/api/ideas`, sans connaitre l'adresse Make.
Cette route est reservee au serveur local : une authentification et des quotas
restent indispensables avant hebergement public (le controle Origin ne suffit pas).

## Import de captures dans Analyse (local)

Le bouton « Lire des captures » extrait le texte des images sur le serveur avec
RapidOCR, puis tente de classer les valeurs avec le webhook Make existant.
Si Make est indisponible, un repérage local conservateur propose uniquement
les chiffres explicitement libellés pour un seul réseau social. Aucun chiffre
n'est appliqué avant la validation manuelle dans l'interface.

Installation du lecteur local (Python 3.9+) :

```sh
python3 -m venv work/ocr-env
work/ocr-env/bin/pip install -r requirements-ocr.txt
python3 server.py
```

Les captures sont traitées temporairement en mémoire. Le texte reconnu est envoyé
au webhook Make configuré côté serveur. Les valeurs et leurs citations sont
conservées dans le rapport local uniquement après validation. La lecture OCR peut
se tromper : vérifier le compte, la période et les chiffres sur les originaux.
Branchement Make vérifié le 9 septembre 2026 sur une capture de démonstration :
12 450 abonnés et 82 300 vues correctement proposés, sans inventer de valeur
pour Facebook. Le prompt demande explicitement du JSON, requis par le module
OpenAI de Make. Les tests automatiques couvrent aussi les valeurs absentes,
ambiguës, contradictoires et les citations non conformes.

## Ateliers de création

`assets/studio/studio.js` et `studio.css` proposent cinq carrousels (comparaison,
symptômes illustrés, vrai ou faux, rappel/planning, informatif), une couverture
Reel et des notes vidéo 9:16. Chaque page est un ensemble d'éléments éditables,
avec des couleurs liées à l'entreprise. Les personnages et deux illustrations
proviennent du PDF fourni par la cliente, sans régénération.

Les créations et la bibliothèque importée sont sauvegardées par entreprise dans
IndexedDB `cm-creation-studio`, sur cet appareil. L'export utilise le même rendu
Canvas que l'aperçu : PNG 1080 px, ZIP de PNG numérotés ou vidéo MediaRecorder
(MP4 si pris en charge, sinon WebM). Garder l'onglet ouvert pendant l'export vidéo.
Les captures Instagram servent de références visuelles ; les textes de départ
sont des espaces à compléter, pas du contenu médical généré.
