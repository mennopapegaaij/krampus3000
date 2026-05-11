"""Krampus3000 - een simpel echt 3D horrorspel."""

import math
import random

from ursina import (
    AmbientLight,
    DirectionalLight,
    Entity,
    PointLight,
    Text,
    Ursina,
    Vec3,
    application,
    camera,
    color,
    mouse,
    time,
    window,
)
from ursina.prefabs.first_person_controller import FirstPersonController


TITEL = "Krampus3000"
TILE_GROOTTE = 4
SPELER_SNELHEID = 5
KRAMPUS_SNELHEID = 2.2

# Dit is de 3D kaart van het spel.
KAART = [
    "#####################",
    "#S..#........#..K..D#",
    "#.#.#.######.#.###..#",
    "#.#...#...K#...#....#",
    "#.#####.#.#####.###.#",
    "#.....#.#.....#..K..#",
    "###.#.#.#####.#####.#",
    "#...#.#...#...#.....#",
    "#.###.###.#.###.###.#",
    "#...K.#...#.....#M..#",
    "#####################",
]


def kleur(rood, groen, blauw, alpha=1.0):
    """Maak een Ursina-kleur met gewone 0-255 getallen."""
    echte_alpha = alpha if alpha <= 1 else alpha / 255
    return color.rgba(rood / 255, groen / 255, blauw / 255, echte_alpha)


def kaart_naar_wereld(kolom, rij):
    """Zet een plek uit de kaart om naar een 3D plek."""
    midden_x = (len(KAART[0]) - 1) * TILE_GROOTTE / 2
    midden_z = (len(KAART) - 1) * TILE_GROOTTE / 2
    return Vec3(kolom * TILE_GROOTTE - midden_x, 0, rij * TILE_GROOTTE - midden_z)


def afstand_xz(plek_a, plek_b):
    """Bereken de afstand over de grond."""
    verschil_x = plek_a.x - plek_b.x
    verschil_z = plek_a.z - plek_b.z
    return math.sqrt(verschil_x * verschil_x + verschil_z * verschil_z)


def zet_muis_vergrendeld(vergrendeld):
    """Vergrendel de muis alleen als het venster dat kan."""
    basis = getattr(application, "base", None)
    venster = getattr(basis, "win", None)
    if venster is not None and hasattr(venster, "requestProperties"):
        mouse.locked = vergrendeld


