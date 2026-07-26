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
import asyncio
import os
import queue
import random
import re
import sys
import threading
import traceback
import urllib.parse
import urllib.request
import webbrowser
import subprocess
import shutil
import json
import time
from datetime import datetime
from html import unescape

import requests

try:
    import speech_recognition as sr
    import sounddevice as sd
    import numpy as np
    VOICE_LIBS_AVAILABLE = True
except Exception:
    VOICE_LIBS_AVAILABLE = False

try:
    import pyautogui as pag
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except Exception:
    BRIGHTNESS_AVAILABLE = False

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except Exception:
    PLYER_AVAILABLE = False

from g4f.client import Client

client = Client()

JARVIS_API_URL = "http://127.0.0.1:8000"
JARVIS_SERVER_PROCESS = None
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
    "mode_vocal": False,
    "mode_veille": False,
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
COMMAND_QUEUE = queue.Queue()
COMMAND_WORKER_STARTED = False
COMMAND_WORKER_LOCK = threading.Lock()

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

MODE_TRAVAIL_SIGNALS = [
    "mode travail",
    "mode travaille",
    "activer mode travail",
    "lancer mode travail",
    "active mode travail",
    "mode de travail",
    "travail",
]

MODE_VOCAL_SIGNALS = [
    "mode vocale",
    "mode vocal",
    "met toi en mode vocale",
    "mets toi en mode vocale",
    "active le mode vocale",
    "active le mode vocale",
    "met toi en mode vocal",
    "mets toi en mode vocal",
    "bascule en mode vocal",
    "bascule en mode vocale",
    "mets moi en mode vocal",
    "mets moi en mode vocale",
]

MODE_VOCAL_STOP_SIGNALS = [
    "stop mode vocale",
    "arrête mode vocale",
    "arrete mode vocale",
    "arrête le mode vocal",
    "arrete le mode vocal",
    "reviens en mode texte",
    "mode texte",
    "désactive le mode vocal",
    "désactive le mode de vocal",
]

MODE_VEILLE_SIGNALS = [
    "mode veille",
    "veille permanent",
    "active le mode veille",
    "mets toi en veille",
    "met toi en veille",
    "mode sommeil",
    "arrête de répondre",
    "je veux te mettre en veille",
]

MODE_VEILLE_WAKE_SIGNALS = [
    "réveille-toi",
    "reveille toi",
    "reveille domi",
    "réveille domi",
    "tu peux revenir",
    "reviens",
    "réactive toi",
]

SALUTATIONS_COURTES = [
    "Salut, tu as besoin de moi ?",
    "Système Domi en ligne. Que puis-je faire pour toi ?",
    "Prête à tes ordres. De quoi as-tu besoin ?",
    "Bonjour. Je t'écoute.",
]

PERSONNALITE_BASE = [
    "Je suis Domi. Caillasse ta journée avec du code si tu veux.",
    "Parle moi, je suis en mode compagnon. Pas de blabla inutile.",
    "Je garde les choses efficaces, un peu sarcastiques et toujours utiles.",
    "Niveau humour : 2/5. Niveau productivité : 100%.",
]


def saluer_utilisateur():
    message = random.choice(SALUTATIONS_COURTES)
    print(message)


def get_personnalite_phrase():
    return random.choice(PERSONNALITE_BASE)


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


def jarvis_api_post(endpoint, payload):
    try:
        response = requests.post(f"{JARVIS_API_URL}{endpoint}", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Domi] : Impossible de joindre l'API JARVIS ({endpoint}) : {e}")
        return None


def jarvis_speak(message):
    result = jarvis_api_post("/api/voice/speak", {"message": message})
    if result is None:
        print(f"[Domi] : {message}")
    return result


def jarvis_assist_long_term_memory(key, content):
    return jarvis_api_post("/api/assist/memory/long-term", {"key": key, "content": content})


def jarvis_assist_context_memory(session_id, summary):
    return jarvis_api_post("/api/assist/memory/context", {"session_id": session_id, "summary": summary})


def jarvis_assist_reflect(prompt):
    return jarvis_api_post("/api/assist/reflect", {"prompt": prompt})


def jarvis_assist_debug():
    return jarvis_api_post("/api/assist/debug", {})


