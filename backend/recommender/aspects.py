"""LES ASPECTS SIGNÉS — ce que tu as AIMÉ et DÉTESTÉ, axe par axe.

LA CORRECTION DE MARTIN (26/07), qui refonde le moteur : « la plateforme n'a pas une
valeur d'aimé ou pas aimé, mais de rapprocher un film d'un autre par ce que j'aime DANS
chacun, et ce que je déteste. » Autrement dit : la valence globale (adoré/détesté) est un
plancher ; la vraie matière, c'est le goût PAR ASPECT.

POURQUOI CE MODULE, ET PAS UN EMBEDDING. Mesuré le 26/07 sur ses 8 ressentis :

    Anatomie vs Tenet (ses 2 détestés, même reproche : alambiqué + mou)
      synopsis (le moteur actuel)   0,506   -> les croit à peine liés
      texte entier encodé MiniLM    0,417   -> le critère est NOYÉ dans le récit du film
      aspects isolés encodés MiniLM 0,258   -> MiniLM ne sait pas relier « alambiqué » et « mou »
      AXES NOMMÉS ET SIGNÉS         0,707   -> ils partagent structure:-, ça marche

Le texte libre ne suffit pas : le critère (« clarté », « mou ») est dilué dans le contenu
du film (le chien, le procès, les acteurs), et MiniLM est trop grossier pour l'isoler. La
seule représentation qui rende justice au modèle de Martin est un jeu d'AXES NOMMÉS, chacun
porté à un SIGNE. « alambiqué » -> structure:-. « mou » -> rythme:-. Deux films se relient
alors parce qu'ils partagent un axe signé, pas par une proximité de mots floue.

Les axes sont ceux de axes.py (déjà nommés en français) ; ce module leur ajoute ce qui
manquait : le signe, extrait du texte par un LLM. C'est le remplaçant annoncé du lexique
de valence (MANIFESTE §7), poussé un cran plus loin — signé, et par aspect.

Sans clé API, tout dégrade proprement (comme relecture.py) : pas d'extraction, rien de
cassé. La valence globale et le profil actuels continuent de fonctionner.

ÉTAT AU 26/07 : le MODÈLE est prouvé (étiquetage à la main, cf. le commit). L'EXTRACTION
LLM est écrite mais PAS ENCORE VÉRIFIÉE contre le vrai modèle — il n'y a pas de clé dans cet
environnement. Première chose à faire quand la clé sera là : lancer extraire() sur les 8
ressentis et comparer aux étiquettes manuelles avant de brancher quoi que ce soit dans le
moteur.
"""
import hashlib
import json
import os

from .axes import AXES

MODELE = "claude-opus-4-8"

# Le cache : une extraction par TEXTE (clé = hash), pour ne jamais rappeler le LLM deux
# fois sur le même ressenti. Recalculable et jetable — c'est une VUE, comme la valence.
_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                           "aspects_cache.json")

_LIBELLES = {cle: ax["libelle"] for cle, ax in AXES.items()}

SYSTEME = """Tu analyses une note personnelle écrite par quelqu'un après avoir vu un film.
Cette note sert à un moteur qui apprend son goût — non pas « a-t-il aimé le film », mais
CE QU'IL A AIMÉ OU DÉTESTÉ DEDANS, aspect par aspect.

On te donne une liste d'AXES nommés. Pour CHAQUE axe que la personne évoque explicitement,
dis si elle en parle POSITIVEMENT (+1) ou NÉGATIVEMENT (-1), et cite le bout de phrase qui
le montre. N'invente RIEN : si un axe n'est pas clairement évoqué, ne le mets pas.

Règles strictes :
- polarité = le JUGEMENT de la personne sur cet aspect DANS CE FILM, pas le ton général.
  « le montage éclaté est réussi » -> structure +1. « alambiqué pour rien » -> structure -1.
  « c'est mou, long » -> rythme -1. « les couleurs sont splendides » -> image +1.
- un même texte peut être +1 sur un axe et -1 sur un autre (aimé la lumière, détesté le son).
- ne juge pas la qualité de l'écriture, ne reformule pas, ne complète pas.
- la citation est un extrait EXACT du texte, courte.

Réponds uniquement avec le JSON demandé."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "aspects": {
            "type": "array",
            "description": "Un élément par axe RÉELLEMENT évoqué. Vide si aucun.",
            "items": {
                "type": "object",
                "properties": {
                    "axe": {"type": "string", "enum": list(AXES.keys())},
                    "polarite": {"type": "integer", "enum": [-1, 1]},
                    "citation": {"type": "string"},
                },
                "required": ["axe", "polarite", "citation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["aspects"],
    "additionalProperties": False,
}


def disponible():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _cache():
    try:
        return json.load(open(_CACHE_PATH, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _cle(texte):
    return hashlib.sha1((texte or "").strip().encode("utf-8")).hexdigest()[:16]


def extraire(texte, forcer=False):
    """texte -> [{axe, polarite, citation}], ou None si indisponible.

    Mis en cache par hash de texte. Ne lève jamais : c'est un enrichissement, pas la
    serrure.
    """
    texte = (texte or "").strip()
    if not texte:
        return None
    cache = _cache()
    k = _cle(texte)
    if not forcer and k in cache:
        return cache[k]
    if not disponible():
        return None
    try:
        import anthropic
    except ImportError:
        return None

    axes_desc = "\n".join(f"- {cle} ({lib})" for cle, lib in _LIBELLES.items())
    prompt = f"AXES :\n{axes_desc}\n\nNOTE :\n{texte}"
    try:
        client = anthropic.Anthropic()
        rep = client.messages.create(
            model=MODELE, max_tokens=2000, system=SYSTEME,
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        if rep.stop_reason == "refusal":
            return None
        brut = next((b.text for b in rep.content if b.type == "text"), None)
        aspects = json.loads(brut)["aspects"] if brut else None
    except Exception:
        return None
    if aspects is None:
        return None
    cache[k] = aspects
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    json.dump(cache, open(_CACHE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return aspects


def profil_axes(aretes):
    """TON GOÛT PAR AXE : moyenne signée des aspects sur tes ressentis.

    Renvoie {axe: valeur dans [-1, 1]} pour les axes réellement évoqués, plus le nombre
    de ressentis exploités. C'est la brique que l'oracle utilisera pour relier les films
    par ce que tu aimes/détestes DEDANS — quand l'extraction aura été vérifiée.

    Fonctionne sans clé : lit le cache. Tant que rien n'est extrait, renvoie un profil
    vide, honnêtement — jamais un profil inventé.
    """
    somme = {cle: 0.0 for cle in AXES}
    compte = {cle: 0 for cle in AXES}
    n = 0
    for a in aretes or []:
        asp = extraire(a.get("texte"))          # depuis le cache si pas de clé
        if not asp:
            continue
        n += 1
        for item in asp:
            ax = item.get("axe")
            if ax in somme:
                somme[ax] += item.get("polarite", 0)
                compte[ax] += 1
    profil = {ax: round(somme[ax] / compte[ax], 3) for ax in AXES if compte[ax]}
    return {"axes": profil, "ressentis_analyses": n,
            "assez": n >= 5}          # sous 5 ressentis, le profil d'axes est anecdotique
