# 🤖 RSSHub to Mastodon Bot

Un bot automatisé qui récupère les tweets d'un compte Twitter via RSSHub et les poste sur Mastodon avec les médias en natif.

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Docker](https://img.shields.io/badge/docker-enabled-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Fonctionnalités

- ✅ **Récupère les tweets** via flux RSSHub local ou public
- ✅ **Extrait les médias** (images, vidéos) de la description HTML
- ✅ **Poste sur Mastodon** avec les médias en natif
- ✅ **Nettoyage HTML** automatique des descriptions
- ✅ **Cache des tweets** pour éviter les doublons
- ✅ **Message d'auto-destruction** au démarrage (avec humour 😄)
- ✅ **Vérification périodique** (30 minutes par défaut)
- ✅ **Déploiement Docker** simple et rapide
- ✅ **Gestion des entités HTML** (`&amp;` → `&`)
- ✅ **Support des vidéos** (MP4, WebM)

---

## 🚀 Installation rapide

### Prérequis

- Docker & Docker Compose
- Compte Mastodon + Token API
- Instance RSSHub locale ou publique

### 1️⃣ Clone ou crée le dossier

```bash
mkdir rss-mastodon-bot
cd rss-mastodon-bot
```

### 2️⃣ Crée les fichiers

**Dockerfile** :
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install feedparser requests
COPY bot.py .
CMD ["python", "-u", "bot.py"]
```

**docker-compose.yml** :
```yaml
services:
  rss-mastodon-bot:
    build: .
    container_name: rss-mastodon-bot
    environment:
      MASTODON_TOKEN: "ton_token_ici"
      MASTODON_URL: "https://mastodon.social"
      RSSHUB_URL: "http://host.docker.internal:1200/twitter/user/L_ThinkTank"
      CHECK_INTERVAL: "1800"
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### 3️⃣ Récupère le bot.py

Télécharge le fichier `bot.py` de ce repo.

### 4️⃣ Démarre le bot

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `MASTODON_TOKEN` | Token API Mastodon | `""` |
| `MASTODON_URL` | URL instance Mastodon | `https://mastodon.social` |
| `RSSHUB_URL` | URL flux RSSHub | `http://host.docker.internal:1200/twitter/user/L_ThinkTank` |
| `CHECK_INTERVAL` | Intervalle de vérification (secondes) | `1800` (30 min) |

### Obtenir le token Mastodon

1. Accède à Préférences → Paramètres → Applications → Nouvelle application
2. Nomme l'app et autorise : `read:statuses` `write:statuses` `write:media`
3. Copie le token d'accès

### Configuration de RSSHub

**Option 1 : Local (Docker)**
```bash
docker run -d -p 1200:1200 diylc/rsshub
```

**Option 2 : Public**
```
https://rsshub.app/twitter/user/USERNAME
```

---

## 📊 Architecture

```
┌─────────────────────────┐
│  Bot Container          │
├─────────────────────────┤
│ bot.py                  │
│ - Récupère flux RSSHub  │
│ - Extrait images/vidéos │
│ - Poste sur Mastodon    │
│ - Cache les tweets      │
└─────────────────────────┘
         ↓
┌─────────────────────────┐
│  RSSHub (Local/Public)  │
│  Flux Twitter           │
└─────────────────────────┘
         ↓
┌─────────────────────────┐
│  Mastodon Instance      │
│  Posts avec médias      │
└─────────────────────────┘
```

---

## 📝 Utilisation

### Démarrage

```bash
docker-compose up -d
```

### Logs en direct

```bash
docker-compose logs -f
```

### Arrêt

```bash
docker-compose down
```

### Redémarrage

```bash
docker-compose restart
```

---

## 🔍 Logs et Debug

Le bot affiche des logs détaillés :

```
[INIT] Bot started with RSSHub + Media extraction
[OK] Startup message posted
[INFO] Waiting 30s before delete...
[OK] Startup message deleted! 💣
[INIT] Cached: 5
[INFO] Checking RSSHub...
[DEBUG] Latest tweet: [Titre du tweet...]
[INFO] Found 2 images in description
[OK] Media uploaded: 115549257326252217
[OK] Posted (ID: 115549257005214725): [Description...]
[OK] Posted 1 new tweets
```

### Dépannage

**Le bot ne démarre pas**
```bash
docker-compose build --no-cache
docker-compose up -d
docker-compose logs
```

**Les médias ne sont pas téléchargés**
- Vérifiez que les URLs d'images répondent (200)
- Vérifiez le token Mastodon
- Vérifiez les permissions du token

**Erreur 422 Mastodon**
- Vérifiez que le format du statut est valide
- Vérifiez que les IDs des médias sont corrects
- Vérifiez la limite de caractères Mastodon

---

## 🎨 Personnalisation

### Modifier l'intervalle de vérification

Dans `docker-compose.yml` :
```yaml
CHECK_INTERVAL: "300"  # 5 minutes
```

### Modifier le message d'auto-destruction

Dans `bot.py`, ligne ~80 :
```python
startup_msg = f"""🤖 Ton message personnalisé ici
..."""
```

### Modifier les sources Twitter

Dans `docker-compose.yml` :
```yaml
RSSHUB_URL: "http://host.docker.internal:1200/twitter/user/AUTRE_COMPTE"
```

---

## 📂 Structure du projet

```
rss-mastodon-bot/
├── Dockerfile
├── docker-compose.yml
├── bot.py
├── posted_urls.json      # Cache (créé auto)
└── README.md
```

---

## 🔄 Flux de fonctionnement

```
1. Démarrage
   ├─ Poste message "Startup" + emoji
   └─ Supprime le message après 30s

2. Première exécution
   ├─ Récupère le flux RSSHub
   ├─ Extrait la dernière entrée
   ├─ Upload les médias
   └─ Poste sur Mastodon

3. Boucle infinie (30 min d'intervalle)
   ├─ Récupère le flux
   ├─ Vérifie les nouveaux tweets
   ├─ Pour chaque nouveau tweet :
   │  ├─ Extrait images/vidéos
   │  ├─ Upload sur Mastodon
   │  └─ Poste le tweet
   └─ Cache le tweet posté
```

---

## 🐛 Problèmes connus

### Les images ne s'affichent pas

**Cause** : Entités HTML mal décodées (`&amp;` au lieu de `&`)
**Solution** : Le bot décode automatiquement les entités

### Les vidéos ne téléchargent pas

**Cause** : Format non supporté ou URL invalide
**Solution** : Vérifiez le format (MP4, WebM)

### Erreur "Connection refused"

**Cause** : RSSHub local non accessible
**Solution** : Utilisez `host.docker.internal` ou une URL publique

---

## 📊 Performance

- **Utilisation CPU** : Minimal (veille 30 min)
- **Utilisation RAM** : ~50-100MB
- **Bande passante** : ~1-5MB par tweet (avec médias)
- **Temps de traitement** : 5-30s par tweet (dépend de la taille)

---

## 🤝 Contribution

Les contributions sont bienvenues ! 

Pour contribuer :
1. Fork le repo
2. Crée une branche (`git checkout -b feature/AméliorationX`)
3. Commit tes changements (`git commit -m 'Add feature X'`)
4. Push (`git push origin feature/AméliorationX`)
5. Ouvre une Pull Request

---

## 📜 License

MIT License - Libre d'utilisation commerciale et personnelle

---

## 🙏 Remerciements

- **RSSHub** : Pour l'agrégation de flux Twitter
- **Mastodon** : Pour l'API ouverte
- **Docker** : Pour la conteneurisation

---

## 📞 Support

Pour les questions ou problèmes :
- Ouvrez une **Issue** sur GitHub
- Vérifiez les logs : `docker-compose logs -f`
- Consultez la section **Dépannage**

---

## 📚 Ressources utiles

- [RSSHub Documentation](https://docs.rsshub.app)
- [Mastodon API Docs](https://docs.joinmastodon.org)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file)
- [feedparser Docs](https://pythonhosted.org/feedparser)

---

**Fait avec ❤️ pour les amateurs de Mastodon & bots**

