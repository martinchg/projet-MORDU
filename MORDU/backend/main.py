from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# IMPORTANT : Le CORS permet à ton React (port 5173) de parler à FastAPI (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # On autorise tout pour le dev
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/movies")
async def get_movies():
    # Simulation de base de données (ce que ton RAG et ton IA rempliront)
    return [
        {
            "id": "arcane",
            "title": "Arcane",
            "studio": "Fortiche",
            "color": "bg-blue-400",
            "insight": "Fortiche a utilisé un mélange unique de textures 2D sur des modèles 3D, une technique appelée 'digital painting' qui donne cet aspect fait main."
        },
        {
            "id": "midsommar",
            "title": "Midsommar",
            "studio": "A24",
            "color": "bg-orange-300",
            "insight": "A24 a révolutionné l'horreur avec ce film en utilisant la lumière du jour constante pour créer une angoisse psychologique sans jumpscares."
        }
    ]