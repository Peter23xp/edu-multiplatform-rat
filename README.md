# Educational Remote Access Trojan (RAT)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.6%2B-brightgreen.svg)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)
![Educational Only](https://img.shields.io/badge/purpose-educational%20only-red.svg)

## ⚠️ UTILISATION LÉGALE UNIQUEMENT

**Ce projet est EXCLUSIVEMENT destiné à l'éducation en cybersécurité.**

- Utilisez ce logiciel UNIQUEMENT dans des environnements contrôlés, machines virtuelles, ou systèmes que vous possédez
- L'utilisation sans autorisation explicite est ILLÉGALE dans la plupart des juridictions
- L'accès non autorisé à des systèmes informatiques est un crime grave
- Les auteurs n'acceptent AUCUNE responsabilité pour toute utilisation abusive
- En utilisant ce logiciel, vous assumez l'ENTIÈRE responsabilité de vos actions

## ⚡ Quick Start (Démarrage Rapide)

1. **Installation** : Exécutez `setup.bat` et choisissez l'option 1 pour installer les dépendances
2. **Lancement du serveur** : Exécutez `setup.bat` et choisissez l'option 2 (ou `python server_gui.py`)
3. **Génération du client** : Dans l'interface du serveur, allez dans l'onglet "Settings", puis cliquez sur "Generate Client Now"
4. **Test rapide** : 
   - Sur la même machine : Exécutez `python client_gen.py`
   - Vérifiez la connexion dans l'interface du serveur
   - Sélectionnez le client et envoyez la commande `whoami` ou cliquez sur "Capture Screenshot"

**Adresse et port par défaut** : 127.0.0.1:4444 (pour un test local)

## 📋 Introduction

Ce projet implémente un RAT (Remote Access Trojan) éducatif avec interface graphique pour aider les étudiants en cybersécurité à comprendre comment ces outils fonctionnent et comment s'en défendre. Le code est délibérément maintenu simple et non-obfusqué pour une transparence pédagogique.

## 🔧 Prérequis

- Python 3.6+
- Bibliothèques requises (installées via `requirements.txt`) :
  - Socket (bibliothèque standard)
  - Subprocess (bibliothèque standard)
  - Tkinter (bibliothèque standard)
  - Pillow (traitement d'images)
  - PyAutoGUI (captures d'écran)
  - OpenCV-Python (accès webcam)
  - Pynput (keylogging)
  - PyInstaller (création d'exécutables)

## 💿 Installation

### Méthode 1 : Utilisation du script d'installation automatique

1. Exécutez le script `setup.bat` (Windows) et sélectionnez l'option 1 :
   ```
   setup.bat
   ```

2. Le script installera toutes les dépendances et créera les dossiers nécessaires.

### Méthode 2 : Installation manuelle

1. Clonez ou téléchargez ce dépôt sur votre machine locale
2. Installez toutes les dépendances requises :
   ```
   pip install -r requirements.txt
   ```
3. Créez les dossiers nécessaires :
   ```
   mkdir -p dist builds/clients
   ```

## 🖥️ Lancement du Serveur

### Méthode 1 : Via l'outil de configuration

1. Exécutez `setup.bat` et sélectionnez l'option 2 :
   ```
   setup.bat
   ```

### Méthode 2 : Lancement direct

1. Lancez le serveur GUI directement :
   ```
   python server_gui.py
   ```

2. La fenêtre du serveur s'ouvrira avec plusieurs onglets :
   - **Control Panel** : Gestion des connexions et envoi de commandes
   - **File Operations** : Transfert de fichiers
   - **Screenshots** : Visualisation des captures d'écran
   - **System Info** : Informations système des clients
   - **Webcam** : Captures de la webcam
   - **Keylogger** : Suivi des frappes clavier
   - **Settings** : Configuration du serveur et génération de clients
   - **Help** : Aide à l'utilisation

3. Dans l'onglet **Settings** :
   - Configurez l'adresse d'écoute (0.0.0.0 pour toutes les interfaces)
   - Définissez le port (4444 par défaut)
   - Configurez les paramètres d'authentification (nom d'utilisateur/mot de passe)
   - Choisissez si vous souhaitez utiliser l'IP LAN (pour connexions entre machines) ou localhost

4. Retournez à l'onglet **Control Panel** et cliquez sur "Start Server"

## 🔄 Génération du Client

### Option 1 : Via l'interface graphique

1. Dans le serveur GUI, allez dans l'onglet "Settings"
2. Assurez-vous que le serveur est démarré
3. Configurez les options du client :
   - Utilisez l'IP LAN pour des connexions entre machines
   - Configurez les identifiants d'authentification
   - Choisissez si vous souhaitez générer un exécutable (.exe)
4. Cliquez sur "Generate Client Now"
   - Un fichier `client_gen.py` sera créé
   - Si l'option de construction d'exécutable est activée, un fichier `.exe` sera également créé

### Option 2 : Création manuelle du client

1. Copiez `client_template.py` vers un nouveau fichier
2. Éditez les variables suivantes :
   - `SERVER_HOST` : IP du serveur (ex: "192.168.1.10")
   - `SERVER_PORT` : Port du serveur (ex: 4444)
   - `AUTH_USERNAME` et `AUTH_PASSWORD` : Identifiants d'authentification

## 📤 Transfert et Exécution du Client

### Transfert du client vers une autre machine

1. **Par clé USB** : Copiez le fichier `client_gen.py` ou l'exécutable généré
2. **Par partage réseau** : Placez le fichier sur un partage réseau accessible
3. **Par e-mail** (à des fins de test uniquement) : Envoyez le fichier en pièce jointe

⚠️ **IMPORTANT** : Pour une connexion entre machines différentes, assurez-vous que :
- L'adresse IP du serveur est correcte (utilisez l'IP LAN, pas localhost)
- Le port est ouvert dans le pare-feu
- Les deux machines sont sur le même réseau

### Exécution du client

#### Si vous utilisez le script Python :
```
python client_gen.py
```

#### Si vous utilisez l'exécutable :
Double-cliquez simplement sur le fichier `.exe` généré

#### Processus de connexion :
1. Le client testera d'abord la connexion au serveur
2. Le client s'authentifiera avec le serveur
3. En cas de connexion réussie, le client apparaîtra dans la liste des clients du serveur GUI

## 👁️ Visualisation des Résultats

### Dans l'interface du serveur

1. **Sélection d'un client** :
   - Dans l'onglet "Control Panel", vous verrez la liste des clients connectés
   - Cliquez sur un client puis sur "Connect" pour le sélectionner

2. **Envoi de commandes** :
   - Entrez une commande dans le champ texte en bas de l'onglet "Control Panel"
   - Cliquez sur "Send" pour l'envoyer au client

3. **Visualisation des résultats** :
   - Les résultats des commandes s'affichent dans la console de l'onglet "Control Panel"
   - Les captures d'écran apparaissent dans l'onglet "Screenshots"
   - Les captures webcam sont visibles dans l'onglet "Webcam"
   - Les données du keylogger s'affichent dans l'onglet "Keylogger"
   - Les informations système sont dans l'onglet "System Info"

### Stockage des données

1. **Captures d'écran et images webcam** :
   - Peuvent être sauvegardées sur disque via les boutons "Save" dans leurs onglets respectifs
   - Sauvegardées dans l'emplacement que vous choisissez via la boîte de dialogue

2. **Données du keylogger** :
   - Temporairement stockées sur la machine cliente
   - Récupérées avec la commande "keylogger_dump"
   - Peuvent être sauvegardées dans un fichier via le bouton "Save To File" de l'onglet Keylogger

3. **Transferts de fichiers** :
   - Onglet "File Operations" pour télécharger/uploader des fichiers
   - Les fichiers téléchargés depuis le client sont enregistrés dans le répertoire courant du serveur
   - Les fichiers à envoyer au client doivent être sélectionnés depuis l'explorateur de fichiers local

## 🔐 Gestion Multi-clients

1. **Liste des clients** :
   - Tous les clients connectés apparaissent dans l'onglet "Control Panel"
   - Chaque client est identifié par ID, adresse IP et informations système

2. **Basculer entre les clients** :
   - Sélectionnez un client dans la liste
   - Cliquez sur "Connect" pour interagir avec lui
   - Toutes les commandes et actions suivantes seront dirigées vers ce client

3. **Suivi des connexions** :
   - L'indicateur visuel vert indique que des clients sont connectés
   - L'indicateur jaune indique que le serveur est en attente de connexions
   - L'indicateur rouge indique que le serveur est arrêté

## 🛑 Arrêt Propre

### Arrêter un client

1. **Via le serveur** :
   - Sélectionnez le client dans la liste
   - Envoyez la commande `exit`
   - Le client se déconnectera proprement et terminera son processus

2. **Manuellement** :
   - Sur la machine cliente, utilisez Ctrl+C dans la console (si visible)
   - Ou terminez le processus via le gestionnaire de tâches

### Arrêter le serveur

1. Cliquez sur le bouton "Stop Server" dans l'onglet "Control Panel"
2. Fermez l'application en cliquant sur la croix de la fenêtre
3. Confirmez que vous souhaitez quitter

## 🧪 Dépannage des Connexions

En cas de problèmes de connexion, utilisez l'outil de test de connexion :

1. Exécutez `setup.bat` et choisissez l'option 3, ou lancez directement :
   ```
   python test_connection.py
   ```

2. L'outil vous guidera pour diagnostiquer les problèmes courants :
   - IP incorrecte
   - Port fermé/bloqué
   - Problèmes de pare-feu
   - Configuration réseau incorrecte

## 📚 Commandes Disponibles

- `sysinfo` - Obtenir les informations système
- `shell [commande]` - Exécuter des commandes shell sur la cible
- `upload <fichier>` - Envoyer un fichier au client
- `download <fichier>` - Télécharger un fichier depuis le client
- `screenshot` - Capturer l'écran du client
- `webcam` - Capturer une image depuis la webcam
- `keylogger_start` - Démarrer le keylogger
- `keylogger_stop` - Arrêter le keylogger
- `keylogger_dump` - Récupérer les frappes enregistrées
- `exit` - Déconnecter le client

## ⚖️ Considérations Éthiques et Risques

Lors de l'étude d'outils de sécurité offensive :

1. Pratiquez TOUJOURS dans des environnements isolés et contrôlés
2. Concentrez-vous sur la compréhension des mécanismes pour construire de meilleures défenses
3. Considérez comment les logiciels antivirus et de sécurité pourraient détecter ces outils
4. Discutez des implications éthiques de la création de tels outils
5. Ne déployez JAMAIS sur des systèmes sans permission explicite

### Détection et Défense

Pour compléter l'aspect éducatif, voici comment détecter et se défendre contre les RATs :

- Surveillez les connexions réseau inhabituelles
- Utilisez des outils de surveillance des processus pour détecter les processus suspects
- Implémentez des règles de pare-feu appropriées
- Maintenez vos systèmes et logiciels antivirus à jour
- Méfiez-vous des fichiers exécutables inconnus
- Utilisez des listes blanches d'applications quand c'est approprié
- Surveillez les comportements système inhabituels
- Vérifiez les accès non autorisés à la webcam ou au microphone
- Utilisez des outils de chiffrement du clavier pour prévenir le keylogging
- Implémentez l'authentification multi-facteurs 

## �� Comment Contribuer

🎉 **Ce projet est ouvert à la collaboration !** Que vous soyez développeur, pentester ou étudiant, vos idées sont les bienvenues.

### Contribuez au développement

1. Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour les directives
2. Parcourez les [issues ouvertes](../../issues) ou créez-en une nouvelle
3. Proposez une Pull Request avec vos améliorations
4. Participez aux discussions pour partager vos idées

### Types de contributions recherchées

- Amélioration de la compatibilité multiplateforme
- Nouvelles fonctionnalités éducatives
- Améliorations de l'interface
- Documentation et tutoriels
- Corrections de bugs

### Respectez notre éthique

Toutes les contributions doivent respecter l'objectif pédagogique du projet et notre [Code de Conduite](CODE_OF_CONDUCT.md).

## 📜 Licence

Ce projet est distribué sous licence MIT. Voir [LICENSE](LICENSE) pour plus d'informations.

---

<div align="center">
  <strong>🛡️ Apprenez la sécurité offensive pour mieux vous défendre. Ce projet est une ressource éducative pour comprendre les menaces et améliorer votre posture de sécurité. ��️</strong>
</div> 