class Krampus3000Spel:
    """Beheer het hele 3D horrorspel."""

    def __init__(self):
        # Dit maakt het spelvenster netter.
        window.title = TITEL
        window.color = kleur(8, 6, 10)
        window.exit_button.visible = False
        window.fps_counter.enabled = False
        camera.fov = 92
        zet_muis_vergrendeld(True)

        self.speler_start = Vec3(0, 1.5, 0)
        self.krampus_start = Vec3(0, 0, 0)
        self.deur_plek = Vec3(0, 1.6, 0)
        self.sleutel_plekken = []
        self.beste_tijd = None
        self.tijd_seconden = 0.0
        self.status = "spelen"
        self.heeft_sleutel = False
        self.melding = ""

        self.maak_wereld()
        self.maak_speler()
        self.maak_krampus()
        self.maak_sleutel()
        self.maak_ui()
        self.reset_spel()

    def maak_wereld(self):
        """Bouw de 3D kamer, muren en deur."""
        vloer_breedte = len(KAART[0]) * TILE_GROOTTE
        vloer_diepte = len(KAART) * TILE_GROOTTE

        # Een donkere luchtbol maakt het spel meteen enger.
        self.lucht = Entity(
            model="sphere",
            scale=180,
            double_sided=True,
            color=kleur(18, 10, 16),
        )
        self.vloer = Entity(
            model="plane",
            scale=(vloer_breedte + 8, 1, vloer_diepte + 8),
            color=kleur(34, 24, 34),
            texture_scale=(12, 12),
            collider="box",
        )
        self.plafond = Entity(
            model="cube",
            scale=(vloer_breedte + 8, 0.5, vloer_diepte + 8),
            position=(0, 4.4, 0),
            color=kleur(20, 12, 18),
        )

        self.muren = []
        for rij, regel in enumerate(KAART):
            for kolom, teken in enumerate(regel):
                plek = kaart_naar_wereld(kolom, rij)

                if teken == "#":
                    muur = Entity(
                        model="cube",
                        position=(plek.x, 2, plek.z),
                        scale=(TILE_GROOTTE, 4, TILE_GROOTTE),
                        color=kleur(72, 44, 78),
                        collider="box",
                    )
                    rand = Entity(
                        parent=muur,
                        model="cube",
                        scale=1.02,
                        color=kleur(120, 84, 132, 70),
                    )
                    self.muren.append(muur)
                elif teken == "S":
                    self.speler_start = Vec3(plek.x, 1.5, plek.z)
                elif teken == "M":
                    self.krampus_start = Vec3(plek.x, 0, plek.z)
                elif teken == "D":
                    self.deur_plek = Vec3(plek.x, 1.6, plek.z)
                elif teken == "K":
                    self.sleutel_plekken.append(Vec3(plek.x, 1.0, plek.z))

        self.deur = Entity(
            model="cube",
            position=self.deur_plek,
            scale=(2.2, 3.2, 0.45),
            color=kleur(110, 44, 58),
            collider="box",
        )
        self.deur_glans = Entity(
            parent=self.deur,
            model="cube",
            scale=(0.18, 0.3, 1.04),
            x=0.7,
            y=0.1,
            color=kleur(255, 240, 210, 120),
        )

        # Licht maakt de kamer beter zichtbaar maar nog steeds spannend.
        self.ambient_licht = AmbientLight(color=kleur(110, 90, 100, 0.35))
        self.richting_licht = DirectionalLight(color=kleur(255, 220, 210, 0.25))
        self.richting_licht.look_at(Vec3(1, -2, -1))

    def maak_speler(self):
        """Maak de speler met een first-person camera."""
        self.speler = FirstPersonController(
            position=self.speler_start,
            speed=SPELER_SNELHEID,
            origin_y=-0.45,
        )
        self.speler.gravity = 0
        self.speler.cursor.color = kleur(255, 255, 255, 180)
        self.speler_licht = PointLight(
            parent=self.speler,
            y=1.2,
            color=kleur(255, 220, 170, 140),
        )

    def maak_krampus(self):
        """Maak Krampus als een simpel 3D monster."""
        self.krampus = Entity(position=self.krampus_start)
        self.krampus_lijf = Entity(
            parent=self.krampus,
            model="cube",
            y=1.2,
            scale=(1.1, 2.1, 0.9),
            color=kleur(120, 36, 46),
        )
        self.krampus_kop = Entity(
            parent=self.krampus,
            model="sphere",
            y=2.45,
            scale=1.1,
            color=kleur(142, 44, 56),
        )
        self.krampus_oog_links = Entity(
            parent=self.krampus,
            model="sphere",
            position=(-0.22, 2.5, 0.47),
            scale=0.13,
            color=kleur(255, 210, 120),
        )
        self.krampus_oog_rechts = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0.22, 2.5, 0.47),
            scale=0.13,
            color=kleur(255, 210, 120),
        )
        self.krampus_hoorn_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.36, 3.1, 0.02),
            rotation=(0, 0, 28),
            scale=(0.16, 0.55, 0.16),
            color=kleur(220, 215, 205),
        )
        self.krampus_hoorn_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.36, 3.1, 0.02),
            rotation=(0, 0, -28),
            scale=(0.16, 0.55, 0.16),
            color=kleur(220, 215, 205),
        )

    def maak_sleutel(self):
        """Maak de sleutel als een klein 3D voorwerp."""
        self.sleutel = Entity(
            model="cube",
            position=(0, 1.0, 0),
            scale=(0.28, 0.16, 0.95),
            color=kleur(244, 210, 86),
        )
        self.sleutel_ring = Entity(
            parent=self.sleutel,
            model="sphere",
            x=-0.36,
            scale=(0.48, 0.48, 0.12),
            color=kleur(255, 230, 120),
        )

    def maak_ui(self):
        """Maak alle tekst op het scherm."""
        self.titel_tekst = Text("Krampus3000", x=-0.85, y=0.45, scale=2.1, color=kleur(255, 245, 250))
        self.status_tekst = Text("", x=-0.85, y=0.38, scale=1.15, color=kleur(240, 230, 240))
        self.tijd_tekst = Text("", x=-0.85, y=0.32, scale=1.0, color=kleur(255, 226, 160))
        self.beste_tijd_tekst = Text("", x=-0.55, y=0.32, scale=1.0, color=kleur(190, 175, 195))
        self.hint_tekst = Text("", x=-0.85, y=0.26, scale=0.95, color=kleur(210, 190, 210))
        self.besturing_tekst = Text(
            "WASD = lopen | muis = kijken | R = opnieuw | Esc = stoppen",
            x=-0.85,
            y=-0.46,
            scale=0.9,
            color=kleur(200, 180, 200),
        )

    def reset_spel(self):
        """Begin opnieuw met een nieuw rondje."""
        self.speler.position = self.speler_start
        self.speler.rotation = (0, 0, 0)
        self.speler.camera_pivot.rotation = (0, 0, 0)
        self.krampus.position = self.krampus_start
        self.krampus.rotation_y = 0
        self.sleutel.position = random.choice(self.sleutel_plekken)
        self.sleutel.enabled = True
        self.deur.color = kleur(110, 44, 58)
        self.heeft_sleutel = False
        self.status = "spelen"
        self.tijd_seconden = 0.0
        self.melding = "Zoek de sleutel en blijf weg van Krampus."
        self.speler.enabled = True
        zet_muis_vergrendeld(True)
        self.werk_tekst_bij()

    def werk_tekst_bij(self):
        """Zet de goede tekst op het scherm."""
        if self.status == "spelen":
            if self.heeft_sleutel:
                opdracht = "Je hebt de sleutel! Ren nu naar de groene deur."
            else:
                opdracht = "Zoek de sleutel voordat Krampus je vindt."
        elif self.status == "gewonnen":
            opdracht = "Je bent ontsnapt! Druk op R voor nog een potje."
        else:
            opdracht = "Krampus heeft je gepakt... Druk op R om opnieuw te beginnen."

        self.status_tekst.text = opdracht
        self.tijd_tekst.text = f"Tijd: {self.tijd_seconden:.1f} sec"
        if self.beste_tijd is None:
            self.beste_tijd_tekst.text = "Beste tijd: -"
        else:
            self.beste_tijd_tekst.text = f"Beste tijd: {self.beste_tijd:.1f} sec"
        self.hint_tekst.text = self.melding

    def pak_sleutel(self):
        """Pak de sleutel en open de deur."""
        self.heeft_sleutel = True
        self.sleutel.enabled = False
        self.deur.color = kleur(70, 160, 96)
        self.melding = "De deur is open! Snel naar de uitgang."
        self.werk_tekst_bij()

    def win_spel(self):
        """Laat zien dat je gewonnen hebt."""
        self.status = "gewonnen"
        self.speler.enabled = False
        zet_muis_vergrendeld(False)
        if self.beste_tijd is None or self.tijd_seconden < self.beste_tijd:
            self.beste_tijd = self.tijd_seconden
        self.melding = "Krampus was te laat. Jij hebt gewonnen!"
        self.werk_tekst_bij()

    def verlies_spel(self):
        """Laat zien dat je verloren hebt."""
        self.status = "verloren"
        self.speler.enabled = False
        zet_muis_vergrendeld(False)
        self.melding = "Ai! Krampus greep je te pakken."
        self.werk_tekst_bij()

    def beweeg_krampus(self):
        """Laat Krampus langzaam naar de speler lopen."""
        richting = Vec3(
            self.speler.x - self.krampus.x,
            0,
            self.speler.z - self.krampus.z,
        )
        if richting.length() <= 0.2:
            return

        snelheid = KRAMPUS_SNELHEID + (0.8 if self.heeft_sleutel else 0)
        stap = richting.normalized() * snelheid * time.dt
        self.krampus.position += stap
        self.krampus.look_at_2d(self.speler.position, "y")
        self.krampus.y = math.sin(self.tijd_seconden * 5) * 0.05

    def draai_sleutel(self):
        """Laat de sleutel draaien en zweven."""
        if not self.sleutel.enabled:
            return
        self.sleutel.rotation_y += 120 * time.dt
        self.sleutel.y = 1.0 + math.sin(self.tijd_seconden * 4) * 0.12

    def update(self):
        """Werk alles elke frame bij."""
        self.draai_sleutel()

        if self.status != "spelen":
            return

        self.tijd_seconden += time.dt
        self.speler.y = 1.5
        self.beweeg_krampus()

        if not self.heeft_sleutel and afstand_xz(self.speler.position, self.sleutel.position) < 1.4:
            self.pak_sleutel()

        if afstand_xz(self.speler.position, self.deur.position) < 1.7:
            if self.heeft_sleutel:
                self.win_spel()
            else:
                self.melding = "De deur zit nog op slot. Zoek de sleutel."
                self.werk_tekst_bij()

        if afstand_xz(self.speler.position, self.krampus.position) < 1.3:
            self.verlies_spel()

        self.werk_tekst_bij()

    def input(self, toets):
        """Reageer op toetsen van de speler."""
        if toets == "r":
            self.reset_spel()
        elif toets == "escape":
            application.quit()


spel = None


def update():
    """Stuur de update door naar het spel."""
    if spel is not None:
        spel.update()


def input(toets):
    """Stuur invoer door naar het spel."""
    if spel is not None:
        spel.input(toets)


def main():
    """Start Krampus3000."""
    global spel
    app = Ursina(development_mode=False, editor_ui_enabled=False)
    spel = Krampus3000Spel()
    app.run()


if __name__ == "__main__":
    main()
