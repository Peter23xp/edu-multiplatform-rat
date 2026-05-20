# Robustesse C2 — Design Spec

**Date:** 2026-05-20
**Statut:** Approuvé

---

## 1. Vue d'ensemble

Trois améliorations indépendantes pour que l'app fonctionne sans interaction humaine :

1. **SP1 — Reconnexion robuste** : le client se reconnecte seul avec backoff exponentiel + heartbeat bidirectionnel
2. **SP2 — Exfiltration automatique** : keylogger/clipboard/screenshots s'envoient seuls via spool disque
3. **SP3 — Persistance discrète** : noms aléatoires, fallback multi-méthode, vérification automatique

---

## 2. SP1 — Reconnexion & Heartbeat (client.py + server.py)

### Backoff exponentiel
- Délai initial : 1s
- Multiplie par 2 à chaque échec : 1 → 2 → 4 → 8 → … → 60s (plafond)
- Reset à 1s dès connexion réussie
- Remplace le `time.sleep(5)` fixe actuel

### Heartbeat
- Client envoie `PING` toutes les 30s (thread daemon séparé)
- Serveur répond `PONG` immédiatement et met à jour `last_seen[client_id]`
- Watchdog serveur tourne toutes les 10s : si `now - last_seen > 35s` → client marqué MORT, retiré de `self.clients`, log contextuel affiché

### Données à modifier
- `client.py` : boucle de reconnexion + thread heartbeat
- `server.py` : handler PING/PONG + watchdog thread

---

## 3. SP2 — Exfiltration automatique (client.py)

### Spool disque
- Dossier `spool/` dans le répertoire du client
- Chaque donnée collectée est écrite sur disque avant envoi (JSON pour keylog/clipboard, PNG pour screenshots)
- Après ACK serveur → fichier supprimé du spool
- Au démarrage : vider le spool (envoyer les fichiers en attente)

### Minuteries
| Source | Déclencheur | Intervalle |
|---|---|---|
| Keylogger | Timer périodique | 60s |
| Clipboard | Événement onChange | immédiat |
| Screenshot | Timer périodique | 5min (si activé) |
| Envoi spool | Connexion disponible | continu |

### Commandes serveur ajoutées
- `auto_exfil_on` / `auto_exfil_off` : activer/désactiver l'exfil auto depuis le GUI
- `set_keylog_interval <secondes>` : changer l'intervalle

---

## 4. SP3 — Persistance discrète (persistence.py)

### Noms aléatoires
- Nom du service généré à partir d'une liste de noms système légitimes (`WindowsUpdateHelper`, `ServiceHost`, `SystemSync`, etc.)
- Suffixe aléatoire 4 hex chars : `WindowsUpdateHelper_a3f2`
- Même logique pour crontab (Linux) et LaunchAgent (macOS)

### Fallback multi-méthode
Ordre de tentative Windows :
1. Registre `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
2. Dossier Startup utilisateur
3. Tâche planifiée (schtasks)

Dès qu'une méthode réussit → stop. Si toutes échouent → log d'erreur contextuel.

### Vérification automatique
- Au démarrage du client : `persistence.verify()` vérifie que la clé/crontab existe encore
- Si absente → réinstalle automatiquement
- Chemin dynamique : `sys.executable` au lieu de chemins hardcodés

---

## 5. Ce qui ne change pas

- Le protocole réseau (format des messages, chiffrement AES)
- L'interface GUI (`server_gui.py`) — sauf ajout des boutons `auto_exfil_on/off`
- `crypto_utils.py`
- `report_generator.py`
