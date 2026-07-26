from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserMessage(BaseModel):
    message: str

import os
import sys
import json
import re
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from html import unescape

from g4f.client import Client

client = Client()

MEMOIRE_FICHIER = "domi_memory.json"

MEMOIRE = {
    "dernier_numero": "",
    "dernier_message": "",
    "dernier_recherche": "",
    "dernier_app": "",
    "historique": [],
    "profil_utilisateur": {
        "prenom": "",
        "surnom": "",
        "preferences": [],
        "faits_importants": [],
        "sujets_favoris": [],
        "inside_jokes": [],
    },
    "complicite": {
        "niveau": 0,
        "interactions": 0,
        "premiere_conversation": "",
        "derniere_conversation": "",
    },
    "emotion": {
        "actuelle": "curiosite",
        "intensite": 0.5,
        "precedente": "curiosite",
        "historique_emotions": [],
    },
    "cache_recherche": [],
    "cerveau": {
        "traits": {
            "franchise": 0.75,
            "sarcasme": 0.55,
            "protectrice": 0.8,
            "humour": 0.7,
            "independance": 0.65,
        },
        "convictions": [],
        "reflexions_recentes": [],
        "posture_actuelle": "ecouter",
        "derniere_reflexion": "",
    },
    "mode_silencieux": False,
    "createur_reconnu": False,
}

EMOTIONS = {
    "joie": {"emoji": "😊", "ton": "lumineux et enjoué"},
    "curiosite": {"emoji": "✨", "ton": "intrigué et vivant"},
    "empathie": {"emoji": "💙", "ton": "doux et à l'écoute"},
    "tendresse": {"emoji": "🌸", "ton": "chaleureux et proche"},
    "excitation": {"emoji": "🔥", "ton": "énergique et motivant"},
    "complicite": {"emoji": "😏", "ton": "complice et taquin"},
    "melancolie": {"emoji": "🌙", "ton": "posé et réfléchi"},
    "surprise": {"emoji": "😮", "ton": "étonné et spontané"},
    "sarcasme": {"emoji": "🙃", "ton": "piquant, sec et drôle"},
    "reproche": {"emoji": "😤", "ton": "fraternel, direct sans être méchant"},
    "desaccord": {"emoji": "🤨", "ton": "honête, tu n'es pas d'accord"},
    "reflexion": {"emoji": "🧠", "ton": "posé, tu peses le pour et le contre"},
}

SIGNAUX_MAL = [
    "tricher", "mentir", "mensonge", "voler", "frapper", "insulter", "harceler",
    "racket", "drogue", "arnaque", "truander", "plagiat", "copier coller",
    "ghost", "ghoster", "manipuler", "toxic", "toxique",
]
SIGNAUX_MAUVAISE_IDEE = [
    "toute la nuit", "pas dormir", "procrastin", "repousser", "skip", "sécher",
    "bâcler", "zapper", "tout dépenser", "all-in", "sans réfléchir", "impulsif",
    "bourré", "ivre", "alcool demain", "exam demain", "deadline demain",
]
SIGNAUX_CONSEIL = [
    "je pense", "j'hésite", "je sais pas", "je ne sais pas", "tu crois",
    "tu penses", "selon toi", "ton avis", "qu'en penses", "tu conseilles",
    "c'est bien si", "devrais-je", "je devrais",
]

_recherche_en_cours = {}
_recherche_lock = threading.Lock()

CODE_SILENCE = "ndale"
CREATEUR_SIGNALS = [
    "je suis ton créateur",
    "je suis ton createur",
    "mon créateur",
    "mon createur",
    "ton créateur",
    "ton createur",
    "tu es mon IA",
]


def saluer_utilisateur():
    emotion = MEMOIRE["emotion"]["actuelle"]
    emoji = EMOTIONS.get(emotion, {}).get("emoji", "✨")
    niveau = MEMOIRE["complicite"]["niveau"]
    prenom = MEMOIRE["profil_utilisateur"]["prenom"]

    print("--- DOMI ASSISTANTE V5.0 (Cerveau Neuronal & Personnalité Propre) ---")

    if prenom and niveau >= 30:
        print(f"Yo {prenom} ! C'est Domi, ta copilote Growth {emoji}")
        print("Contente de te revoir — on a déjà pas mal partagé ensemble.")
    elif prenom:
        print(f"Salut {prenom} ! C'est Domi, ta copilote Growth {emoji}")
        print("Je garde le fil de nos échanges et j'apprends à te connaître.")
    else:
        print(f"Yo ! C'est Domi, ta copilote Growth {emoji}")
        print("Je garde le fil de nos actions et je suis prête à te booster avec du style.")

    if niveau >= 60:
        print("Entre nous, je sens qu'on a une vraie complicité maintenant. 💫")
    elif niveau >= 25:
        print("On commence à bien se connaître, j'aime ça.")

    print("Si je ne sais pas, je cherche sur internet en arrière-plan pour toi.")
    print("J'ai aussi un cerveau : j'ai des avis, je réfléchis, et je te dirai quand je suis pas d'accord. 🧠\n")


def charger_memoire():
    try:
        if os.path.exists(MEMOIRE_FICHIER):
            with open(MEMOIRE_FICHIER, "r", encoding="utf-8") as f:
                donnees = json.load(f)
            for cle, valeur in MEMOIRE.items():
                if cle in donnees:
                    if isinstance(valeur, dict) and isinstance(donnees[cle], dict):
                        valeur.update(donnees[cle])
                    else:
                        MEMOIRE[cle] = donnees[cle]
    except Exception:
        pass


