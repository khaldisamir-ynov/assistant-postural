"""Jeu de donnees genere : des personnes variees a leur bureau, vues par une webcam, dans les postures VISIBLES sur
une seule image (telephone, boisson, menton dans la main), pour l'essai VLM (C9) et la robustesse de MediaPipe.

Pour chaque personne : une image « droit » generee (texte -> image), puis chaque posture obtenue en MODIFIANT cette
image (meme visage, meme camera, meme cadrage). « droit2 » (rien ne change) sert de temoin : il mesure combien la
modification deplace le corps a elle seule.
Pas de tete en avant, avachi, trop pres, clavier ni penche : essai du 2026-11-06, le modele de modification ne les
produit pas (Kontext) ou deplace le corps de 5 fois le seuil sur une image « inchangee » (Qwen-Image-Edit).
Images ecrites dans <dossier>/photos/<posture>_<personne>.jpg, deja presentes = non regenerees (relance sans surcout).

Usage : .venv\\Scripts\\python essais\\generer_images.py essais\\donnees\\genere [--personnes N]
Puis : essais\\images_vers_reperes.py (banc rejouer.py) et/ou essais\\comparer_vlm.py (telephone / boisson).
Configuration : HF_TOKEN et HF_BILL_TO dans .env. Payant (fournisseurs du routeur HF), 5 images par personne.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

GENERATE = "Qwen/Qwen-Image"
# Garde visage, decor et couleurs ; temoin « droit2 » : raccourcissement 0,4 % (seuil 3 %). Qwen-Image-Edit : 16,5 %
EDIT = "black-forest-labs/FLUX.1-Kontext-dev"
# Diversite volontaire : age, genre, peau, accessoires, eclairage, decor (une personne = une ligne)
PEOPLE = [
    "a woman in her twenties with dark brown skin and braided hair, wearing a grey hoodie, in a bright home office",
    "a man in his fifties with light skin, grey beard and glasses, wearing a shirt, in an open-plan office",
    "a woman in her forties wearing a hijab, olive skin, in a small study lit by a desk lamp in the evening",
    "a young man with East Asian features and headphones around the neck, in a dim bedroom, screen light on the face",
    "a woman in her sixties with short white hair and reading glasses, in a living room, window behind her",
    "a broad-shouldered man in his thirties with a shaved head and tattoos, wearing a t-shirt, in a coworking space",
    "a slim teenage girl with freckles and red hair in a ponytail, in a cluttered student room",
    "a man in his forties with South Asian features and a turban, wearing a sweater, in a cafe",
]
# « webcam » ou « video call » seuls : le modele dessine un ordinateur qui affiche la personne ; d'ou « raw frame »
SCENE = ("Raw webcam frame, front-facing, camera at chest height just in front of the person: {person}, sitting upright "
         "and looking straight at the camera. Head, shoulders and upper chest fill the frame, room behind. The picture "
         "contains only the person and the room: no device, no screen, no interface, no text. Slightly soft focus, "
         "webcam noise.")
KEEP = " Same person, same camera, same framing, same background and lighting; change nothing else."
# Codes de essais/enregistrer.py (lus par rejouer.py et comparer_vlm.py) -> modification demandee
POSTURES = {
    "droit2": "The person is still sitting upright, with a tiny natural change of expression.",
    "menton_main": "The person rests the chin on one hand, elbow on the desk.",
    "telephone": "The person holds a smartphone against the ear with one hand.",
    "boire": "The person drinks from a coffee mug held at the mouth.",
}


def main():
    out = Path(sys.argv[1]) / "photos"
    count = int(sys.argv[sys.argv.index("--personnes") + 1]) if "--personnes" in sys.argv else len(PEOPLE)
    load_dotenv(".env")  # dossier courant : lancer depuis la racine du projet
    token = os.getenv("HF_TOKEN") or sys.exit("HF_TOKEN absent du .env")
    client = InferenceClient(provider="auto", api_key=token, bill_to=os.getenv("HF_BILL_TO") or None, timeout=180)
    out.mkdir(parents=True, exist_ok=True)
    for i, person in enumerate(PEOPLE[:count]):
        ref = out / f"droit_{i}.jpg"
        if not ref.exists():
            client.text_to_image(SCENE.format(person=person), model=GENERATE, width=1024, height=768).convert(
                "RGB").save(ref)
        for posture, change in POSTURES.items():
            path = out / f"{posture}_{i}.jpg"
            if path.exists():
                continue
            try:
                client.image_to_image(ref, prompt=change + KEEP, model=EDIT).convert("RGB").save(path)
            except Exception as e:  # une modification refusee ou en echec ne bloque pas le reste du jeu
                print(f"  {path.name} : echec ({e})")
        print(f"Personne {i} : {person}")
    print(f"Images dans {out} : verifiez-les a l'oeil et supprimez celles qui ne montrent pas la posture demandee.")


if __name__ == "__main__":
    main()
