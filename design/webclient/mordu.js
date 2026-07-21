/* MORDU — le moteur visuel.
 *
 * Principe unique dont tout découle : DANS MORDU, TOUT SE RÉSOUT DEPUIS LE BRUIT.
 * L'affiche, le texte, le fond. Un seul geste, décliné partout — c'est ce qui fait
 * que ça ne ressemble pas à un site de plus.
 *
 * Le tramage passe par un shader WebGL au lieu du getImageData() d'avant. Ça débloque
 * trois choses impossibles en canvas 2D :
 *   - le grain VIVANT (le seuil de Bayer dérive dans le temps : l'image respire),
 *   - la dérive de température par carte (avant, toutes les affiches viraient au beige
 *     parce que les tons chair tombaient dans la même bande de palette),
 *   - la révélation à 60 fps (on anime la résolution, pas un re-calcul CPU par frame).
 *
 * Architecture : UN SEUL contexte WebGL, hors écran, qui blitte vers les canvas 2D.
 * Un contexte par vignette ferait sauter la limite du navigateur (~16) dès la grille
 * des domaines.
 */
(function (global) {
  "use strict";

  // Palette indexée « nuit + un rouge ». C'est la contrainte qui unifie un catalogue
  // d'affiches qu'on ne contrôle pas : tout traverse les mêmes 11 couleurs.
  const PALETTE = [
    [10, 12, 16], [20, 28, 40], [34, 46, 60], [52, 74, 84], [80, 104, 112],
    [120, 110, 72], [168, 138, 84], [208, 178, 120], [234, 228, 212],
    [150, 58, 58], [214, 32, 28],
  ];

  const VERT = `
    attribute vec2 aPos;
    varying vec2 vUv;
    void main(){ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }`;

  const FRAG = `
    precision highp float;
    uniform sampler2D uTex;
    uniform vec2  uSize;      // taille du canvas cible
    uniform float uPix;       // nombre de blocs sur la largeur (la « résolution »)
    uniform float uTime;
    uniform float uTemp;      // -1 froid .. +1 chaud  (mood-drift)
    uniform float uNet;       // 0 = tramé, 1 = net et en couleur
    uniform float uGrain;     // souffle du seuil
    uniform float uExpo;      // exposition de l'état aveugle (0.46 carte, 1 portrait)
    uniform vec3  uPal[11];
    varying vec2 vUv;

    // Bayer analytique (pas de texture de seuil à charger)
    float bayer2(vec2 a){ a = floor(a); return fract(a.x / 2.0 + a.y * a.y * 0.75); }
    float bayer4(vec2 a){ return bayer2(0.5 * a) * 0.25 + bayer2(a); }
    float bayer8(vec2 a){ return bayer4(0.5 * a) * 0.25 + bayer2(a); }

    vec3 proche(vec3 c){
      float d = 1e9; vec3 best = uPal[0];
      for (int i = 0; i < 11; i++){
        vec3 p = uPal[i] / 255.0;
        float dd = dot(c - p, c - p);
        if (dd < d){ d = dd; best = p; }
      }
      return best;
    }

    void main(){
      vec2 uv = vec2(vUv.x, 1.0 - vUv.y);
      float ratio = uSize.y / max(uSize.x, 1.0);
      // pixelisation : on quantifie l'UV, donc la « résolution » s'anime en continu
      vec2 blocs = vec2(uPix, max(floor(uPix * ratio), 1.0));
      vec2 uvq = (floor(uv * blocs) + 0.5) / blocs;
      vec2 uvs = mix(uvq, uv, smoothstep(0.75, 1.0, uNet));

      vec3 col = texture2D(uTex, uvs).rgb;

      // Compression des hautes lumières AVANT tout le reste : sans ça, une affiche
      // claire saturait entièrement vers la teinte la plus pâle de la palette et
      // devenait une tache blanche sans texture.
      col = pow(col, vec3(1.38));
      col = col / (col + 0.30) * 1.16;

      // TANT QUE LA CARTE EST AVEUGLE, on l'assombrit. Une affiche qu'on n'a pas le
      // droit de lire n'a aucune raison d'éclairer l'écran : elle doit rester une
      // masse de nuit avec des éclats. C'est la palette de la DA, et ça rend la
      // révélation spectaculaire (le noir qui bascule d'un coup en couleur).
      col *= mix(uExpo, 1.0, smoothstep(0.0, 0.85, uNet));

      // contraste + bascule de température : c'est ce qui distingue enfin les cartes
      col = (col - 0.5) * 1.14 + 0.5;
      col += vec3(0.045, 0.004, -0.035) * uTemp;
      col -= vec3(0.060, 0.050, 0.010);

      // seuil de Bayer qui DÉRIVE : l'image respire au lieu d'être figée
      vec2 cell = uv * blocs;
      float t = bayer8(cell + vec2(uTime * 0.35, -uTime * 0.22)) - 0.5;
      float souffle = sin(uTime * 0.7 + cell.x * 0.12 + cell.y * 0.09) * 0.5 + 0.5;
      col += t * (0.30 + 0.10 * souffle) * uGrain;

      vec3 trame = proche(clamp(col, 0.0, 1.0));
      vec3 brute = texture2D(uTex, uv).rgb;
      gl_FragColor = vec4(mix(trame, brute, smoothstep(0.82, 1.0, uNet)), 1.0);
    }`;

  // --- le contexte partagé -----------------------------------------------------------
  let gl = null, prog = null, tex = null, loc = {}, glCanvas = null, dispo = null;

  function init() {
    if (dispo !== null) return dispo;
    glCanvas = document.createElement("canvas");
    gl = glCanvas.getContext("webgl", { premultipliedAlpha: false, antialias: false })
      || glCanvas.getContext("experimental-webgl");
    if (!gl) return (dispo = false);

    const sh = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.warn("[mordu] shader:", gl.getShaderInfoLog(s));
        return null;
      }
      return s;
    };
    const vs = sh(gl.VERTEX_SHADER, VERT), fs = sh(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return (dispo = false);

    prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return (dispo = false);
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(prog, "aPos");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    ["uTex", "uSize", "uPix", "uTime", "uTemp", "uNet", "uGrain", "uExpo"].forEach(n => {
      loc[n] = gl.getUniformLocation(prog, n);
    });
    const plat = [];
    PALETTE.forEach(c => plat.push(c[0], c[1], c[2]));
    gl.uniform3fv(gl.getUniformLocation(prog, "uPal[0]"), new Float32Array(plat));

    tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    return (dispo = true);
  }

  // recadrage « cover » : on téléverse l'image déjà cadrée, le shader ne gère que le style
  const cadre = document.createElement("canvas");
  const cadreCtx = cadre.getContext("2d", { willReadFrequently: false });
  let derniereImg = null, derniereCle = "";

  function televerse(img, w, h, mode) {
    const cle = (img.src || "") + "|" + w + "x" + h + "|" + mode;
    if (cle === derniereCle && derniereImg === img) return;
    cadre.width = w; cadre.height = h;
    cadreCtx.fillStyle = "#0a0c10"; cadreCtx.fillRect(0, 0, w, h);
    const ar = w / h, iar = img.width / img.height;
    if (mode === "contain") {
      const s = Math.min(w / img.width, h / img.height) * 0.84;
      const dw = img.width * s, dh = img.height * s;
      cadreCtx.drawImage(img, (w - dw) / 2, (h - dh) / 2, dw, dh);
    } else {
      let sw, sh, sx, sy;
      if (iar > ar) { sh = img.height; sw = sh * ar; sx = (img.width - sw) / 2; sy = 0; }
      else { sw = img.width; sh = sw / ar; sx = 0; sy = (img.height - sh) / 2; }
      cadreCtx.drawImage(img, sx, sy, sw, sh, 0, 0, w, h);
    }
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, cadre);
    derniereCle = cle; derniereImg = img;
  }

  /** Dessine `img` tramée dans un canvas 2D.
   *  net 0 -> illisible ; net 1 -> net et en couleur. */
  function tramer(canvas, img, opts) {
    const o = opts || {};
    const net = Math.max(0, Math.min(1, o.net == null ? 0 : o.net));
    const w = Math.max(2, Math.round(o.w || canvas.clientWidth || 240));
    const h = Math.max(2, Math.round(o.h || canvas.clientHeight || 360));
    const ctx = canvas.getContext("2d");
    canvas.width = w; canvas.height = h;

    if (!init() || !img || !img.complete || !img.naturalWidth) {
      ctx.fillStyle = "#0a0c10"; ctx.fillRect(0, 0, w, h);
      return;
    }
    glCanvas.width = w; glCanvas.height = h;
    gl.viewport(0, 0, w, h);
    televerse(img, w, h, o.mode || "cover");

    // la finesse suit la révélation (courbe carrée : ça reste illisible longtemps,
    // puis ça se résout d'un coup — c'est là qu'est le plaisir)
    const pixMin = o.pixMin == null ? 11 : o.pixMin;
    const pix = net >= 0.999 ? Math.max(w, 300) : pixMin + (Math.max(w, 300) - pixMin) * net * net;

    gl.useProgram(prog);
    gl.uniform2f(loc.uSize, w, h);
    gl.uniform1f(loc.uPix, pix);
    gl.uniform1f(loc.uTime, o.temps == null ? performance.now() / 1000 : o.temps);
    gl.uniform1f(loc.uTemp, o.temperature || 0);
    gl.uniform1f(loc.uNet, net);
    gl.uniform1f(loc.uGrain, o.grain == null ? 1 : o.grain);
    gl.uniform1f(loc.uExpo, o.exposition == null ? 0.46 : o.exposition);
    gl.uniform1i(loc.uTex, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.drawArrays(gl.TRIANGLES, 0, 3);

    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(glCanvas, 0, 0);
  }

  /** Boucle de vie : le grain respire tant que la carte est tramée.
   *  La révélation vit DANS cette boucle — deux boucles concurrentes sur le même
   *  canvas se repeignaient l'une sur l'autre (la révélation « réussissait » puis
   *  était effacée à la frame suivante). */
  function animer(canvas, img, opts) {
    let stop = false, raf = 0, transition = null;
    const o = Object.assign({ net: 0 }, opts);
    (function frame() {
      if (stop) return;
      if (transition) {
        const p = Math.min(1, (performance.now() - transition.t0) / transition.duree);
        const e = 1 - Math.pow(1 - p, 3);
        o.net = transition.depart + (1 - transition.depart) * e;
        o.grain = 1 - e * 0.85;
        if (p >= 1) { const fin = transition.fin; transition = null; fin(); }
      }
      tramer(canvas, img, o);
      raf = requestAnimationFrame(frame);
    })();
    return {
      set net(v) { o.net = v; },
      get net() { return o.net; },
      /** LA révélation : la résolution monte, le grain tombe, l'image sort du bruit. */
      reveler(duree) {
        return new Promise(fin => {
          transition = { t0: performance.now(), duree: duree || 1500, depart: o.net, fin };
        });
      },
      arreter() { stop = true; cancelAnimationFrame(raf); },
    };
  }

  /** Révélation ponctuelle (canvas sans boucle de vie). */
  function reveler(canvas, img, opts) {
    const o = Object.assign({ duree: 1500 }, opts);
    const t0 = performance.now();
    return new Promise(resolve => {
      (function frame(t) {
        const p = Math.min(1, (t - t0) / o.duree);
        const e = 1 - Math.pow(1 - p, 3);
        tramer(canvas, img, Object.assign({}, o, { net: e, grain: 1 - e * 0.85 }));
        if (p < 1) requestAnimationFrame(frame); else resolve();
      })(t0);
    });
  }

  /** Température déterministe tirée du film lui-même (DA : déterministe, pas de ML).
   *  Un thriller nocturne doit tirer au froid, une comédie au chaud — c'est le
   *  « mood-drift » de la direction artistique, et c'est ce qui distingue les cartes. */
  const _FROID = { Thriller: -1, Horror: -1.2, Crime: -.8, Mystery: -.8, "Science Fiction": -.6,
                   Drama: -.2, War: -.5, Documentary: -.3 };
  const _CHAUD = { Comedy: 1, Romance: .9, Family: .8, Animation: .7, Adventure: .5,
                   Music: .8, Fantasy: .4, Western: .6, History: .2 };
  function temperature(film) {
    const g = (film && film.genres) || [];
    let s = 0, n = 0;
    g.forEach(x => {
      if (x in _FROID) { s += _FROID[x]; n++; }
      else if (x in _CHAUD) { s += _CHAUD[x]; n++; }
    });
    // amplitude volontairement resserrée : à ±1 la couleur mangeait l'image
    return n ? Math.max(-0.55, Math.min(0.55, (s / n) * 0.55)) : 0;
  }

  // --- le fond : un champ de bruit qui dérive -----------------------------------------
  // Pas un dégradé animé de plus : c'est la MÊME matière que les affiches, au repos.
  // Presque invisible, mais l'écran cesse d'être mort.
  function fond(opts) {
    const o = Object.assign({ opacite: 0.5, vitesse: 1 }, opts);
    const cv = document.createElement("canvas");
    cv.setAttribute("aria-hidden", "true");
    Object.assign(cv.style, {
      position: "fixed", inset: "0", width: "100%", height: "100%",
      zIndex: "0", pointerEvents: "none", opacity: String(o.opacite),
    });
    document.body.prepend(cv);
    const ctx = cv.getContext("2d");
    let W = 0, H = 0, C = 0, R = 0;
    const TAILLE = 15;                  // côté d'une cellule, en px

    function redim() {
      W = cv.width = Math.ceil(innerWidth / TAILLE);
      H = cv.height = Math.ceil(innerHeight / TAILLE);
      cv.style.imageRendering = "pixelated";
      C = W; R = H;
    }
    redim();
    addEventListener("resize", redim, { passive: true });

    // Bruit de VALEUR (hash + interpolation), pas des sinus croisés : ceux-ci
    // produisaient des rayures verticales régulières — ça lisait « artefact », pas
    // « matière ». Ici la nappe est organique, comme du grain de pellicule.
    function hash(x, y) {
      let h = x * 374761393 + y * 668265263;
      h = (h ^ (h >> 13)) * 1274126177;
      return ((h ^ (h >> 16)) >>> 0) / 4294967295;
    }
    const lisse = t => t * t * (3 - 2 * t);
    function bruit(x, y) {
      const xi = Math.floor(x), yi = Math.floor(y);
      const xf = lisse(x - xi), yf = lisse(y - yi);
      const a = hash(xi, yi), b = hash(xi + 1, yi);
      const c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
      return (a + (b - a) * xf) + ((c + (d - c) * xf) - (a + (b - a) * xf)) * yf;
    }

    let t = 0, dernier = 0;
    (function frame(now) {
      requestAnimationFrame(frame);
      if (now - dernier < 70) return;   // ~14 fps : c'est un fond, pas un jeu vidéo
      dernier = now; t += 0.006 * o.vitesse;
      const d = ctx.createImageData(C, R);
      const p = d.data;
      for (let y = 0; y < R; y++) {
        for (let x = 0; x < C; x++) {
          // deux octaves qui dérivent en sens contraire = respiration lente
          const n = bruit(x * 0.055 + t, y * 0.055 - t * 0.6) * 0.65
                  + bruit(x * 0.13 - t * 0.4, y * 0.13 + t * 0.3) * 0.35;
          const bay = (((x & 3) * 4 + (y & 3)) / 16 - 0.5) * 0.16;  // le tramage, toujours lui
          const v = n + bay;
          const i = (y * C + x) * 4;
          let c;
          // Seuils calés sur les QUARTILES MESURÉS de ce bruit (min -0.08, médiane
          // 0.22, max 0.53) et non à l'intuition : mes premiers seuils étaient à 0.58
          // et 0.70, que la fonction n'atteint JAMAIS — les deux paliers les plus
          // clairs n'étaient donc jamais utilisés et le fond restait plat. Ici chaque
          // palier reçoit ~25 % des cellules, donc le champ respire vraiment.
          // Écart entre paliers RESSERRÉ après essai : à pleine amplitude le champ
          // créait des bandes verticales qui se disputaient avec le texte. Les quatre
          // paliers restent actifs (c'est ça qui le fait respirer), mais l'amplitude
          // est divisée par deux — un fond doit se sentir, pas se voir.
          if (v > 0.29) c = [40, 51, 69];
          else if (v > 0.223) c = [31, 39, 53];
          else if (v > 0.158) c = [23, 29, 39];
          else c = [16, 20, 27];
          // une braise rouge, très rare : le punch de la DA, à dose homéopathique
          if (v > 0.36 && ((x * 7 + y * 13 + ((t * 90) | 0)) % 197 === 0)) c = [165, 36, 32];
          p[i] = c[0]; p[i + 1] = c[1]; p[i + 2] = c[2]; p[i + 3] = 255;
        }
      }
      ctx.putImageData(d, 0, 0);
    })(0);
    return cv;
  }

  // --- le texte se résout lui aussi depuis le bruit ------------------------------------
  const GLYPHES = "▓▒░#@%&/\\|=+*<>[]{}—·01";
  function resoudreTexte(el, texte, opts) {
    const o = Object.assign({ duree: 900, retard: 0 }, opts);
    const cible = String(texte);
    const t0 = performance.now() + o.retard;
    el.textContent = "";
    return new Promise(resolve => {
      (function frame(t) {
        const p = Math.max(0, Math.min(1, (t - t0) / o.duree));
        let out = "";
        for (let i = 0; i < cible.length; i++) {
          const seuil = i / cible.length;
          if (p > seuil + 0.22) out += cible[i];
          else if (p > seuil - 0.05 && cible[i] !== " ")
            out += GLYPHES[(Math.random() * GLYPHES.length) | 0];
          else out += cible[i] === " " ? " " : "";
        }
        el.textContent = out;
        if (p < 1) requestAnimationFrame(frame);
        else { el.textContent = cible; resolve(); }
      })(performance.now());
    });
  }

  global.MORDU = {
    PALETTE, tramer, animer, reveler, fond, resoudreTexte, temperature,
    get webgl() { return init(); },
  };
})(window);