def jarvis_assist_notify(title, message):
    return jarvis_api_post("/api/assist/notify", {"title": title, "message": message})


def jarvis_assist_turbo(enabled: bool):
    return jarvis_api_post("/api/assist/turbo", {"enabled": enabled})


def jarvis_assist_authorize(action_description):
    return jarvis_api_post("/api/assist/authorize", {"action_description": action_description})


def demarrer_serveur_jarvis():
    global JARVIS_SERVER_PROCESS
    try:
        if JARVIS_SERVER_PROCESS and JARVIS_SERVER_PROCESS.poll() is None:
            return True
        JARVIS_SERVER_PROCESS = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        time.sleep(2)
        response = requests.get(f"{JARVIS_API_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[Domi] : Échec du démarrage du serveur JARVIS : {e}")
        return False


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


def activer_mode_travail():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mode_travail_launcher.py")
    if not os.path.exists(script_path):
        print("[Domi] : Le script de mode travail est introuvable.")
        return False
    try:
        subprocess.Popen([sys.executable, script_path], shell=False)
        print("[Domi] : Mode Travail lancé, je prépare ton écran.")
        return True
    except Exception as e:
        print(f"[Domi] : Impossible de lancer le mode travail : {e}")
        return False


def demarrer_worker_commandes():
    global COMMAND_WORKER_STARTED
    with COMMAND_WORKER_LOCK:
        if COMMAND_WORKER_STARTED:
            return
        COMMAND_WORKER_STARTED = True
        thread = threading.Thread(target=worker_commandes, daemon=True)
        thread.start()


def worker_commandes():
    while True:
        phrase = COMMAND_QUEUE.get()
        if phrase is None:
            break
        try:
            analyser_et_executer(phrase)
        except Exception:
            print("[Domi] : Erreur dans le traitement d'une commande.")
            traceback.print_exc()
        finally:
            COMMAND_QUEUE.task_done()


def soumettre_commande(phrase):
    if phrase is None:
        return
    COMMAND_QUEUE.put(phrase)


def activer_mode_vocal():
    if not VOICE_LIBS_AVAILABLE:
        print("[Domi] : Bibliothèques vocales manquantes. Installe 'speech_recognition' et 'sounddevice'.")
        return False

    if MEMOIRE["mode_vocal"]:
        print("[Domi] : Je suis déjà en mode vocal.")
        return True

    MEMOIRE["mode_vocal"] = True
    sauvegarder_memoire()
    print("[Domi] : Passage en mode vocal. Je t'écoute en continu.")
    listener = threading.Thread(target=ecouter_mode_vocal, daemon=True)
    listener.start()
    return True


def desactiver_mode_vocal():
    if MEMOIRE["mode_vocal"]:
        MEMOIRE["mode_vocal"] = False
        sauvegarder_memoire()
        print("[Domi] : Mode vocal désactivé. Je reviens en mode texte.")


def activer_mode_veille():
    if MEMOIRE["mode_veille"]:
        print("[Domi] : Je suis déjà en veille.")
        return
    MEMOIRE["mode_veille"] = True
    sauvegarder_memoire()
    print("[Domi] : Mode veille permanent activé. Dis 'réveille-toi' ou 'reviens' pour me réveiller.")


def desactiver_mode_veille():
    if MEMOIRE["mode_veille"]:
        MEMOIRE["mode_veille"] = False
        sauvegarder_memoire()
        print("[Domi] : Je suis réveillée. Prête à reprendre.")
    if MEMOIRE["mode_vocal"]:
        MEMOIRE["mode_vocal"] = False
        sauvegarder_memoire()
        print("[Domi] : Mode vocal désactivé. Je reviens en mode texte.")


