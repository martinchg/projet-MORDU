// @ts-check
import { defineConfig } from 'astro/config';

/* MORDU — configuration Astro.
 *
 * POURQUOI ASTRO ET PAS REACT. Le produit est MULTI-PAGES par nature (un écran = un
 * moment du rituel), et son meilleur détail visuel est la View Transition INTER-DOCUMENTS
 * native : les pages morphent l'une dans l'autre au niveau du navigateur, sans routeur
 * JavaScript. Un framework SPA aurait remplacé ça par son propre routeur, et fait perdre
 * exactement ce qu'on avait de plus rare.
 *
 * Astro sort du HTML statique et n'envoie AUCUN JavaScript de framework. On garde donc
 * tout ce qui marchait, et on gagne ce qui manquait : des composants (la barre de
 * navigation existait en CINQ exemplaires), un module partagé pour l'API (le même `GET`
 * était recopié dans chaque page), et un build.
 *
 * On n'utilise PAS `<ClientRouter />` : il ferait basculer le site en navigation SPA et
 * écraserait la View Transition native du navigateur. C'est délibéré.
 */
export default defineConfig({
  server: { port: 4321 },
  devToolbar: { enabled: false },
});
