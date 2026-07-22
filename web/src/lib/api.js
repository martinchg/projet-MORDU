/* L'API, en UN SEUL endroit.
 *
 * Avant la migration, ces quatre lignes étaient recopiées à l'identique en tête de chaque
 * page — cinq fois. Corriger l'URL de base ou la gestion d'erreur voulait dire cinq
 * éditions, et j'en ai raté au moins une dans la journée.
 *
 * `?api=` reste supporté : c'est ce qui permet de pointer un autre backend sans toucher
 * au code (utile quand le serveur de dev change de port).
 */
export const API =
  new URLSearchParams(location.search).get('api') || 'http://127.0.0.1:8000';

export async function GET(chemin) {
  const r = await fetch(API + chemin);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

export async function POST(chemin, corps) {
  const r = await fetch(API + chemin, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corps),
  });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

/** Échappe ce qui vient de l'API avant de l'injecter en HTML. */
export const esc = (s) =>
  String(s ?? '').replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

/** Les affiches passent par le proxy du backend : le CDN TMDB n'envoie pas d'en-tête
 *  CORS, donc un canvas qui les dessine deviendrait « tainted » et illisible. */
const cache = {};
export function img(path) {
  if (!path) return null;
  if (cache[path]) return cache[path];
  const im = new Image();
  im.crossOrigin = 'anonymous';
  im.src = `${API}/api/img?path=${encodeURIComponent(path)}&w=342`;
  cache[path] = im;
  return im;
}