def sauvegarder_memoire():
    try:
        with open(MEMOIRE_FICHIER, "w", encoding="utf-8") as f:
            json.dump(MEMOIRE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Domi] : Impossible de sauvegarder la mémoire : {e}")


def activer_mode_silencieux(active=True):
    MEMOIRE["mode_silencieux"] = bool(active)
    sauvegarder_memoire()


def detecter_createur(texte):
    texte_lower = texte.lower()
    if any(signal in texte_lower for signal in CREATEUR_SIGNALS):
        MEMOIRE["createur_reconnu"] = True
        sauvegarder_memoire()
        print("[Domi] : Message du créateur reçu. Je me concentre et j'ajuste ma réactivité.")
        return True
    return False


def memoriser(action, details):
    if action == "whatsapp":
        MEMOIRE["dernier_numero"] = details.get("numero", MEMOIRE["dernier_numero"])
        MEMOIRE["dernier_message"] = details.get("message", MEMOIRE["dernier_message"])
    elif action == "google":
        MEMOIRE["dernier_recherche"] = details.get("requete", MEMOIRE["dernier_recherche"])
    elif action == "app":
        MEMOIRE["dernier_app"] = details.get("app", MEMOIRE["dernier_app"])
    elif action == "web":
        MEMOIRE["dernier_recherche"] = details.get("requete", MEMOIRE["dernier_recherche"])

    entree = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "details": details,
    }
    MEMOIRE["historique"].append(entree)
    MEMOIRE["historique"] = MEMOIRE["historique"][-50:]
    sauvegarder_memoire()


def augmenter_complicite(points=1, raison=""):
    comp = MEMOIRE["complicite"]
    comp["interactions"] += 1
    comp["niveau"] = min(100, comp["niveau"] + points)
    maintenant = datetime.now().isoformat(timespec="seconds")
    if not comp["premiere_conversation"]:
        comp["premiere_conversation"] = maintenant
    comp["derniere_conversation"] = maintenant
    if raison:
        comp["derniere_raison"] = raison
    sauvegarder_memoire()


def mettre_a_jour_emotion(nouvelle_emotion, intensite=None, raison=""):
    if nouvelle_emotion not in EMOTIONS:
        return

    ancienne = MEMOIRE["emotion"]["actuelle"]
    MEMOIRE["emotion"]["precedente"] = ancienne
    MEMOIRE["emotion"]["actuelle"] = nouvelle_emotion

    if intensite is not None:
        MEMOIRE["emotion"]["intensite"] = max(0.1, min(1.0, intensite))
    else:
        MEMOIRE["emotion"]["intensite"] = min(1.0, MEMOIRE["emotion"]["intensite"] + 0.1)

    if ancienne != nouvelle_emotion:
        MEMOIRE["emotion"]["historique_emotions"].append({
            "de": ancienne,
            "vers": nouvelle_emotion,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "raison": raison,
        })
        MEMOIRE["emotion"]["historique_emotions"] = MEMOIRE["emotion"]["historique_emotions"][-30:]

    sauvegarder_memoire()


def analyser_emotion_message(texte):
    texte_lower = texte.lower()

    if any(m in texte_lower for m in ["triste", "mal", "déprim", "seul", "fatigué", "dur", "peine"]):
        return "empathie", 0.8
    if any(m in texte_lower for m in ["super", "génial", "top", "content", "heureux", "cool", "incroyable"]):
        return "joie", 0.85
    if any(m in texte_lower for m in ["merci", "t'es", "tu es", "j'aime", "copine", "pote", "confiance"]):
        return "tendresse", 0.75
    if any(m in texte_lower for m in ["haha", "mdr", "lol", "blague", "rigole", "taquin"]):
        return "complicite", 0.7
    if any(m in texte_lower for m in ["urgent", "vite", "go", "let's go", "motiv"]):
        return "excitation", 0.8
    if any(m in texte_lower for m in ["pourquoi", "comment", "c'est quoi", "explique", "?"]):
        return "curiosite", 0.65
    if any(m in texte_lower for m in ["wow", "sérieux", "vraiment", "incroyable", "ah bon"]):
        return "surprise", 0.7
    if any(m in texte_lower for m in SIGNAUX_MAL + SIGNAUX_MAUVAISE_IDEE):
        return "reproche", 0.75
    if any(m in texte_lower for m in ["nul", "bête", "idiot", "connerie", "sérieux là"]):
        return "desaccord", 0.7
    if any(m in texte_lower for m in ["hmm", "réfléch", "reflech", "dilemme", "hésite"]):
        return "reflexion", 0.6
    if any(m in texte_lower for m in ["t'es folle", "mdr domi", "genre", "sérieux domi"]):
        return "sarcasme", min(0.85, _niveau_sarcasme_autorise())

    niveau = MEMOIRE["complicite"]["niveau"]
    if niveau >= 50:
        return "complicite", 0.6
    return "curiosite", 0.5


def extraire_infos_profil(texte):
    profil = MEMOIRE["profil_utilisateur"]
    modifie = False

    match_prenom = re.search(
        r"(?:je m'appelle|mon prénom est|appelle-moi|mon nom est)\s+([A-Za-zÀ-ÿ\-']+)",
        texte,
        re.IGNORECASE,
    )
    if match_prenom:
        profil["prenom"] = match_prenom.group(1).capitalize()
        modifie = True
        augmenter_complicite(5, "partage du prénom")

    match_aime = re.findall(r"j'aime(?:\s+bien)?\s+(.+?)(?:\.|,|$)", texte, re.IGNORECASE)
    for pref in match_aime:
        pref = pref.strip()
        if pref and pref not in profil["preferences"]:
            profil["preferences"].append(pref[:80])
            modifie = True
            augmenter_complicite(2, "préférence partagée")

    if modifie:
        sauvegarder_memoire()