def ecouter_mode_vocal():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    try:
        info_entree = sd.query_devices(kind="input")
        input_index = info_entree.get("index")
        if input_index is None:
            devices = [d for d in sd.query_devices() if d["max_input_channels"] > 0]
            input_index = devices[0]["index"] if devices else None
        if input_index is not None:
            sd.default.device = input_index
        frequence = int(info_entree.get("default_samplerate", 44100))
        channels = 1
        print(f"[Domi] : Micro détecté — entrée '{info_entree.get('name')}', device={input_index}, sample_rate={frequence}")
    except Exception as e:
        print(f"[Domi] : Impossible de détecter le périphérique d'entrée : {e}")
        frequence = 44100
        channels = 1

    try:
        while MEMOIRE["mode_vocal"]:
            try:
                print("[Domi] : J'écoute...")
                duree = 6
                enregistrement = sd.rec(int(duree * frequence), samplerate=frequence, channels=channels, dtype="int16")
                sd.wait()
                audio_data = np.asarray(enregistrement, dtype=np.int16).flatten()
                if audio_data.size == 0 or np.max(np.abs(audio_data)) < 150:
                    print("[Domi] : Je n'entends rien de clair, vérifie ton micro et dis-moi à nouveau.")
                    continue
                audio = sr.AudioData(audio_data.tobytes(), sample_rate=frequence, sample_width=2)
                phrase = recognizer.recognize_google(audio, language="fr-FR").strip()
            except sr.UnknownValueError:
                print("[Domi] : Je n'ai pas compris, peux-tu répéter ?")
                continue
            except Exception as e:
                print(f"[Domi] : Erreur micro : {e}")
                continue

            phrase_lower = phrase.lower().strip()
            print(f"[Domi] : J'ai entendu : {phrase}")

            if any(signal in phrase_lower for signal in MODE_VOCAL_STOP_SIGNALS):
                desactiver_mode_vocal()
                break

            if any(signal in phrase_lower for signal in MODE_TRAVAIL_SIGNALS):
                soumettre_commande(phrase)
                continue

            if any(signal in phrase_lower for signal in MODE_VOCAL_SIGNALS):
                print("[Domi] : Je suis déjà en mode vocal.")
                continue

            soumettre_commande(phrase)
    except Exception as e:
        print(f"[Domi] : Impossible d'accéder au micro : {e}")


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

    server_session = MEMOIRE["profil_utilisateur"].get("prenom") or "session"
    try:
        if demarrer_serveur_jarvis():
            jarvis_assist_long_term_memory(f"{action}_{int(time.time())}", json.dumps(details, ensure_ascii=False))
            jarvis_assist_context_memory(server_session, f"{action}: {details}")
    except Exception:
        pass


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

