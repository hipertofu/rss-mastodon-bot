# 🤖 RSSHub to Mastodon Bot

Bot automatisé multi-profils pour diffuser des flux RSS Twitter/X vers Mastodon avec gestion complète via interface web avec support des vidéos et images, découpée en threads intelligents.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen)

## 🎯 Fonctionnalités

✅ **Multi-profils** - Gérez plusieurs bots simultanément (chacun avec son compte Mastodon)  
✅ **Surveillance RSS automatique** - Vérifie régulièrement le flux RSS via RSSHub  
✅ **Multi-sources RSS** - Surveillez plusieurs comptes Twitter/X par profil  
✅ **Anti-doublon intelligent** - Si une source détecte un nouveau post, les autres sont ignorées  
✅ **Publication Mastodon** - Publie les posts automatiquement sur votre instance Mastodon   
✅ **Suppression des citations** - Ignore les tweets cités
✅ **Threads intelligents** - Découpe automatiquement les longs posts en threads  
✅ **Interface web** - Panneau de contrôle Material Design 3 avec configuration en temps réel  
✅ **Message de démarrage** - Teste votre token avec un message auto-supprimable  
✅ **Variables personnalisables** - Personnalisez les messages de démarrage et de continuation  
✅ **Cache intelligent** - Évite de republier les mêmes posts  
✅ **Gestion des erreurs robuste** - Logs détaillés et gestion des rate limits  
✅ **Persistance des données** - Volumes Docker pour ne jamais perdre vos configurations  

## 📋 Prérequis

- Docker
- Token API Mastodon (avec permission `write:statuses`)
- URL d'un flux RSSHub fonctionnel
- Accès à RSSHub (interne ou externe)

## 🚀 Installation

### 1. Cloner le repository

```
git clone [<votre-url-repo>](https://github.com/hipertofu/rss-mastodon-bot)
cd rss-mastodon-bot
```

### 2. Créer les fichiers de configuration

```

# Créer les dossiers de données

mkdir -p data/cache
chmod 777 data
chmod 777 data/cache

# Créer requirements.txt
cat > requirements.txt << 'EOF'
feedparser==6.0.10
requests==2.31.0
Flask==2.3.0
EOF

# Créer docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  rss-mastodon-bot:
    build: .
    container_name: rss-mastodon-bot
    ports:
      - "5000:5000"
    environment:
      MASTODON_TOKEN: ${MASTODON_TOKEN:-}
      MASTODON_URL: ${MASTODON_URL:-https://mastodon.social}
      RSSHUB_URL: ${RSSHUB_URL:-http://host.docker.internal:1200/twitter/user/username}
      CHECK_INTERVAL: "1800"
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./config.json:/app/config.json
      - ./posted_urls.json:/app/posted_urls.json
EOF
```

### 3. Configuration initiale

```
# Créer le dossier templates
mkdir -p templates

# Copier les fichiers bot.py, app.py et templates/index.html
# (voir les fichiers fournis)
```

### 4. Lancer le bot

```
# Build et démarrage
docker-compose build
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

### 5. Accéder à l'interface web

Ouvrez votre navigateur et allez à : **http://localhost:5000**

## ⚙️ Configuration

### Via l'interface web (recommandé)

1. Accédez à `http://localhost:5000`
2. Remplissez les paramètres :
   - **URL Mastodon** : Votre instance Mastodon (ex: `https://mastodon.social`)
   - **Token API** : Votre token Mastodon
   - **URL RSSHub** : Votre flux RSS (ex: `http://localhost:1200/twitter/user/username`)
   - **Compte Twitter** : Le compte à surveiller
   - **Autres paramètres** : Intervalle, délais, messages personnalisés
3. Cliquez sur **Sauvegarder**

### Via fichier config.json

```
{
  "MASTODON_URL": "https://mastodon.social",
  "MASTODON_TOKEN": "votre_token_ici",
  "RSSHUB_URL": "http://host.docker.internal:1200/twitter/user/username",
  "TWITTER_ACCOUNT": "username",
  "CHECK_INTERVAL": "1800",
  "AUTO_DELETE_DELAY": "30",
  "AUTODESTRUCT_VIDEO_URL": "https://media.giphy.com/media/7G9jJdKhlCrED7vEvT/giphy.mp4",
  "MAX_CHAR_PER_POST": "490",
  "STARTUP_MESSAGE_TEMPLATE": "🤖 Bot démarrage: {HEURE}\n📡 Surveillance: @{TWITTER_ACCOUNT}\n⏰ Auto-suppression dans {DELAY}s",
  "CONTINUATION_MESSAGE": "[La suite dans les commentaires 👇]"
}
```

