"""RELECTURE — corriger les fautes d'un ressenti SANS lui voler sa voix.

Le piège, et c'est le point central de ce module : la page « mon profil » affiche
« les mots que tu emploies » — c'est la matière qui te distingue. Si un LLM réécrit ton
texte, ce vocabulaire devient LE SIEN. Ton portrait finirait par décrire un modèle de
langue, pas toi. Une relecture mal cadrée détruirait donc exactement ce que MORDU
cherche à capter.

D'où l'architecture, identique à celle de la valence (MANIFESTE §4) :

    texte  = la donnée BRUTE, jamais modifiée, append-only
    corrige = une VUE, stockée à côté, recalculable et jetable

Et l'usage est séparé :
    - le texte CORRIGÉ sert à la lecture et à la valence (moins de fautes = le lexique
      reconnaît mieux les mots) ;
    - le texte BRUT continue seul d'alimenter ton vocabulaire dans le profil.

Sans clé API, tout dégrade proprement : on ne corrige rien, on ne casse rien.
"""
import json
import os

MODELE = "claude-opus-4-8"

# Ce prompt est un organe critique : c'est lui qui empêche la relecture de déborder
# sur le style. Il est volontairement plus long sur les INTERDITS que sur la consigne.
SYSTEME = """Tu corriges des notes personnelles écrites par quelqu'un après avoir vu un
film. Ces notes ne sont lues par personne d'autre : elles servent à un moteur de
recommandation qui apprend le goût de leur auteur.

TA SEULE MISSION : corriger l'orthographe, les accords, la ponctuation manifestement
fautive, et reformuler UNIQUEMENT les passages devenus incompréhensibles (mot manquant,
phrase interrompue, syntaxe cassée).

CE QUE TU NE DOIS JAMAIS FAIRE — c'est plus important que la correction elle-même :
- ne change AUCUN mot correctement orthographié pour un synonyme, même « meilleur » ;
- ne rends pas le texte plus soutenu, plus littéraire, plus fluide ou mieux tourné ;
- garde le registre familier, l'argot, les tics de langage, les abréviations assumées ;
- garde les phrases longues, les répétitions, les digressions, les jugements abrupts ;
- n'ajoute rien : ni transition, ni nuance, ni précision, ni conclusion ;
- ne supprime rien qui ait du sens ;
- ne corrige pas un avis « mal argumenté » — ce n'est pas une faute.

Le vocabulaire de cette personne EST la donnée qu'on veut préserver. Si tu hésites
entre corriger et laisser, LAISSE.

Réponds uniquement avec le JSON demandé."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "corrige": {"type": "string",
                    "description": "Le texte corrigé, au plus près de l'original."},
        "changements": {
            "type": "array",
            "description": "Une entrée par correction réellement faite. Vide si rien.",
            "items": {
                "type": "object",
                "properties": {
                    "avant": {"type": "string"},
                    "apres": {"type": "string"},
                    "type": {"type": "string",
                             "enum": ["orthographe", "accord", "ponctuation", "syntaxe"]},
                },
                "required": ["avant", "apres", "type"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["corrige", "changements"],
    "additionalProperties": False,
}


def disponible():
    """Une clé est-elle configurée ? Sans elle, la relecture est simplement absente."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def relire(texte):
    """Renvoie {'corrige': str, 'changements': [...]} ou None si indisponible.

    Ne lève jamais : une relecture est un confort, elle ne doit pas casser la serrure.
    """
    texte = (texte or "").strip()
    if not texte or not disponible():
        return None
    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic()
        reponse = client.messages.create(
            model=MODELE,
            max_tokens=4000,
            system=SYSTEME,
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            messages=[{"role": "user", "content": texte}],
        )
        if reponse.stop_reason == "refusal":
            return None
        brut = next((b.text for b in reponse.content if b.type == "text"), None)
        if not brut:
            return None
        d = json.loads(brut)
    except Exception:
        return None                    # panne réseau, quota, JSON cassé : on n'insiste pas

    corrige = (d.get("corrige") or "").strip()
    if not corrige:
        return None

    # GARDE-FOU. Un modèle qui « améliore » le style produit un texte très différent du
    # brut. Si l'écart dépasse un tiers de la longueur, on refuse la correction : mieux
    # vaut garder les fautes que perdre la voix — c'est toute la raison d'être du module.
    if abs(len(corrige) - len(texte)) > max(30, len(texte) * 0.33):
        return None

    return {"corrige": corrige, "changements": d.get("changements") or []}