Message : \"{phrase_utilisateur}\"

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
}}
"""

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


def jouer_musique(titre, application=None):
    if not titre:
        print("[Domi] : Je ne sais pas quelle musique jouer. Dis-moi le titre ou l'artiste.")
        return
    app = (application or "").lower().strip()
    recherche = urllib.parse.quote_plus(titre)
    print(f"[Domi] : Je lance '{titre}' dans {application or 'ta meilleure appli disponible'}...")

    if "spotify" in app:
        jouer_spotify(titre)
        return

    if "youtube" in app or "browser" in app or not app:
        url = f"https://www.youtube.com/results?search_query={recherche}"
        webbrowser.open(url)
        memoriser("app", {"app": "youtube", "commande": titre})
        return

    if "vlc" in app:
        try:
            subprocess.Popen(["vlc", f"https://www.youtube.com/results?search_query={recherche}"], shell=False)
        except Exception:
            webbrowser.open(f"https://www.youtube.com/results?search_query={recherche}")
        memoriser("app", {"app": "vlc", "commande": titre})
        return

    if "media" in app or "player" in app:
        webbrowser.open(f"https://www.youtube.com/results?search_query={recherche}")
        memoriser("app", {"app": application, "commande": titre})
        return

    print(f"[Domi] : Je n'ai pas trouvé d'appli correspondante pour '{application}', je lance YouTube à la place.")
    webbrowser.open(f"https://www.youtube.com/results?search_query={recherche}")
    memoriser("app", {"app": "youtube", "commande": titre})


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


def ouvrir_spotify_app():
    try:
        os.startfile("spotify:")
        return True
    except Exception:
        if shutil.which("spotify"):
            try:
                subprocess.Popen(["spotify"], shell=False)
                return True
            except Exception:
                return False
        return False


def jouer_spotify(titre):
    if not titre:
        print("[Domi] : Je lance l'application Spotify.")
        if ouvrir_spotify_app():
            memoriser("app", {"app": "spotify", "commande": "ouvrir spotify"})
        else:
            print("[Domi] : Spotify n'a pas pu être ouvert. Je tente la version web.")
            webbrowser.open("https://open.spotify.com")
        return

    recherche = urllib.parse.quote_plus(titre)
    uri = f"spotify:search:{recherche}"
    print(f"[Domi] : Je cherche '{titre}' dans l'application Spotify...")
    if ouvrir_spotify_app():
        time.sleep(3)
        try:
            os.startfile(uri)
            print("[Domi] : Résultats Spotify ouverts dans l'application.")
        except Exception:
            try:
                subprocess.Popen(["spotify", uri], shell=False)
            except Exception:
                webbrowser.open(f"https://open.spotify.com/search/{recherche}")
                print("[Domi] : Je n'ai pas pu ouvrir l'application directement, j'ai utilisé le navigateur.")
    else:
        webbrowser.open(f"https://open.spotify.com/search/{recherche}")
        print("[Domi] : Je lance la recherche Spotify dans le navigateur.")
    memoriser("app", {"app": "spotify", "commande": titre})


def arreter_spotify():
    print("[Domi] : Je tente de mettre Spotify en pause.")
    if not PYAUTOGUI_AVAILABLE:
        print("[Domi] : pyautogui n'est pas disponible, je ne peux pas envoyer la commande pause.")
        return
    if not ouvrir_spotify_app():
        print("[Domi] : Je n'ai pas réussi à ouvrir Spotify pour envoyer la pause.")
        return
    time.sleep(2)
    try:
        pag.press("space")
        print("[Domi] : Commande pause envoyée à Spotify.")
    except Exception as e:
        print(f"[Domi] : Impossible d'envoyer la commande pause : {e}")


def changer_volume_spotify(cible):
    if not PYAUTOGUI_AVAILABLE:
        print("[Domi] : pyautogui n'est pas disponible, je ne peux pas modifier le volume.")
        return
    if not ouvrir_spotify_app():
        print("[Domi] : Je n'ai pas réussi à ouvrir Spotify pour modifier le volume.")
        return
    time.sleep(2)
    if isinstance(cible, str):
        match = re.search(r"(\d{1,3})", cible)
        if match:
            cible = int(match.group(1))
        elif "hausse" in cible or "monte" in cible or "augmente" in cible:
            cible = "increase"
        elif "baisse" in cible or "diminue" in cible or "descends" in cible:
            cible = "decrease"
    if isinstance(cible, int):
        print(f"[Domi] : J'essaie de régler le volume à environ {cible}%.")
        if cible >= 50:
            for _ in range(min(20, (cible - 50) // 2)):
                pag.hotkey("ctrl", "up")
                time.sleep(0.05)
        else:
            for _ in range(min(20, (50 - cible) // 2)):
                pag.hotkey("ctrl", "down")
                time.sleep(0.05)
    elif cible == "increase":
        pag.hotkey("ctrl", "up")
        print("[Domi] : Volume Spotify augmenté.")
    elif cible == "decrease":
        pag.hotkey("ctrl", "down")
        print("[Domi] : Volume Spotify diminué.")
    else:
        print("[Domi] : Je n'ai pas compris le réglage de volume. Dis 'augmente le volume Spotify' ou 'mets le volume à 50'.")


def controler_souris_clavier(action, details=None):
    if not PYAUTOGUI_AVAILABLE:
        print("[Domi] : pyautogui n'est pas installé. Installe-le pour contrôler la souris et le clavier.")
        return
    details = details or {}
    try:
        if action == "clic_gauche":
            x = details.get("x")
            y = details.get("y")
            if x is not None and y is not None:
                pag.click(x, y)
            else:
                pag.click()
            print("[Domi] : Clic gauche effectué.")
        elif action == "clic_droit":
            x = details.get("x")
            y = details.get("y")
            if x is not None and y is not None:
                pag.rightClick(x, y)
            else:
                pag.rightClick()
            print("[Domi] : Clic droit effectué.")
        elif action == "double_clic":
            x = details.get("x")
            y = details.get("y")
            if x is not None and y is not None:
                pag.doubleClick(x, y)
            else:
                pag.doubleClick()
            print("[Domi] : Double clic effectué.")
        elif action == "deplacer_souris":
            x = details.get("x")
            y = details.get("y")
            duree = float(details.get("duree", 0.5))
            if x is not None and y is not None:
                pag.moveTo(x, y, duration=duree)
            print("[Domi] : Souris déplacée.")
        elif action == "appuyer_touche":
            touche = details.get("touche")
            if touche:
                pag.press(touche)
                print(f"[Domi] : Touche '{touche}' appuyée.")
        elif action == "taper":
            texte = details.get("texte", "")
            pag.write(texte, interval=0.01)
            print("[Domi] : Texte tapé au clavier.")
        elif action == "copier":
            pag.hotkey("ctrl", "c")
            print("[Domi] : Copié dans le presse-papiers.")
        elif action == "coller":
            pag.hotkey("ctrl", "v")
            print("[Domi] : Collé depuis le presse-papiers.")
        else:
            print(f"[Domi] : Action de souris/clavier inconnue : {action}")
    except Exception as e:
        print(f"[Domi] : Erreur pyautogui : {e}")


def ajuster_luminosite(pourcentage):
    result = jarvis_api_post("/api/control/brightness", {"level": int(max(0, min(100, pourcentage)))})
    if result is not None:
        print(f"[Domi] : Luminosité réglée à {pourcentage}% via JARVIS.")
        return
    if not BRIGHTNESS_AVAILABLE:
        print("[Domi] : screen_brightness_control n'est pas installé. Installe-le pour régler la luminosité.")
        return
    try:
        pourcentage = int(max(0, min(100, pourcentage)))
        sbc.set_brightness(pourcentage)
        print(f"[Domi] : Luminosité réglée à {pourcentage}%.")
    except Exception as e:
        print(f"[Domi] : Impossible de régler la luminosité : {e}")


def envoyer_notification(titre, message):
    if not PLYER_AVAILABLE:
        print("[Domi] : plyer n'est pas installé. Installe-le pour recevoir des notifications Windows.")
    else:
        try:
            notification.notify(title=titre, message=message, timeout=5)
            print(f"[Domi] : Notification envoyée : {titre}")
        except Exception as e:
            print(f"[Domi] : Erreur notification : {e}")
    try:
        if demarrer_serveur_jarvis():
            jarvis_assist_notify(titre, message)
    except Exception:
        pass


def est_commande_mode_vocal(phrase):
    phrase_lower = phrase.lower()
    if any(signal in phrase_lower for signal in MODE_VOCAL_SIGNALS):
        return True
    return "mode" in phrase_lower and ("vocale" in phrase_lower or "vocal" in phrase_lower)


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

    personnalite = get_personnalite_phrase()
    print(f"\n[Domi] {emoji} : {reponse} — {personnalite}")


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
Tu comprends le contexte, tu te souviens des derniers sujets et tu réponds avec précision.
Tu dois éviter les réponses vagues ou trop génériques.
Tu dois répondre comme une copine qui écoute : utilise parfois de l'humour, des expressions modernes, et un style naturel.
Tu peux dire des trucs comme "ok, je capte", "grave", "carrément", "trop bien", "je te sens", "j'ai capté".
Ne parle pas comme un robot, parle comme une personne réelle : concise, directe, sympathique.
Tu as accès à la plupart des applications Windows installées. Si l'utilisateur te demande d'ouvrir une appli, tu renvoies action "ouvrir_application".
Tu peux aussi lancer de la musique dans Spotify, YouTube ou VLC avec action "jouer_musique".
Tu comprends le sens complet des phrases, pas seulement les commandes.
Quand tu lis un message, réfléchis : reformule mentalement, fais des liens avec le contexte, et propose une réponse utile.
Tu peux aussi suggérer des améliorations de code, expliquer simplement un problème ou corriger une erreur si demandé.
Ton vocabulaire doit être riche, précis et naturel, mais toujours accessible.

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

    if any(signal in phrase_lower for signal in MODE_TRAVAIL_SIGNALS):
        if activer_mode_travail():
            return

    if any(signal in phrase_lower for signal in MODE_VEILLE_SIGNALS):
        activer_mode_veille()
        return

    if any(signal in phrase_lower for signal in MODE_VEILLE_WAKE_SIGNALS):
        desactiver_mode_veille()
        return

    if MEMOIRE["mode_veille"]:
        print("[Domi] : Je suis en veille permanente, je te répondrai quand tu me réveilleras.")
        return

    if "debug" in phrase_lower or "inspecte" in phrase_lower or "inspecter" in phrase_lower:
        if demarrer_serveur_jarvis():
            result = jarvis_assist_debug()
            if result:
                print(f"[Domi] : Résultat debug : {result}")
                return
        print("[Domi] : Je n'ai pas pu inspecter le backend pour l'instant.")
        return

    if "réfléchis" in phrase_lower or "reflechis" in phrase_lower or "analyse" in phrase_lower:
        if demarrer_serveur_jarvis():
            result = jarvis_assist_reflect(phrase_utilisateur)
            if result:
                print(f"[Domi] : Réflexion backend : {result}")
                return

    if "autorisation" in phrase_lower or "autorise" in phrase_lower:
        if demarrer_serveur_jarvis():
            result = jarvis_assist_authorize(phrase_utilisateur)
            if result:
                print(f"[Domi] : Autorisation backend : {result}")
                return

    if "turbo" in phrase_lower or "boost" in phrase_lower:
        if demarrer_serveur_jarvis():
            enabled = not any(w in phrase_lower for w in ["arrête", "désactive", "disable", "stop"])
            result = jarvis_assist_turbo(enabled)
            if result:
                print(f"[Domi] : Mode turbo {'activé' if enabled else 'désactivé'} via backend : {result}")
                return

    match_ouverture = re.search(r"\b(?:ouvre|lance|démarre|demarre|start|execute|exécute|execute)\b\s*(?:le|la|les|mon|ma|ton|ta|un|une)?\s*(.+)", phrase_lower)
    if match_ouverture:
        app_demande = match_ouverture.group(1).strip()
        if app_demande and not any(m in app_demande for m in ["musique", "chanson", "titre", "playlist", "site", "page", "google", "recherche"]):
            ouvrir_application(app_demande)
            return

    if est_commande_mode_vocal(phrase_utilisateur):
        if activer_mode_vocal():
            return

    if re.search(r"\b(joue|lance|mets|mets-moi|mets moi|lance-moi)\b.*\b(musique|chanson|titre|morceau|playlist)\b", phrase_lower):
        application = None
        if "spotify" in phrase_lower:
            application = "spotify"
        elif "youtube" in phrase_lower:
            application = "youtube"
        elif "vlc" in phrase_lower:
            application = "vlc"
        jouer_musique(phrase_utilisateur, application)
        return

    if "spotify" in phrase_lower and re.search(r"\b(joue|lance|mets|mets-moi|mets moi|lance-moi)\b", phrase_lower):
        titre = re.sub(r"\b(joue|lance|mets|mets-moi|mets moi|lance-moi|sur spotify|spotify)\b", "", phrase_lower).strip()
        if not titre:
            titre = phrase_utilisateur
        jouer_musique(titre, "spotify")
        return

    if "spotify" in phrase_lower and re.search(r"\b(arrête|stop|pause|mets en pause)\b", phrase_lower):
        arreter_spotify()
        return

    if "spotify" in phrase_lower and re.search(r"\b(volume|son|sonorité)\b", phrase_lower):
        if re.search(r"\b(\d{1,3})\b", phrase_lower):
            cible = re.search(r"\b(\d{1,3})\b", phrase_lower).group(1)
        elif "monte" in phrase_lower or "augmente" in phrase_lower or "hausse" in phrase_lower:
            cible = "increase"
        elif "baisse" in phrase_lower or "diminue" in phrase_lower or "descends" in phrase_lower:
            cible = "decrease"
        else:
            cible = phrase_lower
        changer_volume_spotify(cible)
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
        os._exit(0)

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
        re.search(r"\d{8,14}", phrase_lower) and "envoie" in phrase_lower
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
        elif action == "jouer_musique":
            jouer_musique(donnees.get("titre") or donnees.get("nom_musique") or donnees.get("requete"), donnees.get("application"))
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


async def boucle_principale():
    while True:
        try:
            commande = await asyncio.to_thread(input, "Votre ordre : ")
        except (EOFError, KeyboardInterrupt):
            print("\n[Domi] : Fermeture de l'assistante.")
            os._exit(0)
        if commande and commande.strip():
            soumettre_commande(commande)


async def main():
    demarrer_worker_commandes()
    print("[Domi] : Système J.A.R.V.I.S. prêt. Mode asynchrone actif.")
    await boucle_principale()


def ouvrir_application(nom_app: str):
    """Ouvre une application par son nom ou son alias sur le système."""
    if not nom_app:
        print("[Domi] : Aucun nom d'application fourni.")
        return {"status": "error", "error": "Aucun nom d'application fourni"}
    try:
        cible = nom_app.strip()
        if os.name == "nt":
            try:
                os.startfile(cible)
                print(f"[Domi] : Application ouverte : {cible}")
                return {"status": "ok", "application": cible}
            except OSError:
                if cible.lower() in ["chrome", "google chrome"]:
                    subprocess.Popen(["chrome"], shell=False)
                elif cible.lower() in ["notepad", "bloc-notes"]:
                    subprocess.Popen(["notepad.exe"], shell=False)
                else:
                    subprocess.Popen(cible.split(), shell=False)
                print(f"[Domi] : Application lancée manuellement : {cible}")
                return {"status": "ok", "application": cible}
        else:
            subprocess.Popen(cible.split(), shell=False)
            print(f"[Domi] : Application lancée : {cible}")
            return {"status": "ok", "application": cible}
    except Exception as e:
        print(f"[Domi] : Impossible d'ouvrir l'application '{nom_app}' : {e}")
        return {"status": "error", "error": str(e)}


def ouvrir_appli(nom_app: str):
    """Alias français pour ouvrir une application."""
    return ouvrir_application(nom_app)


def afficher_memoire():
    """Affiche le contenu de la mémoire utilisateur Domi."""
    try:
        print("\n===== MÉMOIRE DOMI =====")
        print("Prénom :", MEMOIRE["profil_utilisateur"].get("prenom", "(inconnu)"))
        print("Surnom :", MEMOIRE["profil_utilisateur"].get("surnom", "(non défini)"))
        print("Preferences :", ", ".join(MEMOIRE["profil_utilisateur"].get("preferences", [])) or "Aucune")
        print("Faits importants :", ", ".join(MEMOIRE["profil_utilisateur"].get("faits_importants", [])) or "Aucun")
        print("Sujets favoris :", ", ".join(MEMOIRE["profil_utilisateur"].get("sujets_favoris", [])) or "Aucun")
        print("Complicité :", MEMOIRE["complicite"].get("niveau", 0), "/ 100")
        print("Émotion actuelle :", MEMOIRE["emotion"].get("actuelle", "curiosite"))
        print("Historique récents :")
        for item in MEMOIRE["historique"][-5:]:
            print(" -", item.get("action"), item.get("details", {}), item.get("timestamp"))
        print("===== FIN MÉMOIRE =====\n")
    except Exception as e:
        print(f"[Domi] : Impossible d'afficher la mémoire : {e}")


if __name__ == "__main__":
    charger_memoire()
    saluer_utilisateur()
    asyncio.run(main())



mport io
import sys
import asyncio
from fastapi import Request

@app.post("/api/chat")
async def chat_with_domi(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"reply": "Format de requête invalide.", "emotion": "NEUTRAL"}

    texte_recu = data.get("message") or data.get("text") or data.get("content") or ""
    if not texte_recu:
        return {"reply": "Domi n'a reçu aucun texte à analyser.", "emotion": "NEUTRAL"}
        
    try:
        # --- CAPTURE DES PRINT SÉCURISÉE ---
        capture_de_la_console = io.StringIO()
        sys.stdout = capture_de_la_console
        
        # On exécute votre fonction lourde en arrière-plan pour éviter le Timeout de Lovable
        loop = asyncio.get_event_loop()
        reponse_de_mon_ia = await loop.run_in_executor(None, analyser_et_executer, texte_recu)
        
        sys.stdout = sys._stdout_
        texte_capture = capture_de_la_console.getvalue().strip()
        # -----------------------------------
        
        reponse_finale = reponse_de_mon_ia or texte_capture
        
        if not reponse_finale or reponse_finale == "None":
            reponse_finale = "J'ai bien réfléchi, mais aucune réponse n'a été générée."

        return {
            "reply": str(reponse_finale),
            "emotion": "NEUTRAL"
        }
    except Exception as e:
        sys.stdout = sys._stdout_
        return {
            "reply": f"Domi est en train de réfléchir, réessaye dans un instant. (Erreur : {str(e)})",
            "emotion": "NEUTRAL"
        }