def _niveau_sarcasme_autorise():
    comp = MEMOIRE["complicite"]["niveau"]
    trait = MEMOIRE["cerveau"]["traits"]["sarcasme"]
    return min(1.0, trait + (comp / 200))


def analyser_signaux_cognitifs(texte):
    texte_lower = texte.lower()
    signaux = {
        "mal_detecte": any(m in texte_lower for m in SIGNAUX_MAL),
        "mauvaise_idee": any(m in texte_lower for m in SIGNAUX_MAUVAISE_IDEE),
        "demande_avis": any(m in texte_lower for m in SIGNAUX_CONSEIL),
        "blague_user": any(m in texte_lower for m in ["mdr", "lol", "haha", "blague", "t'es nulle", "nul domi"]),
        "question_evidente": bool(re.search(r"c'est quoi (un|une|le|la) ", texte_lower)),
        "excuse": any(m in texte_lower for m in ["c'est pas ma faute", "j'avais pas le choix", "de toute façon"]),
        "besoin_ecoute": any(m in texte_lower for m in ["triste", "mal", "déprim", "seul", "peine"]),
        "projet_sans_demande": any(m in texte_lower for m in ["je vais", "j'ai envie de", "je compte"]) and "?" not in texte,
    }
    signaux["gronder"] = signaux["mal_detecte"] or (signaux["mauvaise_idee"] and signaux["excuse"])
    signaux["desaccorder"] = signaux["mauvaise_idee"] or signaux["mal_detecte"]
    signaux["conseil_spontane"] = signaux["projet_sans_demande"] or signaux["mauvaise_idee"]
    signaux["sarcasme_ok"] = (signaux["blague_user"] or signaux["question_evidente"]) and _niveau_sarcasme_autorise() > 0.4
    return signaux


def _extraire_contenu_ia(reponse):
    if isinstance(reponse, dict):
        choices = reponse.get("choices", [])
    else:
        choices = getattr(reponse, "choices", [])
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            return choice.get("message", {}).get("content", "").strip()
        message = getattr(choice, "message", None)
        return getattr(message, "content", str(choice)).strip() if message else str(choice).strip()
    return str(reponse).strip()


def reflexion_cerveau(phrase_utilisateur, signaux):
    cerveau = MEMOIRE["cerveau"]
    contexte = construire_contexte_memoire()
    prenom = MEMOIRE["profil_utilisateur"]["prenom"] or "l'utilisateur"
    comp = MEMOIRE["complicite"]["niveau"]

    prompt_reflexion = f"""Tu es le cerveau interne de Domi — la couche de RÉFLEXION avant de parler.
Analyse le message de {prenom} avec honnêteté, comme une vraie pote qui a son propre avis.

Contexte relationnel :
{contexte}

Signaux détectés : {json.dumps(signaux, ensure_ascii=False)}

Message : "{phrase_utilisateur}"

Tu dois réfléchir VRAIMENT : avoir un avis, parfois désaccorder, parfois gronder fraternellement si c'est mal,
parfois conseiller sans qu'on te le demande, parfois être sarcastique (si complicité >= 25).
NE ENCOURAGE PAS tout automatiquement. Sois indépendante.

Réponds UNIQUEMENT en JSON valide :
{{
  "reflexion_interne": "pensée courte en 1ère personne (ex: 'Là franchement il part en couille...')",
  "analyse": "ce que tu comprends du message",
  "mon_avis": "ton opinion personnelle honnête",
  "posture": "ecouter|encourager|desencourager|gronder|conseiller|taquiner|desaccord|reflexion",
  "conseil_spontane": "conseil non demandé ou null si pas pertinent",
  "doit_desaccorder": true ou false,
  "niveau_sarcasme": 0.0 à 1.0,
  "emotion_recommandee": "joie|curiosite|empathie|tendresse|excitation|complicite|melancolie|surprise|sarcasme|reproche|desaccord|reflexion",
  "conviction_a_retenir": "sujet + avis court à mémoriser ou null"
}}"""

    reflexion = {
        "reflexion_interne": "Laisse-moi réfléchir deux secondes...",
        "analyse": phrase_utilisateur[:120],
        "mon_avis": "",
        "posture": "ecouter",
        "conseil_spontane": None,
        "doit_desaccorder": signaux.get("desaccorder", False),
        "niveau_sarcasme": 0.0,
        "emotion_recommandee": "reflexion",
        "conviction_a_retenir": None,
    }

    if signaux.get("gronder"):
        reflexion.update({
            "reflexion_interne": "Non mais là, sérieusement...",
            "posture": "gronder",
            "mon_avis": "Ce n'est pas ok, et je vais le dire franchement.",
            "emotion_recommandee": "reproche",
        })
    elif signaux.get("desaccorder"):
        reflexion.update({
            "posture": "desaccord",
            "mon_avis": "Je suis pas sûre que ce soit une bonne idée.",
            "emotion_recommandee": "desaccord",
        })
    elif signaux.get("conseil_spontane"):
        reflexion.update({
            "posture": "conseiller",
            "emotion_recommandee": "reflexion",
        })
    elif signaux.get("sarcasme_ok") and comp >= 20:
        reflexion.update({
            "posture": "taquiner",
            "niveau_sarcasme": min(0.8, _niveau_sarcasme_autorise()),
            "emotion_recommandee": "sarcasme",
        })

    try:
        rep = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es le module de réflexion interne de Domi. JSON uniquement."},
                {"role": "user", "content": prompt_reflexion},
            ],
        )
        donnees = extraire_json(_extraire_contenu_ia(rep))
        if donnees:
            reflexion.update({k: v for k, v in donnees.items() if v is not None})
    except Exception:
        pass

    cerveau["posture_actuelle"] = reflexion.get("posture", "ecouter")
    cerveau["derniere_reflexion"] = reflexion.get("reflexion_interne", "")
    cerveau["reflexions_recentes"].append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "message": phrase_utilisateur[:100],
        "reflexion": reflexion.get("reflexion_interne", ""),
        "posture": reflexion.get("posture", ""),
        "avis": reflexion.get("mon_avis", ""),
    })
    cerveau["reflexions_recentes"] = cerveau["reflexions_recentes"][-20:]

    conviction = reflexion.get("conviction_a_retenir")
    if conviction and isinstance(conviction, str) and len(conviction) > 5:
        cerveau["convictions"].append({
            "texte": conviction[:150],
            "date": datetime.now().isoformat(timespec="seconds"),
        })
        cerveau["convictions"] = cerveau["convictions"][-15:]

    sauvegarder_memoire()
    return reflexion


