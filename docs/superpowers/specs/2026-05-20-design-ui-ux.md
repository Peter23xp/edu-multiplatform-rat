# Design UI/UX — EduRAT Console

**Date:** 2026-05-20
**Statut:** Approuvé

---

## 1. Vue d'ensemble

Refonte de l'interface graphique `server_gui.py` pour la rendre plus friendly, moderne et lisible. Les 14 onglets actuels sont remplacés par une **sidebar avec groupes nommés**. Un système de **messages d'erreur contextuels** remplace les messages génériques actuels. Le dark theme Nord est conservé mais modernisé avec de meilleurs contrastes et une hiérarchie visuelle claire.

---

## 2. Architecture de navigation

### Remplacement des 14 onglets par une sidebar

La sidebar gauche contient 5 groupes. Chaque groupe est un label discret (petites majuscules) suivi de ses items. Un item actif est mis en évidence par un fond légèrement plus clair et une bordure gauche colorée.

**Groupe Contrôle**
- Dashboard (vue par défaut au démarrage)
- Terminal (envoi de commandes)
- Clients (liste détaillée avec info système)

**Groupe Surveillance**
- Écran / Stream (screenshots + live stream fusionnés)
- Webcam
- Keylogger
- Presse-papier

**Groupe Fichiers**
- Explorateur (navigation + suppression)
- Transfert (upload / download)

**Groupe Réseau & Système**
- Scanner réseau
- Persistance
- Info système

**Groupe Config (bas de sidebar, séparé par une ligne)**
- Paramètres (hôte, port, timeout, credentials)
- Génération client
- Défense / Détection
- Rapports
- Aide

### Dimensions sidebar
- Largeur fixe : 160px
- Fond : `#141824`
- Bordure droite : `1px solid #1e2433`

---

## 3. Palette de couleurs modernisée

| Élément | Couleur actuelle | Nouvelle couleur |
|---|---|---|
| Fond principal | `#2E3440` | `#0f1117` |
| Fond sidebar | `#2E3440` | `#141824` |
| Fond cards / panels | `#3B4252` | `#1a1e2e` |
| Fond console | `#3B4252` | `#080b10` |
| Bordures | `#3B4252` | `#1e2433` |
| Texte principal | `#ECEFF4` | `#eceff4` (inchangé) |
| Texte inactif | `#D8DEE9` | `#4c566a` |
| Accent cyan | `#88C0D0` | `#88c0d0` (inchangé) |
| Accent vert | `#A3BE8C` | `#a3be8c` (inchangé) |
| Accent rouge | `#BF616A` | `#bf616a` (inchangé) |
| Accent jaune | `#EBCB8B` | `#ebcb8b` (inchangé) |
| Accent bleu | `#5E81AC` | `#5e81ac` (inchangé) |

### 3 niveaux de profondeur
1. **Fond** : `#0f1117` — arrière-plan général
2. **Sidebar + panels** : `#141824` — éléments de premier plan
3. **Cards / inputs** : `#1a1e2e` — contenu imbriqué

---

## 4. Dashboard (vue principale)

Affiché par défaut au lancement. Contient :

- **Barre de statut globale** (haut de fenêtre) : nom de l'app, indicateur serveur ON/OFF avec dot pulsant vert, nombre de clients, badge port, compteur d'alertes
- **Rangée de métriques** : 3 cards — Clients connectés, Statut serveur, Alertes actives
- **Zone de notifications** : liste des messages d'erreur/succès/info récents (voir section 5)
- **Liste des clients** : chaque client sur une ligne avec IP, OS, statut, bouton "Sélectionner"
- **Console** : log scrollable en bas, fond `#080b10`, monospace 9px

---

## 5. Système de messages d'erreur contextuels

Chaque message remplace les anciens `[!] Screenshot failed` par un bloc structuré en 3 lignes.

### Structure d'un message

```
[icône] NIVEAU — Titre court          [BADGE CATÉGORIE]    horodatage
Client: IP · Opération: nom · Cause: description exacte
→ Suggestion d'action concrète (commande ou chemin si applicable)
```

### 4 niveaux de sévérité

| Niveau | Icône | Couleur bordure | Fond |
|---|---|---|---|
| ERREUR | ✕ | `#bf616a` | `#bf616a0d` |
| AVERTISSEMENT | ⚠ | `#ebcb8b` | `#ebcb8b0d` |
| TIMEOUT | ⏱ | `#d08770` | `#d087700d` |
| SUCCÈS | ✓ | `#a3be8c` | `#a3be8c0d` |
| INFO | ℹ | `#5e81ac` | `#5e81ac0d` |

### Badges de catégorie
`RÉSEAU` · `FICHIER` · `DÉPENDANCE` · `SURVEILLANCE` · `AUTHENTIFICATION` · `SYSTÈME`

### Cas d'erreur à couvrir (avec suggestions)

| Erreur | Cause affichée | Suggestion |
|---|---|---|
| Screenshot échoué | pyautogui non installé | `pip install pyautogui` sur le client |
| Webcam indisponible | opencv-python absent | `pip install opencv-python` sur le client |
| Keylogger indisponible | pynput non installé | `pip install pynput` sur le client |
| Connexion perdue | errno 104 / reset | Vérifier que le processus client tourne |
| Timeout commande | 15s dépassées | Augmenter timeout dans Paramètres → Réseau |
| Permission refusée | errno 13 | Vérifier droits root/admin du client |
| Fichier introuvable | errno 2 / ENOENT | Vérifier le chemin exact sur le client |
| Authentification échouée | Mauvais credentials | Vérifier user/password dans Paramètres |
| Port déjà utilisé | errno 98 / EADDRINUSE | Changer le port dans Paramètres ou libérer :4444 |
| Chiffrement indisponible | pycryptodome absent | `pip install pycryptodome` — fallback non chiffré actif |

### Affichage dans la console
Les mêmes infos apparaissent dans la console en format compact :
```
[HH:MM:SS] [✕] Screenshot 192.168.1.10 — pyautogui absent → pip install pyautogui
```

---

## 6. Animations et micro-interactions

- **Hover sidebar** : transition `background 150ms ease` vers `#1e2433`
- **Item actif** : bordure gauche `2px solid #88c0d0`, fond `#1e2636`
- **Notifications** : fade-in `opacity 200ms ease` à l'apparition
- **Indicateur serveur actif** : animation `pulse` sur le dot vert (scale 1→1.15, 2s loop)
- **Boutons** : légère élévation `box-shadow` au hover

---

## 7. Composants réutilisables à créer

| Composant | Description |
|---|---|
| `SidebarGroup` | Frame Tkinter avec label de groupe + items |
| `SidebarItem` | Label cliquable avec icône, texte, état actif/inactif |
| `NotificationBar` | Zone scrollable de notifications en haut du contenu |
| `Notification` | Widget d'une notification avec niveau, contexte, suggestion |
| `StatCard` | Card métrique (nombre + label) |
| `ConsoleWidget` | Text scrollable avec tags de couleur par niveau |

---

## 8. Ce qui ne change pas

- La logique réseau (socket, protocol, encryption) — aucune modification
- Les fonctionnalités (toutes conservées, juste réorganisées)
- Les raccourcis clavier existants
- La compatibilité Windows/Linux/macOS
- `server.py` (CLI) — hors scope

---

## 9. Hors scope

- Refonte du client (`client.py`, `client_gen.py`)
- Tests unitaires
- Mode light/dark toggle
- Internationalisation
