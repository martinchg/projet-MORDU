/* PROTOTYPE — l'écran « domaines » en îlot Preact, À CÔTÉ de domaines.astro.
 *
 * Rien n'est remplacé : la page d'origine reste la seule branchée sur la navigation.
 * Ce fichier existe pour répondre à UNE question mesurable — « est-ce que ça règle une
 * douleur réelle, et à quel prix en octets ? ».
 *
 * Ce qui change par rapport à la version innerHTML, et qui est vérifiable :
 *   1. plus AUCUN `esc()` : JSX échappe le texte par construction. `d.name`, `f.title`,
 *      `f.year` étaient injectés bruts (domaines.astro L73, L92, L99) — impossible ici.
 *   2. plus AUCUN écouteur reposé : `onClick` est attaché au nœud, pas re-créé après un
 *      innerHTML. La version d'origine reposait 262 écouteurs (190 cartes + 72 films) à
 *      CHAQUE case cochée.
 *   3. le canvas n'est repeint que si SA maîtrise a changé (useEffect sur `net`), au lieu
 *      des 190 appels à MORDU.tramer que déclenchait un seul clic.
 *   4. une seule source de vérité pour `watched` : l'état Preact. localStorage devient un
 *      effet de bord, plus une seconde copie qu'on resynchronise à la main.
 */
import { useState, useEffect, useRef, useMemo } from 'preact/hooks';
import { GET, img } from '../../lib/api.js';

const LS = 'mordu_vus_proto';   // clé DISTINCTE : le prototype ne touche pas l'état réel
const ETIQ = { director: 'Réal', actor: 'Acteur', studio: 'Studio' };

/** Une vignette tramée. Le canvas survit aux re-rendus ; seul `net` le fait repeindre. */
function Vignette({ path, net, type, w = 150, h = 200 }) {
  const cv = useRef(null);
  useEffect(() => {
    const el = cv.current;
    if (!el) return;
    const im = img(path);
    const rendre = () =>
      window.MORDU.tramer(el, im, {
        net, w, h, pixMin: 14,
        mode: type === 'studio' ? 'contain' : 'cover',
        temperature: (net - 0.5) * 0.5,
        exposition: 0.9,
      });
    if (im && !im.complete) {
      im.addEventListener('load', rendre, { once: true });
      im.addEventListener('error', rendre, { once: true });
    }
    rendre();
  }, [path, net, type]);
  return <canvas ref={cv} />;
}

function Carte({ d, vus, onOuvrir }) {
  const dedans = d.catalogue_ids.filter((i) => vus.has(i)).length;
  const m = d.catalogue_ids.length ? dedans / d.catalogue_ids.length : 0;
  return (
    <div class={'dom apparait' + (m >= 0.999 ? ' done' : '')} onClick={onOuvrir}>
      <div class="frame">
        <Vignette path={d.image_path} net={m} type={d.type} />
        <span class="tag">{ETIQ[d.type]}</span>
      </div>
      <div class="name">{d.name}</div>
      <div class="m"><i style={{ width: Math.round(m * 100) + '%' }} /></div>
      <div class="mv">{dedans}/{d.catalogue_ids.length} vus · {d.canon_size} essentiels</div>
    </div>
  );
}

function Modale({ dom, vus, basculer, fermer }) {
  const [plein, setPlein] = useState(null);
  useEffect(() => {
    let vivant = true;
    setPlein(null);
    GET(`/api/domaine/${dom.type}/${dom.id}`)
      .then((r) => vivant && setPlein(r))
      .catch(() => vivant && setPlein(false));
    return () => { vivant = false; };
  }, [dom.type, dom.id]);

  const dansCat = useMemo(
    () => new Set(plein ? plein.catalogue_ids : []),
    [plein]
  );

  return (
    <div class="modal on" onClick={(e) => e.target === e.currentTarget && fermer()}>
      <div class="sheet">
        {plein === null && <p class="empty">chargement…</p>}
        {plein === false && <p class="empty">erreur</p>}
        {plein && (
          <>
            <button class="close" onClick={fermer}>fermer ✕</button>
            <h3>{plein.name}</h3>
            <div class="sub">
              canon : {plein.canon_size} films essentiels · {plein.catalogue_ids.length} dans
              MORDU · <b style="color:var(--green)">
                {plein.catalogue_ids.filter((i) => vus.has(i)).length} vus
              </b> — coche ce que t'as vu
            </div>
            <div class="films">
              {plein.canon.map((f) => {
                const a = dansCat.has(f.id), vu = vus.has(f.id);
                return (
                  <div
                    key={f.id}
                    class={'film ' + (a ? (vu ? 'seen' : '') : 'off na')}
                    onClick={() => a && basculer(f.id)}
                  >
                    {f.poster_url
                      ? <img src={f.poster_url} alt="" loading="lazy" />
                      : <div class="ph" />}
                    <span class="chk">{vu ? '✓ vu' : 'vu ?'}</span>
                    <div class="ft">{f.title}</div>
                    <div class="fy">{f.year || ''}{a ? '' : ' · hors MORDU'}</div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function DomainesIlot() {
  const [domaines, setDomaines] = useState([]);
  const [filtre, setFiltre] = useState('all');
  const [vus, setVus] = useState(() => new Set(JSON.parse(localStorage.getItem(LS) || '[]')));
  const [ouvert, setOuvert] = useState(null);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const h = await GET('/api/health');
        let v = new Set(vus);
        try { (await GET('/api/vus')).forEach((i) => v.add(i)); } catch { /* serveur muet */ }
        setVus(v);
        const d = await GET('/api/domaines?min_catalogue=2');
        setDomaines(d);
        const st = document.getElementById('status');
        if (st) { st.className = 'status ok'; st.textContent = `API connectée · ${h.films} films · ${v.size} vus`; }
      } catch (e) {
        console.error('[domaines-preact]', e);
        setErreur(e instanceof TypeError ? 'API hors ligne' : 'erreur de rendu');
        const st = document.getElementById('status');
        if (st) { st.className = 'status ko'; st.textContent = 'API hors ligne'; }
      }
    })();
  }, []);

  // localStorage n'est plus une seconde source de vérité : c'est un effet de l'état.
  useEffect(() => { localStorage.setItem(LS, JSON.stringify([...vus])); }, [vus]);

  const basculer = (id) =>
    setVus((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const liste = domaines.filter((d) => filtre === 'all' || d.type === filtre);

  if (erreur) return <div class="banner"><b>{erreur}</b> — lance <code>uvicorn main:app --reload</code> et recharge.</div>;

  return (
    <>
      <div class="filters">
        {[['all', 'Tous'], ['director', 'Réalisateurs'], ['actor', 'Acteurs'], ['studio', 'Studios']]
          .map(([k, lbl]) => (
            <button key={k} aria-pressed={filtre === k} onClick={() => setFiltre(k)}>{lbl}</button>
          ))}
      </div>
      {!liste.length
        ? <p class="empty">…</p>
        : <div class="grid">
            {liste.map((d) => (
              <Carte key={d.type + d.id} d={d} vus={vus} onOuvrir={() => setOuvert(d)} />
            ))}
          </div>}
      {ouvert && (
        <Modale dom={ouvert} vus={vus} basculer={basculer} fermer={() => setOuvert(null)} />
      )}
    </>
  );
}
