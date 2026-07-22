"""Serveur statique de dev pour le webclient.

`python -m http.server` n'envoie AUCUN en-tête de cache. Les navigateurs appliquent alors
une fraîcheur HEURISTIQUE (dérivée de Last-Modified) et continuent de servir l'ancien
mordu.js / mordu.css pendant des minutes après une modification — on croit que le code ne
marche pas alors qu'il n'a simplement jamais été chargé. Une soirée perdue à débugger un
fichier que le navigateur ne lisait pas.

    python3 serve.py [port]        (défaut : 5173)
"""
import http.server
import sys


class SansCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    print(f"webclient sur http://127.0.0.1:{port}  (sans cache)")
    http.server.test(HandlerClass=SansCache, port=port, bind="127.0.0.1")