## 🎯 Obtenir votre token Mastodon

1. Allez sur votre instance Mastodon (ex: mastodon.social)
2. Paramètres → Applications → Nouvelle application
3. Remplissez le formulaire :
   - **Nom** : RSSHub Bot
   - **Redirection URI** : `urn:ietf:wg:oauth:2.0:oob`
   - **Permissions** : Cochez `write:statuses` (minimum)
4. Cliquez sur **Soumettre**
5. Copiez le **Token d'accès**

## 🔗 Configuration RSSHub

### Exemple avec Twitter

```
http://localhost:1200/twitter/user/L_ThinkTank
```

### Documentation RSSHub

Pour d'autres sources RSS : [https://docs.rsshub.app/](https://docs.rsshub.app/)

## 📱 Interface Web

L'interface web (Material Design 3) vous permet de :

- ✏️ Modifier la configuration en temps réel
- 🎬 Tester les posts avant publication
- 🎨 Personnaliser les messages de démarrage
- 📊 Monitorer les paramètres du bot

### Variables de personnalisation

**Message de démarrage :**
- `{HEURE}` - Heure actuelle (HH:MM:SS)
- `{DATE}` - Date actuelle (DD/MM/YYYY)
- `{TWITTER_ACCOUNT}` - Nom du compte surveillé
- `{DELAY}` - Délai avant suppression automatique

## 🧪 Test

Utilisez le bouton **Test Post** dans l'interface web pour vérifier :
- La connexion RSSHub
- La connexion Mastodon
- Le upload de médias
- La publication sur Mastodon

## 📊 Logs

Les logs sont disponibles via Docker :

```
# Logs en temps réel
docker-compose logs -f

# Logs du bot uniquement
docker-compose logs -f rss-mastodon-bot | grep "$$BOT$$"
```

## 🤝 Exemple en production

Ce script alimente actuellement le compte Mastodon :

**🦣 [@ThinkTankNotOfficial@mastodon.social](https://mastodon.social/@ThinkTankNotOfficial)**

## 🛠️ Architecture

```
┌─────────────┐
│   Twitter   │
│   Account   │
└──────┬──────┘
       │
       ├─────────────────────────┐
       │                         │
   ┌───┴────────┐         ┌──────┴───────┐
   │  RSSHub    │ ◄────── │  RSS Feed    │
   └────┬───────┘         └──────────────┘
        │
        │ (HTTP Request)
        │
   ┌────┴──────────────────────┐
   │   Docker Container        │
   │  ┌──────────────────────┐ │
   │  │   bot.py             │ │
   │  │ (Monitoring + Posts) │ │
   │  └──────────────────────┘ │
   │  ┌──────────────────────┐ │
   │  │   app.py             │ │
   │  │ (Web UI + API)       │ │
   │  └──────────────────────┘ │
   └────┬──────────────────────┘
        │
        ├──────────────────┐
        │                  │
    ┌───┴────────┐    ┌────┴──────────┐
    │  Mastodon  │    │  Web Browser  │
    │  Instance  │    │  (localhost)  │
    │            │    │  Port 5000    │
    └────────────┘    └───────────────┘
```

## 📝 Fichiers principaux

- **bot.py** - Script de monitoring et publication
- **app.py** - API Flask et interface web
- **templates/index.html** - Interface web Material Design 3
- **docker-compose.yml** - Configuration Docker
- **Dockerfile** - Image Docker
- **config.json** - Configuration persistante

## ⚠️ Notes importantes

- Le **token Mastodon** doit avoir la permission `write:statuses`
- RSSHub doit être accessible (localement ou via réseau)
- Les messages de démarrage s'auto-suppriment après le délai configuré
- Le cache `posted_urls.json` évite les doublons
- Les videos ont priorité sur les images
- Les citations Twitter (rsshub-quote) sont automatiquement supprimées

## 🐛 Troubleshooting

### Le bot ne publie rien

```
# Vérifier les logs
docker-compose logs -f

# Vérifier la configuration
docker exec rss-mastodon-bot cat config.json

# Redémarrer
docker-compose restart
```

### Erreur de connexion Mastodon

- Vérifiez votre token
- Vérifiez l'URL de l'instance
- Vérifiez les permissions du token

### Erreur RSSHub

- Vérifiez l'URL RSSHub
- Vérifiez que RSSHub est accessible
- Testez manuellement l'URL dans un navigateur

## 📧 Support

Pour toute question ou problème, ouvrez une [Issue GitHub](https://github.com/votre-username/rss-mastodon-bot/issues)

---

**Made with ❤️**
