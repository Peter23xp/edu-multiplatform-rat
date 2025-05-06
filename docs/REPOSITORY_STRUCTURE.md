# Structure du Dépôt

Ce document décrit l'organisation des fichiers dans le dépôt du projet éducatif RAT multiplateforme.

## Vue d'ensemble

```
edu-multiplatform-rat/
├── .github/                     # Configuration GitHub
│   └── ISSUE_TEMPLATE/          # Modèles pour les issues
│       ├── bug_report.md        # Modèle pour rapport de bug
│       └── feature_request.md   # Modèle pour demande de fonctionnalité
├── build/                       # Fichiers temporaires de build (ignorés par Git)
├── builds/                      # Builds finalisés
│   └── clients/                 # Clients générés
├── dist/                        # Fichiers de distribution
├── docs/                        # Documentation
│   ├── FIRST_ISSUE.md           # Exemple d'issue pour démarrer
│   ├── GITHUB_SETUP.md          # Instructions pour la configuration GitHub
│   └── REPOSITORY_STRUCTURE.md  # Ce document
├── screenshots/                 # Captures d'écran pour documentation
├── .gitignore                   # Configuration des fichiers à ignorer
├── client.py                    # Client RAT principal
├── client_template.py           # Modèle pour la génération de clients
├── CODE_OF_CONDUCT.md           # Code de conduite pour les contributeurs
├── CONTRIBUTING.md              # Guide de contribution
├── LICENSE                      # Licence MIT
├── README.md                    # Documentation principale
├── requirements.txt             # Dépendances Python
├── SECURITY.md                  # Politique de sécurité
├── server.py                    # Serveur RAT en ligne de commande
├── server_gui.py                # Interface graphique du serveur
├── setup.bat                    # Script d'installation pour Windows
└── test_connection.py           # Outil de diagnostic de connexion
```

## Description des composants principaux

### Fichiers source

- **server.py** - Serveur RAT en ligne de commande avec interface texte colorée
- **server_gui.py** - Serveur RAT avec interface graphique Tkinter
- **client.py** - Client RAT avec fonctionnalités complètes
- **client_template.py** - Modèle pour générer des clients personnalisés
- **test_connection.py** - Outil de diagnostic pour les problèmes de connexion

### Documentation

- **README.md** - Documentation principale et guide d'utilisation
- **CONTRIBUTING.md** - Guide pour contribuer au projet
- **CODE_OF_CONDUCT.md** - Règles pour la communauté et considérations éthiques
- **LICENSE** - Licence MIT pour le projet
- **SECURITY.md** - Politique de divulgation de sécurité et conseils

### Configuration

- **.gitignore** - Liste des fichiers à ne pas suivre dans Git
- **requirements.txt** - Dépendances Python nécessaires
- **setup.bat** - Script d'installation pour Windows

### Configuration GitHub

- **.github/ISSUE_TEMPLATE/** - Modèles pour les rapports de bug et demandes de fonctionnalités

## Organisation des dossiers

- **builds/clients/** - Stocke les clients générés et compilés
- **dist/** - Fichiers de distribution générés par PyInstaller
- **docs/** - Documentation supplémentaire
- **screenshots/** - Captures d'écran pour la documentation

## Flux de travail du projet

1. **Installation**: Via setup.bat ou requirements.txt
2. **Lancement du serveur**: Exécution de server.py ou server_gui.py
3. **Génération du client**: Personnalisation via l'interface ou édition de client_template.py
4. **Déploiement**: Distribution du client aux systèmes cibles pour tests éducatifs
5. **Communication**: Échange de commandes et de données entre serveur et client 