"""Krampus3000 - een simpel echt 3D horrorspel."""

from collections import deque
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
    held_keys,
    mouse,
    raycast,
    time,
    window,
)
from ursina.prefabs.first_person_controller import FirstPersonController


TITEL = "Krampus3000"
TILE_GROOTTE = 4
SPELER_SNELHEID = 5
KRAMPUS_SNELHEID = 2.2
PIJL_DRAAI_SNELHEID = 120
PIJL_KIJK_SNELHEID = 80
KRAMPUS_STRAAL = 0.55
DEUR_KLIK_AFSTAND = 5
KRAMPUS_PAD_INTERVAL = 0.25
KRAMPUS_WEGPUNT_BEREIK = 0.35

# Dit is de 3D kaart van het spel.
KAART = [
    "#####################",
    "#S..#.....O..#..K..D#",
    "#.#.#.######.#.###..#",
    "#.#...#...K#...#....#",
    "#.#####.#.#####.###.#",
    "#.O...#.#.....#..K..#",
    "###.#.#.#####.#####.#",
    "#...#.#...#...#.O...#",
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


def wereld_naar_kaart(plek):
    """Zet een 3D plek om naar een plek op de kaart."""
    midden_x = (len(KAART[0]) - 1) * TILE_GROOTTE / 2
    midden_z = (len(KAART) - 1) * TILE_GROOTTE / 2
    kolom = int(round((plek.x + midden_x) / TILE_GROOTTE))
    rij = int(round((plek.z + midden_z) / TILE_GROOTTE))
    kolom = max(0, min(len(KAART[0]) - 1, kolom))
    rij = max(0, min(len(KAART) - 1, rij))
    return kolom, rij


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
        self.klik_deuren = []
        self.klikdeur_per_tegel = {}
        self.krampus_pad = []
        self.krampus_pad_doel = None
        self.krampus_pad_timer = 0.0
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
        self.klik_deuren = []
        self.klikdeur_per_tegel = {}
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
                elif teken == "O":
                    self.maak_klikdeur(kolom, rij, plek)

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

    def maak_klikdeur(self, kolom, rij, plek):
        """Maak een deur die je met een klik kunt openen."""
        schaal = self.bepaal_klikdeur_schaal(kolom, rij)
        deur = Entity(
            model="cube",
            position=(plek.x, 1.6, plek.z),
            scale=schaal,
            color=kleur(126, 66, 152),
            collider="box",
        )
        deur.gesloten_positie = Vec3(plek.x, 1.6, plek.z)
        deur.gesloten_scale = Vec3(schaal.x, schaal.y, schaal.z)
        deur.open_positie = Vec3(plek.x, 0.22, plek.z)
        deur.open_scale = Vec3(schaal.x, 0.25, schaal.z)
        deur.is_open = False
        deur.kaart_kolom = kolom
        deur.kaart_rij = rij
        self.klik_deuren.append(deur)
        self.klikdeur_per_tegel[(kolom, rij)] = deur

    def bepaal_klikdeur_schaal(self, kolom, rij):
        """Kies hoe de deur moet staan in de gang."""
        links_blok = KAART[rij][kolom - 1] == "#"
        rechts_blok = KAART[rij][kolom + 1] == "#"
        boven_blok = KAART[rij - 1][kolom] == "#"
        onder_blok = KAART[rij + 1][kolom] == "#"

        if boven_blok and onder_blok:
            return Vec3(0.45, 3.2, TILE_GROOTTE)
        if links_blok and rechts_blok:
            return Vec3(TILE_GROOTTE, 3.2, 0.45)
        return Vec3(1.4, 3.2, 1.4)

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
            "WASD = lopen | pijltjes of muis = kijken | klik = deur open | R = opnieuw | Esc = stoppen",
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
        for klikdeur in self.klik_deuren:
            self.zet_klikdeur_open(klikdeur, False)
        self.krampus_pad = []
        self.krampus_pad_doel = None
        self.krampus_pad_timer = 0.0
        self.heeft_sleutel = False
        self.status = "spelen"
        self.tijd_seconden = 0.0
        self.melding = "Zoek de sleutel, klik deuren open en blijf weg van Krampus."
        self.speler.enabled = True
        zet_muis_vergrendeld(True)
        self.werk_tekst_bij()

    def werk_tekst_bij(self):
        """Zet de goede tekst op het scherm."""
        if self.status == "spelen":
            if self.heeft_sleutel:
                opdracht = "Je hebt de sleutel! Ren nu naar de groene deur."
            else:
                opdracht = "Zoek de sleutel, open deuren en blijf weg van Krampus."
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

    def zet_klikdeur_open(self, deur, open_zetten):
        """Zet een klikdeur open of dicht."""
        deur.is_open = open_zetten
        if open_zetten:
            deur.position = deur.open_positie
            deur.scale = deur.open_scale
            deur.color = kleur(90, 180, 120)
            deur.collider = None
        else:
            deur.position = deur.gesloten_positie
            deur.scale = deur.gesloten_scale
            deur.color = kleur(126, 66, 152)
            deur.collider = "box"

    def pak_geraakte_klikdeur(self):
        """Zoek of je naar een dichte deur kijkt."""
        raak = raycast(
            origin=camera.world_position,
            direction=camera.forward,
            distance=DEUR_KLIK_AFSTAND,
            ignore=(self.speler,),
        )
        if raak.hit and raak.entity in self.klik_deuren and not raak.entity.is_open:
            return raak.entity
        return None

    def open_geraakte_klikdeur(self):
        """Open een deur als je erop klikt."""
        deur = self.pak_geraakte_klikdeur()
        if deur is None:
            return
        self.zet_klikdeur_open(deur, True)
        self.krampus_pad = []
        self.krampus_pad_timer = 0.0
        self.melding = "Klik! De deur is open. Pas op: Krampus kan er nu ook door."
        self.werk_tekst_bij()

    def plek_raakt_blok(self, nieuwe_x, nieuwe_z, blok, straal):
        """Kijk of een ronde botsing een blok raakt."""
        halve_blok_x = blok.scale_x / 2
        halve_blok_z = blok.scale_z / 2
        return abs(nieuwe_x - blok.x) < halve_blok_x + straal and abs(nieuwe_z - blok.z) < halve_blok_z + straal

    def krampus_botst_met_muur(self, nieuwe_x, nieuwe_z):
        """Kijk of Krampus op deze plek tegen een muur zou komen."""
        for muur in self.muren:
            if self.plek_raakt_blok(nieuwe_x, nieuwe_z, muur, KRAMPUS_STRAAL):
                return True

        for klikdeur in self.klik_deuren:
            if klikdeur.is_open:
                continue
            if self.plek_raakt_blok(nieuwe_x, nieuwe_z, klikdeur, KRAMPUS_STRAAL):
                return True
        return False

    def tegel_is_beloopbaar(self, kolom, rij):
        """Kijk of Krampus over deze kaartplek mag lopen."""
        if kolom < 0 or rij < 0 or rij >= len(KAART) or kolom >= len(KAART[0]):
            return False

        if KAART[rij][kolom] == "#":
            return False

        klikdeur = self.klikdeur_per_tegel.get((kolom, rij))
        if klikdeur is not None and not klikdeur.is_open:
            return False

        return True

    def maak_krampus_pad(self):
        """Zoek een slim pad door het doolhof."""
        start = wereld_naar_kaart(self.krampus.position)
        doel = wereld_naar_kaart(self.speler.position)
        self.krampus_pad_doel = doel

        if start == doel:
            self.krampus_pad = []
            return

        wachtrij = deque([start])
        vorige_stap = {start: None}

        # Zo vindt Krampus een route door gangen en open deuren.
        while wachtrij:
            huidige = wachtrij.popleft()
            if huidige == doel:
                break

            for verschil_kolom, verschil_rij in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                volgende = (huidige[0] + verschil_kolom, huidige[1] + verschil_rij)
                if volgende in vorige_stap:
                    continue
                if not self.tegel_is_beloopbaar(*volgende) and volgende != doel:
                    continue
                vorige_stap[volgende] = huidige
                wachtrij.append(volgende)

        eind_tegel = doel
        if doel not in vorige_stap:
            # Als Krampus je nog niet kan halen, loopt hij alvast zo dicht mogelijk naar je toe.
            eind_tegel = min(
                vorige_stap,
                key=lambda tegel: abs(tegel[0] - doel[0]) + abs(tegel[1] - doel[1]),
            )

        if eind_tegel == start:
            self.krampus_pad = []
            return

        pad = []
        stap = eind_tegel
        while stap != start:
            pad.append(stap)
            stap = vorige_stap[stap]
        pad.reverse()

        self.krampus_pad = [kaart_naar_wereld(kolom, rij) for kolom, rij in pad]

    def pak_krampus_doelpunt(self):
        """Pak het volgende punt waar Krampus naartoe moet."""
        while self.krampus_pad:
            doelpunt = self.krampus_pad[0]
            if afstand_xz(self.krampus.position, doelpunt) <= KRAMPUS_WEGPUNT_BEREIK:
                self.krampus_pad.pop(0)
                continue
            return doelpunt

        if wereld_naar_kaart(self.krampus.position) == wereld_naar_kaart(self.speler.position):
            return Vec3(self.speler.x, 0, self.speler.z)

        return None

    def beweeg_krampus_stap(self, stap):
        """Beweeg Krampus stap voor stap langs muren."""
        nieuwe_x = self.krampus.x + stap.x
        if not self.krampus_botst_met_muur(nieuwe_x, self.krampus.z):
            self.krampus.x = nieuwe_x

        nieuwe_z = self.krampus.z + stap.z
        if not self.krampus_botst_met_muur(self.krampus.x, nieuwe_z):
            self.krampus.z = nieuwe_z

    def beweeg_krampus(self):
        """Laat Krampus langzaam naar de speler lopen."""
        speler_tegel = wereld_naar_kaart(self.speler.position)
        krampus_tegel = wereld_naar_kaart(self.krampus.position)
        self.krampus_pad_timer -= time.dt

        if self.krampus_pad_timer <= 0 or self.krampus_pad_doel != speler_tegel or (not self.krampus_pad and krampus_tegel != speler_tegel):
            self.maak_krampus_pad()
            self.krampus_pad_timer = KRAMPUS_PAD_INTERVAL

        doelpunt = self.pak_krampus_doelpunt()
        if doelpunt is None:
            self.krampus.look_at_2d(self.speler.position, "y")
            self.krampus.y = math.sin(self.tijd_seconden * 5) * 0.05
            return

        richting = Vec3(
            doelpunt.x - self.krampus.x,
            0,
            doelpunt.z - self.krampus.z,
        )
        if richting.length() <= 0.2:
            return

        snelheid = KRAMPUS_SNELHEID + (0.8 if self.heeft_sleutel else 0)
        stap_lengte = min(snelheid * time.dt, richting.length())
        stap = richting.normalized() * stap_lengte
        oude_positie = Vec3(self.krampus.x, 0, self.krampus.z)
        self.beweeg_krampus_stap(stap)
        nieuwe_positie = Vec3(self.krampus.x, 0, self.krampus.z)
        if afstand_xz(oude_positie, nieuwe_positie) <= 0.01:
            self.krampus_pad = []
            self.krampus_pad_timer = 0.0
        self.krampus.look_at_2d(doelpunt, "y")
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

        # Met de pijltjes kun je ook rondkijken.
        if held_keys["left arrow"]:
            self.speler.rotation_y -= PIJL_DRAAI_SNELHEID * time.dt
        if held_keys["right arrow"]:
            self.speler.rotation_y += PIJL_DRAAI_SNELHEID * time.dt
        if held_keys["up arrow"]:
            self.speler.camera_pivot.rotation_x = max(
                -90,
                self.speler.camera_pivot.rotation_x - PIJL_KIJK_SNELHEID * time.dt,
            )
        if held_keys["down arrow"]:
            self.speler.camera_pivot.rotation_x = min(
                90,
                self.speler.camera_pivot.rotation_x + PIJL_KIJK_SNELHEID * time.dt,
            )

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
        elif toets == "left mouse down" and self.status == "spelen":
            self.open_geraakte_klikdeur()
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