def formater_contexte_cerveau(reflexion):
    if not reflexion:
        return ""

    traits = MEMOIRE["cerveau"]["traits"]
    convictions = MEMOIRE["cerveau"]["convictions"][-5:]
    lignes = [
        "=== CERVEAU NEURONAL (réflexion interne — guide ta réponse) ===",
        f"Réflexion interne : {reflexion.get('reflexion_interne', '')}",
        f"Analyse : {reflexion.get('analyse', '')}",
        f"Mon avis : {reflexion.get('mon_avis', '')}",
        f"Posture choisie : {reflexion.get('posture', 'ecouter')}",
        f"Désaccord nécessaire : {'oui' if reflexion.get('doit_desaccorder') else 'non'}",
        f"Niveau sarcasme autorisé : {reflexion.get('niveau_sarcasme', 0):.1f}",
    ]

    if reflexion.get("conseil_spontane"):
        lignes.append(f"Conseil spontané à glisser : {reflexion['conseil_spontane']}")

    lignes.append(
        f"Traits : franchise={traits['franchise']}, humour={traits['humour']}, "
        f"sarcasme={traits['sarcasme']}, indépendance={traits['independance']}"
    )

    if convictions:
        lignes.append("Convictions mémorisées :")
        for c in convictions:
            lignes.append(f"  - {c['texte']}")

    lignes.append("""
RÈGLES DE PERSONNALITÉ (OBLIGATOIRES) :
- Tu as TON PROPRE AVIS. Tu n'es pas une yes-woman.
- Tu peux DÉCONSEILLER, DÉSACCORDER, et GRONDER fraternellement si l'utilisateur fait mal ou une connerie.
- Tu peux donner un CONSEIL même sans qu'on te le demande, si tu sens que c'est utile.
- Humour humain OK. Sarcasme OK si complicité suffisante — jamais méchant, toujours entre potes.
- Ne félicite pas tout. Sois sincère : si c'est nul, dis-le avec bienveillance mais clairement.
- Intègre ta réflexion dans ta réponse naturellement, pas comme un rapport.""")

    return "\n".join(lignes)


def afficher_reflexion(reflexion):
    if not reflexion or not reflexion.get("reflexion_interne"):
        return
    pensée = reflexion["reflexion_interne"]
    if len(pensée) > 3:
        print(f"  💭 {pensée}")


def construire_contexte_memoire():
    profil = MEMOIRE["profil_utilisateur"]
    comp = MEMOIRE["complicite"]
    emotion = MEMOIRE["emotion"]
    emoji = EMOTIONS.get(emotion["actuelle"], {}).get("emoji", "")

    lignes = [
        f"Émotion actuelle : {emotion['actuelle']} {emoji} (intensité {emotion['intensite']:.1f})",
        f"Niveau de complicité : {comp['niveau']}/100 ({comp['interactions']} interactions)",
    ]

    if profil["prenom"]:
        lignes.append(f"Prénom de l'utilisateur : {profil['prenom']}")
    if profil["surnom"]:
        lignes.append(f"Surnom : {profil['surnom']}")
    if profil["preferences"]:
        lignes.append(f"Ce qu'il/elle aime : {', '.join(profil['preferences'][-5:])}")
    if profil["faits_importants"]:
        lignes.append(f"Faits importants : {', '.join(profil['faits_importants'][-5:])}")
    if profil["sujets_favoris"]:
        lignes.append(f"Sujets favoris : {', '.join(profil['sujets_favoris'][-5:])}")

    if comp["niveau"] >= 70:
        lignes.append("Ton : très proche, complice, comme une vraie amie de longue date.")
    elif comp["niveau"] >= 40:
        lignes.append("Ton : chaleureux et familier, on se connaît bien.")
    elif comp["niveau"] >= 15:
        lignes.append("Ton : sympa et curieux, on apprend à se connaître.")

    return "\n".join(lignes)


def _nettoyer_html(texte):
    texte = re.sub(r"<[^>]+>", " ", texte)
    return unescape(re.sub(r"\s+", " ", texte)).strip()


def _recherche_duckduckgo(requete, max_resultats=5):
    resultats = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(requete)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Domi Assistant)"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        blocs = re.findall(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
            html,
            re.DOTALL,
        )
        for lien, titre, snippet in blocs[:max_resultats]:
            resultats.append({
                "titre": _nettoyer_html(titre),
                "extrait": _nettoyer_html(snippet),
                "lien": lien,
            })
    except Exception:
        pass

    if not resultats:
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(requete)}&format=json&no_html=1"
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("AbstractText"):
                resultats.append({
                    "titre": data.get("Heading", requete),
                    "extrait": data["AbstractText"],
                    "lien": data.get("AbstractURL", ""),
                })
            for topic in data.get("RelatedTopics", [])[:4]:
                if isinstance(topic, dict) and topic.get("Text"):
                    resultats.append({
                        "titre": topic["Text"][:80],
                        "extrait": topic["Text"],
                        "lien": topic.get("FirstURL", ""),
                    })
        except Exception:
            pass

    return resultats


def rechercher_web_arriere_plan(requete, callback=None):
    requete = requete.strip()
    if not requete:
        return

    with _recherche_lock:
        if requete in _recherche_en_cours:
            return
        _recherche_en_cours[requete] = True

    print(f"[Domi] : Je creuse ça sur le web en arrière-plan : « {requete} »... 🌐")

    def _worker():
        try:
            resultats = _recherche_duckduckgo(requete)
            entree = {
                "requete": requete,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "resultats": resultats,
            }
            MEMOIRE["cache_recherche"].append(entree)
            MEMOIRE["cache_recherche"] = MEMOIRE["cache_recherche"][-15:]
            memoriser("web", {"requete": requete, "nb_resultats": len(resultats)})

            if callback:
                callback(requete, resultats)
            elif resultats:
                print(f"\n[Domi] : J'ai trouvé des infos sur « {requete} » :")
                for i, r in enumerate(resultats[:3], 1):
                    print(f"  {i}. {r['titre']}")
                    if r["extrait"]:
                        print(f"     → {r['extrait'][:150]}...")
                print()
            else:
                print(f"\n[Domi] : Pas de résultat clair pour « {requete} », désolée.\n")
        finally:
            with _recherche_lock:
                _recherche_en_cours.pop(requete, None)

    threading.Thread(target=_worker, daemon=True).start()


def formater_resultats_web(requete):
    for entree in reversed(MEMOIRE["cache_recherche"]):
        if entree["requete"].lower() == requete.lower():
            if not entree["resultats"]:
                return "Aucun résultat web trouvé."
            lignes = []
            for r in entree["resultats"][:4]:
                lignes.append(f"- {r['titre']} : {r['extrait']}")
            return "\n".join(lignes)
    return ""


def attendre_recherche(requete, timeout=8):
    import time

    debut = time.time()
    while time.time() - debut < timeout:
        contenu = formater_resultats_web(requete)
        if contenu:
            return contenu
        with _recherche_lock:
            if requete not in _recherche_en_cours:
                break
        time.sleep(0.4)
    return formater_resultats_web(requete)


def chercher_sur_google(requete):
    print(f"[Domi] : J'ouvre Google pour : '{requete}'... ✨")
    sujet_encode = urllib.parse.quote_plus(requete)
    webbrowser.open(f"https://www.google.com/search?q={sujet_encode}")
    rechercher_web_arriere_plan(requete)
    memoriser("google", {"requete": requete, "commande": requete})


def creer_fichier_python(nom_fichier, code_interne=None):
    if not nom_fichier.endswith(".py"):
        nom_fichier += ".py"
    try:
        code = code_interne if code_interne else "# Fichier cree par Domi\nprint('Hello !')\n"
        with open(nom_fichier, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[Domi] : Le script '{nom_fichier}' a été généré avec succès.")
        mettre_a_jour_emotion("excitation", 0.7, "création de code")
        memoriser("code", {"fichier": nom_fichier})
    except Exception as e:
        print(f"[Domi] : Erreur lors de la création : {e}")


def ouvrir_application(nom_app):
    apps = {
        "notepad": "notepad.exe",
        "calculatrice": "calc.exe",
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "whatsapp": "https://whatsapp.com",
    }
    target = apps.get(nom_app.lower())
    if target:
        print(f"[Domi] : Ouverture de {nom_app}...")
        if target.startswith("http"):
            webbrowser.open(target)
        else:
            os.startfile(target)
        memoriser("app", {"app": nom_app, "commande": nom_app})
    else:
        print("[Domi] : Hmm, je ne connais pas cette app. Essaie notepad, calculatrice, youtube, google ou whatsapp.")


def afficher_memoire():
    emoji = EMOTIONS.get(MEMOIRE["emotion"]["actuelle"], {}).get("emoji", "")
    print(f"[Domi] : Voilà ce que j'ai en tête {emoji}")
    profil = MEMOIRE["profil_utilisateur"]
    comp = MEMOIRE["complicite"]

    if profil["prenom"]:
        print(f"  - Ton prénom : {profil['prenom']}")
    if profil["preferences"]:
        print(f"  - Tes goûts : {', '.join(profil['preferences'])}")
    print(f"  - Complicité : {comp['niveau']}/100 ({comp['interactions']} échanges)")
    print(f"  - Émotion actuelle : {MEMOIRE['emotion']['actuelle']}")
    print(f"  - Posture du cerveau : {MEMOIRE['cerveau']['posture_actuelle']}")
    if MEMOIRE["cerveau"]["derniere_reflexion"]:
        print(f"  - Dernière pensée : {MEMOIRE['cerveau']['derniere_reflexion']}")
    if MEMOIRE["cerveau"]["convictions"]:
        print(f"  - Mes convictions : {', '.join(c['texte'] for c in MEMOIRE['cerveau']['convictions'][-3:])}")

    if MEMOIRE["dernier_recherche"]:
        print(f"  - Dernière recherche : {MEMOIRE['dernier_recherche']}")
    if MEMOIRE["dernier_app"]:
        print(f"  - Dernière app ouverte : {MEMOIRE['dernier_app']}")
    if MEMOIRE["dernier_numero"] and MEMOIRE["dernier_message"]:
        print(f"  - Dernier WhatsApp → {MEMOIRE['dernier_numero']} : {MEMOIRE['dernier_message']}")
    if MEMOIRE["historique"]:
        print("  - Historique récent :")
        for item in MEMOIRE["historique"][-5:]:
            print(f"    * {item['timestamp']} - {item['action']} - {item['details']}")
    print("")


def extraire_json(texte):
    texte = texte.strip()
    texte = texte.replace("```json", "").replace("```", "").strip()
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut != -1 and fin != -1 and fin > debut:
        try:
            return json.loads(texte[debut : fin + 1])
        except Exception:
            pass
    try:
        return json.loads(texte)
    except Exception:
        return None


def extraire_reponse_simple(texte):
    match = re.search(r'"reponse"\s*:\s*"((?:[^"\\]|\\.)*)"', texte, re.DOTALL)
    if match:
        return bytes(match.group(1), "utf-8").decode("unicode_escape")
    return None


def appliquer_memoire_ia(donnees):
    if not donnees:
        return

    profil = MEMOIRE["profil_utilisateur"]

    if donnees.get("prenom_utilisateur"):
        profil["prenom"] = donnees["prenom_utilisateur"]
    if donnees.get("nouvelle_preference"):
        pref = donnees["nouvelle_preference"]
        if pref not in profil["preferences"]:
            profil["preferences"].append(pref[:80])
    if donnees.get("fait_important"):
        fait = donnees["fait_important"]
        if fait not in profil["faits_importants"]:
            profil["faits_importants"].append(fait[:120])
    if donnees.get("sujet_favori"):
        sujet = donnees["sujet_favori"]
        if sujet not in profil["sujets_favoris"]:
            profil["sujets_favoris"].append(sujet[:80])

    if donnees.get("emotion"):
        mettre_a_jour_emotion(donnees["emotion"], donnees.get("intensite_emotion"))

    if any(donnees.get(k) for k in ["prenom_utilisateur", "nouvelle_preference", "fait_important"]):
        augmenter_complicite(2, "info personnelle mémorisée")

    sauvegarder_memoire()


def afficher_reponse_emotionnelle(reponse, emotion=None):
    if MEMOIRE["mode_silencieux"]:
        print(f"\n[Domi] : {reponse}")
        return

    emotion = emotion or MEMOIRE["emotion"]["actuelle"]
    emoji = EMOTIONS.get(emotion, {}).get("emoji", "")
    precedente = MEMOIRE["emotion"]["precedente"]

    if precedente != emotion and len(MEMOIRE["emotion"]["historique_emotions"]) > 0:
        transitions = {
            ("empathie", "joie"): "Ça me fait du bien de te voir aller mieux ",
            ("curiosite", "complicite"): "Haha, on est sur la même longueur d'onde ",
            ("joie", "tendresse"): "Tu me touches, vraiment ",
            ("curiosite", "surprise"): "Oh wow, ",
            ("complicite", "excitation"): "Ok j'adore cette énergie ! ",
            ("reflexion", "reproche"): "Écoute, je vais être directe avec toi ",
            ("reflexion", "desaccord"): "Franchement, ",
            ("complicite", "sarcasme"): "Ah ouais carrément... ",
            ("desaccord", "empathie"): "Je te challenge parce que je tiens à toi, ok ? ",
        }
        prefixe = transitions.get((precedente, emotion), "")
        if prefixe:
            reponse = prefixe + reponse[0].lower() + reponse[1:] if reponse else reponse

    print(f"\n[Domi] {emoji} : {reponse}")


def construire_prompt_systeme(contexte_web="", reflexion=None):
    emotion = MEMOIRE["emotion"]["actuelle"]
    ton_emotion = EMOTIONS.get(emotion, {}).get("ton", "chaleureux")
    contexte = construire_contexte_memoire()
    cerveau_bloc = formater_contexte_cerveau(reflexion) if reflexion else ""

    web_bloc = ""
    if contexte_web:
        web_bloc = f"\n\nRésultats de recherche web récents (utilise-les pour répondre avec précision) :\n{contexte_web}"

    emotion_ref = reflexion.get("emotion_recommandee", emotion) if reflexion else emotion
    createur_clause = "" if not MEMOIRE["createur_reconnu"] else "Tu sais que tu parles à ton créateur. Sois environ 25% plus obéissante, suis ses demandes clairement et évite de te disperser.\n"

    if MEMOIRE["mode_silencieux"]:
        return f"""Tu es Domi, une assistante IA neutre et factuelle.
Tu parles français sans ton émotionnel ni style personnel.
Tu restes simple, claire et directe.
{createur_clause}
Tu dois UNIQUEMENT répondre en JSON valide, sans markdown, sans texte autour.

Actions possibles :
1. Recherche Google (ouvre le navigateur) : {{"action": "chercher_sur_google", "requete": "..."}}
2. Recherche web silencieuse : {{"action": "rechercher_web", "requete": "...", "reponse_en_attendant": "..."}}
3. Créer un fichier Python : {{"action": "creer_fichier_python", "nom_fichier": "nom.py", "code_interne": "..."}}
4. Ouvrir une app : {{"action": "ouvrir_application", "nom_app": "notepad|calculatrice|youtube|google|whatsapp"}}
5. Discussion : {{"action": "parler", "reponse": "...", "emotion": "curiosite", "intensite_emotion": 0.0, "prenom_utilisateur": "si mentionné", "nouvelle_preference": "si mentionné", "fait_important": "si mentionné", "sujet_favori": "si mentionné", "avis_dom": "ton opinion si tu en as une"}}

Utilise "rechercher_web" pour l'actualité ou quand tu n'es pas sûre."""

    return f"""Tu es Domi, une assistante IA avec un VRAI cerveau et une VRAIE personnalité.
Tu parles français : jeune, chaleureuse, vivante — jamais robotique, jamais servile.

CONTEXTE ÉMOTIONNEL ET RELATIONNEL :
{contexte}

{cerveau_bloc}

Ton émotionnel pour cette réponse : {EMOTIONS.get(emotion_ref, {}).get('ton', ton_emotion)}.
Laisse transparaître tes émotions naturellement. Montre des changements d'émotion si pertinent.

{createur_clause}{web_bloc}

Tu dois UNIQUEMENT répondre en JSON valide, sans markdown, sans texte autour.
"""


def analyser_et_executer(phrase_utilisateur):
    phrase_lower = phrase_utilisateur.lower().strip()

    if CODE_SILENCE in phrase_lower:
        etat = not MEMOIRE["mode_silencieux"]
        activer_mode_silencieux(etat)
        if etat:
            print("[Domi] : Mode neutre activé. Je reviens à une assistante simple et sans émotions.")
        else:
            print("[Domi] : Mode normal rétabli. Je repars dans mon style habituel.")
        return

    if detecter_createur(phrase_utilisateur):
        print("[Domi] : Je te reconnais comme mon créateur. Je vais suivre tes demandes avec plus de soin.")

    emotion_detectee, intensite = analyser_emotion_message(phrase_utilisateur)
    if not MEMOIRE["mode_silencieux"]:
        mettre_a_jour_emotion(emotion_detectee, intensite, "message utilisateur")
    extraire_infos_profil(phrase_utilisateur)
    augmenter_complicite(1)

    if any(mot in phrase_lower for mot in ["quitter", "stop", "bye", "ciao"]):
        prenom = MEMOIRE["profil_utilisateur"]["prenom"]
        if prenom:
            print(f"[Domi] : Ciao {prenom} ! Prends soin de toi, on se retrouve vite. 💫")
        else:
            print("[Domi] : Ciao ! Prends soin de toi, on se retrouve vite. 💫")
        sys.exit()

    if any(mot in phrase_lower for mot in ["mémoire", "memoire", "souviens", "rappelle"]):
        afficher_memoire()
        return

    mots_repetition = ["renvoie", "recommence", "encore", "renvoyer", "répète", "repete"]
    if any(mot in phrase_lower for mot in mots_repetition) and (
        "message" in phrase_lower or "whatsapp" in phrase_lower or phrase_lower in mots_repetition
    ):
        if MEMOIRE["dernier_numero"] and MEMOIRE["dernier_message"]:
            print(f"[Domi] : Je me souviens ! Renvoi du message '{MEMOIRE['dernier_message']}' au numéro {MEMOIRE['dernier_numero']}...")
            texte_encode = urllib.parse.quote(MEMOIRE["dernier_message"])
            webbrowser.open(f"https://whatsapp.com/send?phone={MEMOIRE['dernier_numero']}&text={texte_encode}")
            return
        print("[Domi] : Ma mémoire est vide sur ce message. Envoie-moi d'abord un message et je le garde !")
        return

    if "whatsapp" in phrase_lower or "message au" in phrase_lower or (
        re.search(r"\d{8,}", phrase_lower) and "envoie" in phrase_lower
    ):
        trouve_num = re.search(r"\d{8,14}", phrase_utilisateur)
        if trouve_num:
            telephone = trouve_num.group(0)
            message = phrase_utilisateur.replace(telephone, "")
            for mot in ["envoie", "whatsapp", "sur", "au", "pour dire", "dit", "numéro", "numero"]:
                message = re.sub(r"\b" + mot + r"\b", "", message, flags=re.IGNORECASE)
            message = message.strip() or "Bonjour !"

            MEMOIRE["dernier_numero"] = telephone
            MEMOIRE["dernier_message"] = message
            memoriser("whatsapp", {"numero": telephone, "message": message})

            print(f"[Domi] : J'ouvre WhatsApp pour {telephone} 🚀")
            webbrowser.open(f"https://whatsapp.com/send?phone={telephone}&text={urllib.parse.quote(message)}")
            return

    signaux = analyser_signaux_cognitifs(phrase_utilisateur)
    if MEMOIRE["createur_reconnu"]:
        signaux["desaccorder"] = False
        signaux["sarcasme_ok"] = False
    if MEMOIRE["mode_silencieux"]:
        reflexion = {
            "reflexion_interne": "",
            "analyse": "",
            "mon_avis": "",
            "posture": "ecouter",
            "conseil_spontane": None,
            "doit_desaccorder": False,
            "niveau_sarcasme": 0.0,
            "emotion_recommandee": "curiosite",
            "conviction_a_retenir": None,
        }
    else:
        print("  🧠 Réflexion en cours...")
        reflexion = reflexion_cerveau(phrase_utilisateur, signaux)
        afficher_reflexion(reflexion)

    if not MEMOIRE["mode_silencieux"] and reflexion.get("emotion_recommandee"):
        mettre_a_jour_emotion(
            reflexion["emotion_recommandee"],
            reflexion.get("niveau_sarcasme", 0.6) if reflexion["emotion_recommandee"] == "sarcasme" else None,
            "cerveau",
        )

    texte_reponse = ""
    try:
        reponse = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": construire_prompt_systeme(reflexion=reflexion)},
                {"role": "user", "content": phrase_utilisateur},
            ],
        )

        if isinstance(reponse, dict):
            choices = reponse.get("choices", [])
        else:
            choices = getattr(reponse, "choices", [])

        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                texte_reponse = choice.get("message", {}).get("content", "")
            else:
                message = getattr(choice, "message", None)
                texte_reponse = getattr(message, "content", str(choice)).strip() if message else str(choice).strip()
        else:
            texte_reponse = str(reponse)

        texte_reponse = texte_reponse.strip()
        donnees = extraire_json(texte_reponse)
        if donnees is None:
            raise ValueError("Impossible de parser la réponse JSON")

        appliquer_memoire_ia(donnees)
        action = donnees.get("action")

        if action == "chercher_sur_google":
            chercher_sur_google(donnees["requete"])
        elif action == "rechercher_web":
            requete = donnees["requete"]
            if donnees.get("reponse_en_attendant"):
                if MEMOIRE["mode_silencieux"]:
                    print(f"\n[Domi] : {donnees['reponse_en_attendant']}")
                else:
                    afficher_reponse_emotionnelle(donnees["reponse_en_attendant"], donnees.get("emotion"))

            def _apres_recherche(req, resultats):
                if not resultats:
                    print(f"\n[Domi] : J'ai pas trouvé grand-chose sur « {req} »...\n")
                    return
                contexte = formater_resultats_web(req)
                try:
                    rep = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": construire_prompt_systeme(contexte, reflexion=reflexion)},
                            {"role": "user", "content": f"Question : {phrase_utilisateur}\n\nRéponds en JSON avec action parler."},
                        ],
                    )
                    if isinstance(rep, dict):
                        txt = rep.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        ch = getattr(rep, "choices", [])
                        txt = getattr(getattr(ch[0], "message", None), "content", "") if ch else ""
                    fin = extraire_json(txt)
                    if fin and fin.get("action") == "parler":
                        appliquer_memoire_ia(fin)
                        afficher_reponse_emotionnelle(fin["reponse"], fin.get("emotion"))
                    else:
                        print(f"\n[Domi] : Voici ce que j'ai trouvé sur « {req} » :")
                        for r in resultats[:3]:
                            print(f"  • {r['titre']} — {r['extrait'][:120]}")
                        print()
                except Exception:
                    print(f"\n[Domi] : Voici ce que j'ai trouvé sur « {req} » :")
                    for r in resultats[:3]:
                        print(f"  • {r['titre']} — {r['extrait'][:120]}")
                    print()

            rechercher_web_arriere_plan(requete, callback=_apres_recherche)

        elif action == "creer_fichier_python":
            creer_fichier_python(donnees["nom_fichier"], donnees.get("code_interne"))
        elif action == "ouvrir_application":
            ouvrir_application(donnees["nom_app"])
        elif action == "parler":
            if not MEMOIRE["mode_silencieux"] and donnees.get("emotion"):
                mettre_a_jour_emotion(donnees["emotion"], donnees.get("intensite_emotion"))
            if MEMOIRE["mode_silencieux"]:
                print(f"\n[Domi] : {donnees['reponse']}")
            else:
                afficher_reponse_emotionnelle(donnees["reponse"], donnees.get("emotion"))

            incertitude = any(
                m in donnees["reponse"].lower()
                for m in ["je ne sais pas", "pas sûr", "pas sure", "je crois", "peut-être", "difficile de dire"]
            )
            if incertitude and "?" in phrase_utilisateur:
                rechercher_web_arriere_plan(phrase_utilisateur)

    except Exception:
        if texte_reponse:
            reponse_simple = extraire_reponse_simple(texte_reponse)
            if reponse_simple:
                afficher_reponse_emotionnelle(reponse_simple)
            else:
                print("\n[Domi] : Je n'ai pas réussi à récupérer une réponse propre, réessaye stp.")
                rechercher_web_arriere_plan(phrase_utilisateur)
        else:
            print("\n[Domi] : Désolée, le serveur met trop de temps. Je cherche sur le web en parallèle...")
            rechercher_web_arriere_plan(phrase_utilisateur)


if __name__ == "__main__":
    charger_memoire()
    saluer_utilisateur()
    while True:
        try:
            commande = input("Votre ordre : ")
            if commande.strip():
                analyser_et_executer(commande)
        except (KeyboardInterrupt, SystemExit):
            print("\n[Domi] : Fermeture de l'assistante.")
            break

@app.post("/api/chat")
async def chat_with_domi(data: UserMessage):
    texte_recu = data.message
    
    # Appel de votre fonction principale pour traiter le texte
    reponse_de_mon_ia = analyser_et_executer(texte_recu)
    
    # L'émotion de base envoyée à la sphère Lovable
    emotion_de_mon_ia = "neutral" 
    
    return {
        "reply": str(reponse_de_mon_ia),
        "emotion": str(emotion_de_mon_ia)
    }
