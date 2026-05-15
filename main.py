"""Krampus3000 - een simpel echt 3D horrorspel."""

from collections import deque
import math

from ursina import (
    AmbientLight,
    Audio,
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
KRAMPUS_SNELHEID = SPELER_SNELHEID
PIJL_DRAAI_SNELHEID = 120
PIJL_KIJK_SNELHEID = 80
KRAMPUS_STRAAL = 0.55
DEUR_KLIK_AFSTAND = 5
KAST_KLIK_AFSTAND = 3
KRAMPUS_PAD_INTERVAL = 0.25
KRAMPUS_WEGPUNT_BEREIK = 0.35
KRAMPUS_DEUR_AFSTAND = 1.35
KRAMPUS_DEUR_AUTO_DICHT_TIJD = 1.6
KRAMPUS_GELUID_AFSTAND = 30
PLAFOND_HOOGTE = 5.95
MUUR_HOOGTE = 6.1
DEUR_HOOGTE = MUUR_HOOGTE
DEUR_GESLOTEN_Y = DEUR_HOOGTE / 2
DEUR_OPEN_HOOGTE = 0.25
DEUR_OPEN_Y = DEUR_OPEN_HOOGTE / 2
KRAMPUS_BASIS_Y = 0.85
KRAMPUS_ZWEEF_HOOGTE = 0.05
TEXTUUR_VLOER = "textures/vloer_hout.ppm"
TEXTUUR_PLAFOND = "textures/plafond_hout.ppm"
TEXTUUR_MUUR = "textures/muur_hout.ppm"
TEXTUUR_DEUR = "textures/deur_oud.ppm"
TEXTUUR_KRAMPUS_VACHT = "textures/krampus_vacht.ppm"
TEXTUUR_KRAMPUS_HUID = "textures/krampus_huid.ppm"

SLEUTEL_INFO = {
    "a": {"deur": "1", "naam": "rode", "kleur": (236, 92, 92)},
    "b": {"deur": "2", "naam": "blauwe", "kleur": (92, 156, 244)},
    "c": {"deur": "3", "naam": "groene", "kleur": (92, 214, 126)},
    "d": {"deur": "4", "naam": "paarse", "kleur": (188, 110, 244)},
    "e": {"deur": "5", "naam": "gouden", "kleur": (244, 208, 96)},
}
DEUR_NAAR_SLEUTEL = {info["deur"]: sleutel_id for sleutel_id, info in SLEUTEL_INFO.items()}


def kleur(rood, groen, blauw, alpha=1.0):
    """Maak een Ursina-kleur met gewone 0-255 getallen."""
    echte_alpha = alpha if alpha <= 1 else alpha / 255
    return color.rgba(rood / 255, groen / 255, blauw / 255, echte_alpha)


def maak_kaart():
    """Maak een veel grotere kaart met deuren, sleutels en kasten."""
    breedte = 43
    hoogte = 21
    kaart = []

    for rij in range(hoogte):
        nieuwe_rij = []
        for kolom in range(breedte):
            if kolom in (0, breedte - 1) or rij in (0, hoogte - 1):
                nieuwe_rij.append("#")
            else:
                nieuwe_rij.append(".")
        kaart.append(nieuwe_rij)

    for kolom in (8, 16, 24, 32):
        for rij in range(1, hoogte - 1):
            kaart[rij][kolom] = "#"

    for rij in (5, 10, 15):
        for kolom in range(1, breedte - 1):
            kaart[rij][kolom] = "#"

    openingen = {
        (8, 2): "O",
        (8, 8): ".",
        (8, 12): "O",
        (8, 17): ".",
        (16, 3): ".",
        (16, 8): "2",
        (16, 13): "O",
        (16, 18): ".",
        (24, 2): "O",
        (24, 8): ".",
        (24, 12): "O",
        (24, 17): ".",
        (32, 3): "O",
        (32, 8): ".",
        (32, 13): "4",
        (32, 18): "O",
        (4, 5): "O",
        (12, 5): "1",
        (20, 5): "O",
        (28, 5): "O",
        (36, 5): ".",
        (6, 10): "O",
        (14, 10): ".",
        (22, 10): "3",
        (30, 10): "O",
        (38, 10): "O",
        (4, 15): ".",
        (12, 15): "O",
        (20, 15): "5",
        (28, 15): ".",
        (36, 15): "O",
    }

    plaatsingen = {
        (2, 2): "S",
        (40, 2): "D",
        (40, 18): "M",
        (3, 2): "a",
        (19, 2): "b",
        (6, 12): "c",
        (27, 12): "d",
        (19, 18): "e",
        (5, 3): "C",
        (11, 7): "C",
        (27, 3): "C",
        (35, 7): "C",
        (3, 13): "C",
        (27, 18): "C",
        (36, 18): "C",
    }

    for plek, teken in openingen.items():
        kaart[plek[1]][plek[0]] = teken

    for plek, teken in plaatsingen.items():
        kaart[plek[1]][plek[0]] = teken

    return ["".join(rij) for rij in kaart]


KAART = maak_kaart()


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
        self.deur_plek = Vec3(0, DEUR_GESLOTEN_Y, 0)
        self.slot_sleutel_plekken = {}
        self.kast_plekken = []
        self.klik_deuren = []
        self.slot_deuren = []
        self.kasten = []
        self.muren = []
        self.klikdeur_per_tegel = {}
        self.slotdeur_per_tegel = {}
        self.sleutels = []
        self.sleutel_per_id = {}
        self.beste_tijd = None
        self.tijd_seconden = 0.0
        self.status = "spelen"
        self.heeft_sleutel = False
        self.melding = ""
        self.gevonden_sleutels = set()
        self.verstopt_in_kast = False
        self.actieve_kast = None
        self.verstop_terug_plek = None
        self.krampus_pad = []
        self.krampus_pad_doel = None
        self.krampus_pad_timer = 0.0
        self.krampus_laatste_speler_plek = None
        self.krampus_vlucht_plek = None
        self.krampus_stap_geluid = None
        self.krampus_stap_timer = 0.0
        self.krampus_beweegt = False

        self.maak_wereld()
        self.maak_speler()
        self.maak_krampus()
        self.maak_sleutels()
        self.maak_kasten()
        self.maak_ui()
        self.maak_geluiden()
        self.reset_spel()

    def maak_wereld(self):
        """Bouw de 3D kamer, muren en deuren."""
        vloer_breedte = len(KAART[0]) * TILE_GROOTTE
        vloer_diepte = len(KAART) * TILE_GROOTTE

        # Een donkere luchtbol maakt het spel meteen enger.
        self.lucht = Entity(
            model="sphere",
            scale=220,
            double_sided=True,
            color=kleur(18, 10, 16),
        )
        self.vloer = Entity(
            model="plane",
            scale=(vloer_breedte + 10, 1, vloer_diepte + 10),
            texture=TEXTUUR_VLOER,
            texture_scale=(8, 8),
            color=kleur(214, 196, 178),
            collider="box",
        )
        self.plafond = Entity(
            model="plane",
            scale=(vloer_breedte + 10, 1, vloer_diepte + 10),
            position=(0, PLAFOND_HOOGTE, 0),
            rotation=(180, 0, 0),
            texture=TEXTUUR_PLAFOND,
            texture_scale=(7, 7),
            color=kleur(180, 155, 135),
            double_sided=True,
        )

        self.muren = []
        self.klik_deuren = []
        self.slot_deuren = []
        self.kasten = []
        self.klikdeur_per_tegel = {}
        self.slotdeur_per_tegel = {}
        self.slot_sleutel_plekken = {}
        self.kast_plekken = []

        for rij, regel in enumerate(KAART):
            for kolom, teken in enumerate(regel):
                plek = kaart_naar_wereld(kolom, rij)

                if teken == "#":
                    muur = Entity(
                        model="cube",
                        position=(plek.x, MUUR_HOOGTE / 2, plek.z),
                        scale=(TILE_GROOTTE, MUUR_HOOGTE, TILE_GROOTTE),
                        texture=TEXTUUR_MUUR,
                        texture_scale=(1.35, 0.9),
                        color=kleur(150, 126, 102),
                        collider="box",
                    )
                    self.muren.append(muur)
                elif teken == "S":
                    self.speler_start = Vec3(plek.x, 1.5, plek.z)
                elif teken == "M":
                    self.krampus_start = Vec3(plek.x, KRAMPUS_BASIS_Y, plek.z)
                elif teken == "D":
                    self.deur_plek = Vec3(plek.x, DEUR_GESLOTEN_Y, plek.z)
                elif teken == "O":
                    self.maak_klikdeur(kolom, rij, plek)
                elif teken in "12345":
                    self.maak_slotdeur(teken, kolom, rij, plek)
                elif teken in SLEUTEL_INFO:
                    self.slot_sleutel_plekken[teken] = Vec3(plek.x, 1.0, plek.z)
                elif teken == "C":
                    self.kast_plekken.append(Vec3(plek.x, 1.35, plek.z))

        self.deur = Entity(
            model="cube",
            position=self.deur_plek,
            scale=(2.2, DEUR_HOOGTE, 0.45),
            texture=TEXTUUR_DEUR,
            texture_scale=(1.4, 1.2),
            color=kleur(112, 86, 62),
            collider="box",
        )
        self.maak_deur_details(self.deur, accent_kleur=(180, 164, 128))
        self.deur_glans = Entity(
            parent=self.deur,
            model="cube",
            scale=(0.05, 0.22, 1.04),
            x=0.78,
            y=0.05,
            color=kleur(205, 182, 150, 95),
        )

        # Licht maakt de kamer beter zichtbaar maar nog steeds spannend.
        self.ambient_licht = AmbientLight(color=kleur(108, 96, 78, 0.48))
        self.richting_licht = DirectionalLight(color=kleur(250, 205, 150, 0.14))
        self.richting_licht.look_at(Vec3(1, -2, -1))

    def maak_deur_details(self, deur, accent_kleur=None):
        """Geef een deur oude houten details."""
        frame_y = deur.scale_y / 2 - 0.18
        accent_hoogte = max(0.4, deur.scale_y - 0.75)
        deur.frame_boven = Entity(
            parent=deur,
            model="cube",
            position=(0, frame_y, 0),
            scale=(1.02, 0.1, 1.04),
            color=kleur(70, 48, 31),
        )
        deur.frame_onder = Entity(
            parent=deur,
            model="cube",
            position=(0, -frame_y, 0),
            scale=(1.02, 0.1, 1.04),
            color=kleur(70, 48, 31),
        )
        deur.handvat = Entity(
            parent=deur,
            model="cube",
            position=(0.34, 0.02, 0.26),
            scale=(0.06, 0.22, 0.08),
            color=kleur(165, 140, 104),
        )
        deur.accent = Entity(
            parent=deur,
            model="cube",
            position=(-0.33, 0, 0.24),
            scale=(0.06, accent_hoogte, 0.05),
            color=kleur(78, 58, 38),
        )
        if accent_kleur is None:
            deur.accent.visible = False
        else:
            deur.accent.visible = True
            deur.accent.color = kleur(accent_kleur[0], accent_kleur[1], accent_kleur[2], 210)

    def maak_klikdeur(self, kolom, rij, plek):
        """Maak een gewone deur die je met een klik kunt openen."""
        schaal = self.bepaal_deur_schaal(kolom, rij)
        deur = Entity(
            model="cube",
            position=(plek.x, DEUR_GESLOTEN_Y, plek.z),
            scale=schaal,
            texture=TEXTUUR_DEUR,
            texture_scale=(1.3, 1.15),
            color=kleur(108, 82, 58),
            collider="box",
        )
        self.maak_deur_details(deur)
        deur.gesloten_positie = Vec3(plek.x, DEUR_GESLOTEN_Y, plek.z)
        deur.gesloten_scale = Vec3(schaal.x, schaal.y, schaal.z)
        deur.open_positie = Vec3(plek.x, DEUR_OPEN_Y, plek.z)
        deur.open_scale = Vec3(schaal.x, DEUR_OPEN_HOOGTE, schaal.z)
        deur.is_open = False
        deur.krampus_auto_dicht_timer = 0.0
        deur.krampus_opende_deur = False
        deur.kaart_kolom = kolom
        deur.kaart_rij = rij
        self.klik_deuren.append(deur)
        self.klikdeur_per_tegel[(kolom, rij)] = deur

    def maak_slotdeur(self, deur_teken, kolom, rij, plek):
        """Maak een deur die een speciale sleutel nodig heeft."""
        schaal = self.bepaal_deur_schaal(kolom, rij)
        sleutel_id = DEUR_NAAR_SLEUTEL[deur_teken]
        basis_kleur = SLEUTEL_INFO[sleutel_id]["kleur"]
        deur = Entity(
            model="cube",
            position=(plek.x, DEUR_GESLOTEN_Y, plek.z),
            scale=schaal,
            texture=TEXTUUR_DEUR,
            texture_scale=(1.3, 1.15),
            color=kleur(104, 78, 56),
            collider="box",
        )
        self.maak_deur_details(
            deur,
            accent_kleur=(
                min(255, basis_kleur[0] + 8),
                min(255, basis_kleur[1] + 8),
                min(255, basis_kleur[2] + 8),
            ),
        )
        deur.gesloten_positie = Vec3(plek.x, DEUR_GESLOTEN_Y, plek.z)
        deur.gesloten_scale = Vec3(schaal.x, schaal.y, schaal.z)
        deur.open_positie = Vec3(plek.x, DEUR_OPEN_Y, plek.z)
        deur.open_scale = Vec3(schaal.x, DEUR_OPEN_HOOGTE, schaal.z)
        deur.is_open = False
        deur.krampus_auto_dicht_timer = 0.0
        deur.krampus_opende_deur = False
        deur.sleutel_id = sleutel_id
        deur.deur_teken = deur_teken
        deur.kaart_kolom = kolom
        deur.kaart_rij = rij
        self.slot_deuren.append(deur)
        self.slotdeur_per_tegel[(kolom, rij)] = deur

    def bepaal_deur_schaal(self, kolom, rij):
        """Kies hoe de deur moet staan in de gang."""
        links_blok = KAART[rij][kolom - 1] == "#"
        rechts_blok = KAART[rij][kolom + 1] == "#"
        boven_blok = KAART[rij - 1][kolom] == "#"
        onder_blok = KAART[rij + 1][kolom] == "#"

        if boven_blok and onder_blok:
            return Vec3(0.45, DEUR_HOOGTE, TILE_GROOTTE)
        if links_blok and rechts_blok:
            return Vec3(TILE_GROOTTE, DEUR_HOOGTE, 0.45)
        return Vec3(1.4, DEUR_HOOGTE, 1.4)

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
        """Maak Krampus realistischer met donkere vacht en een enge kop."""
        self.krampus = Entity(position=self.krampus_start)
        vacht_donker = kleur(36, 24, 20)
        vacht_licht = kleur(62, 44, 34)
        huid_donker = kleur(84, 50, 40)
        bot_kleur = kleur(218, 200, 176)
        oor_hand_kleur = kleur(34, 22, 16)
        hoorn_kleur = kleur(198, 180, 158)

        self.krampus_lijf = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 1.45, 0.02),
            scale=(1.26, 2.25, 1.04),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.2, 1.8),
            color=vacht_donker,
        )
        self.krampus_buik = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 1.12, 0.24),
            scale=(0.94, 1.16, 0.72),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.0, 1.2),
            color=vacht_licht,
        )
        self.krampus_rug = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 1.74, -0.24),
            scale=(1.12, 0.98, 0.9),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.0, 1.0),
            color=vacht_donker,
        )

        self.krampus_arm_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.78, 1.22, 0.06),
            rotation=(10, 0, 16),
            scale=(0.28, 1.72, 0.3),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(0.6, 1.7),
            color=vacht_donker,
        )
        self.krampus_arm_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.78, 1.22, 0.06),
            rotation=(10, 0, -16),
            scale=(0.28, 1.72, 0.3),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(0.6, 1.7),
            color=vacht_donker,
        )
        self.krampus_klauw_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.86, 0.22, 0.18),
            rotation=(22, 0, 0),
            scale=(0.2, 0.38, 0.14),
            color=oor_hand_kleur,
        )
        self.krampus_klauw_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.86, 0.22, 0.18),
            rotation=(22, 0, 0),
            scale=(0.2, 0.38, 0.14),
            color=oor_hand_kleur,
        )

        self.krampus_been_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.3, 0.16, -0.02),
            rotation=(0, 0, 7),
            scale=(0.36, 1.46, 0.38),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(0.65, 1.4),
            color=vacht_donker,
        )
        self.krampus_been_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.3, 0.16, -0.02),
            rotation=(0, 0, -7),
            scale=(0.36, 1.46, 0.38),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(0.65, 1.4),
            color=vacht_donker,
        )
        self.krampus_hoef_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.3, -0.7, 0.2),
            rotation=(0, 0, 3),
            scale=(0.3, 0.18, 0.46),
            color=bot_kleur,
        )
        self.krampus_hoef_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.3, -0.7, 0.2),
            rotation=(0, 0, -3),
            scale=(0.3, 0.18, 0.46),
            color=bot_kleur,
        )

        self.krampus_nek = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 2.34, 0.02),
            scale=(0.58, 0.48, 0.5),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.0, 1.0),
            color=vacht_donker,
        )
        self.krampus_kop = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 2.72, 0.12),
            scale=(1.0, 1.12, 1.06),
            texture=TEXTUUR_KRAMPUS_HUID,
            texture_scale=(1.0, 1.0),
            color=huid_donker,
        )
        self.krampus_voorhoofd_vacht = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 2.92, 0.02),
            scale=(0.78, 0.42, 0.62),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.0, 1.0),
            color=vacht_donker,
        )
        self.krampus_snuit = Entity(
            parent=self.krampus,
            model="cube",
            position=(0, 2.52, 0.74),
            scale=(0.48, 0.38, 0.82),
            texture=TEXTUUR_KRAMPUS_HUID,
            texture_scale=(1.0, 1.2),
            color=kleur(78, 50, 42),
        )
        self.krampus_kaak = Entity(
            parent=self.krampus,
            model="cube",
            position=(0, 2.3, 0.6),
            rotation=(10, 0, 0),
            scale=(0.44, 0.18, 0.64),
            texture=TEXTUUR_KRAMPUS_HUID,
            texture_scale=(1.0, 1.0),
            color=kleur(68, 42, 34),
        )
        self.krampus_neus = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0, 2.48, 1.1),
            scale=(0.22, 0.16, 0.16),
            color=kleur(18, 14, 14),
        )
        self.krampus_oor_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.48, 2.84, 0.1),
            rotation=(18, 0, 34),
            scale=(0.12, 0.34, 0.08),
            color=oor_hand_kleur,
        )
        self.krampus_oor_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.48, 2.84, 0.1),
            rotation=(18, 0, -34),
            scale=(0.12, 0.34, 0.08),
            color=oor_hand_kleur,
        )
        def maak_hoorn(richting):
            hoorn_stukken = [
                (0.27, 3.02, 0.10, (0.26, 0.28, 0.26)),
                (0.28, 3.14, 0.08, (0.22, 0.24, 0.22)),
                (0.29, 3.26, 0.05, (0.2, 0.2, 0.2)),
                (0.3, 3.38, 0.01, (0.18, 0.18, 0.18)),
                (0.32, 3.49, -0.03, (0.16, 0.16, 0.16)),
                (0.34, 3.59, -0.06, (0.14, 0.14, 0.14)),
                (0.36, 3.68, -0.09, (0.12, 0.12, 0.12)),
                (0.38, 3.76, -0.12, (0.1, 0.1, 0.1)),
            ]

            for x, y, z, schaal in hoorn_stukken:
                Entity(
                    parent=self.krampus,
                    model="sphere",
                    position=(richting * x, y, z),
                    scale=schaal,
                    color=hoorn_kleur,
                )

            for x, y, z, schaal in (
                (0.39, 3.82, -0.14, (0.09, 0.09, 0.09)),
                (0.4, 3.89, -0.17, (0.075, 0.075, 0.075)),
                (0.41, 3.95, -0.2, (0.06, 0.06, 0.06)),
            ):
                Entity(
                    parent=self.krampus,
                    model="sphere",
                    position=(richting * x, y, z),
                    scale=schaal,
                    color=hoorn_kleur,
                )

        maak_hoorn(-1)
        maak_hoorn(1)
        self.krampus_oog_links = Entity(
            parent=self.krampus,
            model="sphere",
            position=(-0.19, 2.72, 0.56),
            scale=0.13,
            color=kleur(255, 102, 42),
        )
        self.krampus_oog_rechts = Entity(
            parent=self.krampus,
            model="sphere",
            position=(0.19, 2.72, 0.56),
            scale=0.13,
            color=kleur(255, 102, 42),
        )
        self.krampus_wenkbrauw_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.21, 2.9, 0.42),
            rotation=(0, 0, 20),
            scale=(0.26, 0.08, 0.12),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.0, 1.0),
            color=vacht_donker,
        )
        self.krampus_wenkbrauw_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.21, 2.9, 0.42),
            rotation=(0, 0, -20),
            scale=(0.26, 0.08, 0.12),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(1.0, 1.0),
            color=vacht_donker,
        )
        self.krampus_baard = Entity(
            parent=self.krampus,
            model="cube",
            position=(0, 2.0, 0.44),
            rotation=(22, 0, 0),
            scale=(0.42, 1.02, 0.18),
            texture=TEXTUUR_KRAMPUS_VACHT,
            texture_scale=(0.8, 1.8),
            color=vacht_donker,
        )
        self.krampus_tong = Entity(
            parent=self.krampus,
            model="cube",
            position=(0, 2.16, 0.88),
            rotation=(34, 0, 0),
            scale=(0.12, 0.6, 0.08),
            color=kleur(154, 34, 38),
        )
        self.krampus_tand_links = Entity(
            parent=self.krampus,
            model="cube",
            position=(-0.14, 2.28, 0.82),
            rotation=(24, 0, 0),
            scale=(0.06, 0.22, 0.06),
            color=bot_kleur,
        )
        self.krampus_tand_rechts = Entity(
            parent=self.krampus,
            model="cube",
            position=(0.14, 2.28, 0.82),
            rotation=(24, 0, 0),
            scale=(0.06, 0.22, 0.06),
            color=bot_kleur,
        )

    def maak_sleutels(self):
        """Maak alle speciale sleutels."""
        self.sleutels = []
        self.sleutel_per_id = {}

        for sleutel_id in sorted(self.slot_sleutel_plekken):
            plek = self.slot_sleutel_plekken[sleutel_id]
            sleutel_kleur = SLEUTEL_INFO[sleutel_id]["kleur"]
            sleutel = Entity(
                model="cube",
                position=plek,
                scale=(0.28, 0.16, 0.95),
                color=kleur(sleutel_kleur[0], sleutel_kleur[1], sleutel_kleur[2]),
            )
            sleutel.sleutel_id = sleutel_id
            sleutel.start_positie = Vec3(plek.x, plek.y, plek.z)
            Entity(
                parent=sleutel,
                model="sphere",
                x=-0.36,
                scale=(0.48, 0.48, 0.12),
                color=kleur(255, 240, 190),
            )
            self.sleutels.append(sleutel)
            self.sleutel_per_id[sleutel_id] = sleutel

    def maak_kasten(self):
        """Maak kasten waar je je in kunt verstoppen."""
        self.kasten = []

        for plek in self.kast_plekken:
            kast = Entity(
                model="cube",
                position=(plek.x, plek.y, plek.z),
                scale=(1.55, 2.7, 1.25),
                color=kleur(96, 70, 46),
                collider="box",
            )
            kast.normale_collider = "box"
            kast.verstop_plek = Vec3(plek.x, 1.5, plek.z)
            Entity(
                parent=kast,
                model="cube",
                position=(0.38, 0, 0.58),
                scale=(0.04, 0.3, 0.04),
                color=kleur(220, 188, 120),
            )
            self.kasten.append(kast)

    def maak_ui(self):
        """Maak alle tekst op het scherm."""
        self.titel_tekst = Text("Krampus3000", x=-0.85, y=0.45, scale=2.1, color=kleur(255, 245, 250))
        self.status_tekst = Text("", x=-0.85, y=0.38, scale=1.1, color=kleur(240, 230, 240))
        self.sleutel_tekst = Text("", x=-0.85, y=0.32, scale=0.95, color=kleur(255, 226, 160))
        self.tijd_tekst = Text("", x=-0.85, y=0.26, scale=0.95, color=kleur(190, 175, 195))
        self.beste_tijd_tekst = Text("", x=-0.45, y=0.26, scale=0.95, color=kleur(190, 175, 195))
        self.hint_tekst = Text("", x=-0.85, y=0.20, scale=0.9, color=kleur(210, 190, 210))
        self.besturing_tekst = Text(
            "WASD = lopen | pijltjes of muis = kijken | klik = deur of kast | R = opnieuw | Esc = stoppen",
            x=-0.85,
            y=-0.46,
            scale=0.82,
            color=kleur(200, 180, 200),
        )

    def maak_geluiden(self):
        """Maak de geluiden van het spel."""
        self.krampus_stap_geluid = Audio("krampus_step.wav", autoplay=False, auto_destroy=False)
        self.krampus_stap_geluid.volume = 0

    def reset_spel(self):
        """Begin opnieuw met een nieuw rondje."""
        if self.actieve_kast is not None:
            self.actieve_kast.collider = self.actieve_kast.normale_collider

        self.speler.position = self.speler_start
        self.speler.rotation = (0, 0, 0)
        self.speler.camera_pivot.rotation = (0, 0, 0)
        self.speler.speed = SPELER_SNELHEID
        self.krampus.position = Vec3(self.krampus_start.x, KRAMPUS_BASIS_Y, self.krampus_start.z)
        self.krampus.rotation_y = 0
        self.gevonden_sleutels = set()
        self.verstopt_in_kast = False
        self.actieve_kast = None
        self.verstop_terug_plek = None

        for sleutel in self.sleutels:
            sleutel.position = sleutel.start_positie
            sleutel.enabled = True

        for klikdeur in self.klik_deuren:
            self.zet_klikdeur_open(klikdeur, False)
        for slotdeur in self.slot_deuren:
            self.zet_slotdeur_open(slotdeur, False)

        self.krampus_pad = []
        self.krampus_pad_doel = None
        self.krampus_pad_timer = 0.0
        self.krampus_laatste_speler_plek = Vec3(self.speler.x, 0, self.speler.z)
        self.krampus_vlucht_plek = None
        self.krampus_stap_timer = 0.0
        self.krampus_beweegt = False
        self.heeft_sleutel = False
        self.status = "spelen"
        self.tijd_seconden = 0.0
        self.melding = "Zoek 5 sleutels, open deuren en verstop je in een kast."
        self.speler.enabled = True
        self.krampus_stap_geluid.stop(destroy=False)
        zet_muis_vergrendeld(True)
        self.werk_uitgang_bij()
        self.werk_tekst_bij()

    def zet_krampus_hoogte(self):
        """Houd Krampus boven de vloer met een klein zweefje."""
        self.krampus.y = KRAMPUS_BASIS_Y + math.sin(self.tijd_seconden * 5) * KRAMPUS_ZWEEF_HOOGTE

    def werk_uitgang_bij(self):
        """Laat de uitgang zien als alle sleutels binnen zijn."""
        self.heeft_sleutel = len(self.gevonden_sleutels) == len(SLEUTEL_INFO)
        if self.heeft_sleutel:
            self.deur.color = kleur(130, 102, 74)
            self.deur.accent.color = kleur(186, 174, 130, 220)
            self.deur_glans.color = kleur(225, 214, 182, 145)
        else:
            self.deur.color = kleur(112, 86, 62)
            self.deur.accent.color = kleur(132, 114, 86, 200)
            self.deur_glans.color = kleur(205, 182, 150, 95)

    def werk_tekst_bij(self):
        """Zet de goede tekst op het scherm."""
        gevonden = len(self.gevonden_sleutels)
        totaal = len(SLEUTEL_INFO)

        if self.status == "spelen":
            if self.verstopt_in_kast:
                opdracht = "Je zit verstopt in een kast. Klik om eruit te komen."
            elif self.heeft_sleutel:
                opdracht = "Je hebt alle 5 sleutels! Ren nu naar de groene deur."
            else:
                opdracht = "Zoek de sleutels, open deuren en blijf weg van Krampus."
        elif self.status == "gewonnen":
            opdracht = "Je bent ontsnapt! Druk op R voor nog een potje."
        else:
            opdracht = "Krampus heeft je gepakt... Druk op R om opnieuw te beginnen."

        self.status_tekst.text = opdracht
        self.sleutel_tekst.text = f"Sleutels: {gevonden}/{totaal}"
        self.tijd_tekst.text = f"Tijd: {self.tijd_seconden:.1f} sec"
        if self.beste_tijd is None:
            self.beste_tijd_tekst.text = "Beste tijd: -"
        else:
            self.beste_tijd_tekst.text = f"Beste tijd: {self.beste_tijd:.1f} sec"
        self.hint_tekst.text = self.melding

    def pak_sleutel(self, sleutel):
        """Pak een sleutel op."""
        if not sleutel.enabled:
            return

        sleutel.enabled = False
        self.gevonden_sleutels.add(sleutel.sleutel_id)
        self.werk_uitgang_bij()

        info = SLEUTEL_INFO[sleutel.sleutel_id]
        if self.heeft_sleutel:
            self.melding = "Je hebt alle 5 sleutels! De uitgang is nu open."
        else:
            self.melding = f"Je vond de {info['naam']} sleutel voor deur {info['deur']}."
        self.werk_tekst_bij()

    def win_spel(self):
        """Laat zien dat je gewonnen hebt."""
        self.status = "gewonnen"
        self.speler.enabled = False
        self.krampus_stap_geluid.stop(destroy=False)
        zet_muis_vergrendeld(False)
        if self.beste_tijd is None or self.tijd_seconden < self.beste_tijd:
            self.beste_tijd = self.tijd_seconden
        self.melding = "Krampus was te laat. Jij hebt gewonnen!"
        self.werk_tekst_bij()

    def verlies_spel(self):
        """Laat zien dat je verloren hebt."""
        self.status = "verloren"
        self.speler.enabled = False
        self.krampus_stap_geluid.stop(destroy=False)
        zet_muis_vergrendeld(False)
        self.melding = "Ai! Krampus greep je te pakken."
        self.werk_tekst_bij()

    def zet_klikdeur_open(self, deur, open_zetten):
        """Zet een gewone klikdeur open of dicht."""
        deur.is_open = open_zetten
        if open_zetten:
            deur.position = deur.open_positie
            deur.scale = deur.open_scale
            deur.color = kleur(128, 100, 72)
            deur.collider = None
        else:
            deur.position = deur.gesloten_positie
            deur.scale = deur.gesloten_scale
            deur.color = kleur(108, 82, 58)
            deur.collider = "box"
        if not open_zetten:
            deur.krampus_auto_dicht_timer = 0.0
            deur.krampus_opende_deur = False

    def zet_slotdeur_open(self, deur, open_zetten):
        """Zet een slotdeur open of dicht."""
        basis_kleur = SLEUTEL_INFO[deur.sleutel_id]["kleur"]
        deur.is_open = open_zetten
        if open_zetten:
            deur.position = deur.open_positie
            deur.scale = deur.open_scale
            deur.color = kleur(130, 102, 74)
            deur.collider = None
            deur.accent.color = kleur(basis_kleur[0], basis_kleur[1], basis_kleur[2], 210)
        else:
            deur.position = deur.gesloten_positie
            deur.scale = deur.gesloten_scale
            if deur.sleutel_id in self.gevonden_sleutels:
                deur.color = kleur(104, 78, 56)
                deur.accent.color = kleur(basis_kleur[0], basis_kleur[1], basis_kleur[2], 210)
            else:
                deur.color = kleur(90, 68, 48)
                deur.accent.color = kleur(
                    max(50, basis_kleur[0] - 110),
                    max(50, basis_kleur[1] - 110),
                    max(50, basis_kleur[2] - 110),
                    170,
                )
            deur.collider = "box"
        if not open_zetten:
            deur.krampus_auto_dicht_timer = 0.0
            deur.krampus_opende_deur = False

    def pak_geraakt_object(self):
        """Zoek waar de speler nu naar kijkt."""
        raak = raycast(
            origin=camera.world_position,
            direction=camera.forward,
            distance=DEUR_KLIK_AFSTAND,
            ignore=(self.speler,),
        )
        if raak.hit:
            return raak.entity
        return None

    def ga_in_kast(self, kast):
        """Verstop de speler in een kast."""
        if afstand_xz(self.speler.position, kast.position) > KAST_KLIK_AFSTAND:
            self.melding = "Loop dichter naar de kast om je te verstoppen."
            self.werk_tekst_bij()
            return

        self.verstopt_in_kast = True
        self.actieve_kast = kast
        self.verstop_terug_plek = Vec3(self.speler.x, 1.5, self.speler.z)
        self.krampus_laatste_speler_plek = Vec3(self.speler.x, 0, self.speler.z)
        kast.collider = None
        self.speler.speed = 0
        self.speler.position = kast.verstop_plek
        self.krampus_pad = []
        self.krampus_pad_timer = 0.0
        self.krampus_vlucht_plek = None
        self.melding = "Je zit verstopt in de kast. Krampus loopt nu weg."
        self.werk_tekst_bij()

    def verlaat_kast(self):
        """Laat de speler weer uit de kast stappen."""
        if not self.verstopt_in_kast:
            return

        if self.actieve_kast is not None:
            self.actieve_kast.collider = self.actieve_kast.normale_collider

        if self.verstop_terug_plek is not None:
            self.speler.position = self.verstop_terug_plek
        self.speler.speed = SPELER_SNELHEID
        self.verstopt_in_kast = False
        self.actieve_kast = None
        self.verstop_terug_plek = None
        self.krampus_laatste_speler_plek = Vec3(self.speler.x, 0, self.speler.z)
        self.krampus_vlucht_plek = None
        self.melding = "Je bent weer uit de kast."
        self.werk_tekst_bij()

    def gebruik_interactie(self):
        """Doe iets met deuren of een kast."""
        if self.verstopt_in_kast:
            self.verlaat_kast()
            return

        doel = self.pak_geraakt_object()
        if doel is None:
            return

        if doel in self.kasten:
            self.ga_in_kast(doel)
            return

        if doel in self.klik_deuren and not doel.is_open:
            self.zet_klikdeur_open(doel, True)
            self.krampus_pad = []
            self.krampus_pad_timer = 0.0
            self.melding = "Klik! De gewone deur is open."
            self.werk_tekst_bij()
            return

        if doel in self.slot_deuren and not doel.is_open:
            if doel.sleutel_id in self.gevonden_sleutels:
                self.zet_slotdeur_open(doel, True)
                self.melding = f"Deur {doel.deur_teken} gaat open."
            else:
                info = SLEUTEL_INFO[doel.sleutel_id]
                self.melding = f"Voor deur {doel.deur_teken} heb je de {info['naam']} sleutel nodig."
            self.werk_tekst_bij()

    def plek_raakt_blok(self, nieuwe_x, nieuwe_z, blok, straal):
        """Kijk of een ronde botsing een blok raakt."""
        halve_blok_x = blok.scale_x / 2
        halve_blok_z = blok.scale_z / 2
        return abs(nieuwe_x - blok.x) < halve_blok_x + straal and abs(nieuwe_z - blok.z) < halve_blok_z + straal

    def krampus_botst_met_muur(self, nieuwe_x, nieuwe_z):
        """Kijk of Krampus op deze plek tegen een muur of gewone deur zou komen."""
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

        return True

    def pak_verste_loopplek_van(self, start_plek):
        """Zoek een verre plek zodat Krampus van de kast wegloopt."""
        speler_tegel = wereld_naar_kaart(start_plek)
        krampus_tegel = wereld_naar_kaart(self.krampus.position)
        wachtrij = deque([krampus_tegel])
        vorige_stap = {krampus_tegel: None}
        beste_tegel = None
        beste_score = (-1, -1)

        # Zo kiest Krampus een pad dat meteen van de kast af beweegt.
        while wachtrij:
            huidige = wachtrij.popleft()

            for verschil_kolom, verschil_rij in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                volgende = (huidige[0] + verschil_kolom, huidige[1] + verschil_rij)
                if volgende in vorige_stap:
                    continue
                if not self.tegel_is_beloopbaar(*volgende):
                    continue
                vorige_stap[volgende] = huidige
                wachtrij.append(volgende)

        for tegel in vorige_stap:
            if tegel == krampus_tegel:
                continue

            eerste_stap = tegel
            while vorige_stap[eerste_stap] != krampus_tegel:
                eerste_stap = vorige_stap[eerste_stap]

            eerste_score = abs(eerste_stap[0] - speler_tegel[0]) + abs(eerste_stap[1] - speler_tegel[1])
            totale_score = abs(tegel[0] - speler_tegel[0]) + abs(tegel[1] - speler_tegel[1])
            score = (eerste_score, totale_score)
            if score > beste_score:
                beste_score = score
                beste_tegel = tegel

        if beste_tegel is None:
            return None
        return kaart_naar_wereld(beste_tegel[0], beste_tegel[1])

    def open_deur_voor_krampus(self, deur):
        """Laat een deur voor Krampus even open gaan."""
        if deur in self.klik_deuren:
            self.zet_klikdeur_open(deur, True)
        else:
            self.zet_slotdeur_open(deur, True)

        deur.krampus_opende_deur = True
        deur.krampus_auto_dicht_timer = KRAMPUS_DEUR_AUTO_DICHT_TIJD

    def open_deuren_bij_krampus(self, nieuwe_x, nieuwe_z):
        """Open deuren waar Krampus bijna tegenaan loopt."""
        for deur in self.klik_deuren + self.slot_deuren:
            if deur.is_open:
                continue
            if self.plek_raakt_blok(nieuwe_x, nieuwe_z, deur, KRAMPUS_DEUR_AFSTAND):
                self.open_deur_voor_krampus(deur)

    def werk_krampus_deuren_bij(self):
        """Laat deuren achter Krampus weer dichtgaan."""
        for deur in self.klik_deuren + self.slot_deuren:
            if not deur.krampus_opende_deur:
                continue

            deur.krampus_auto_dicht_timer -= time.dt
            if deur.krampus_auto_dicht_timer > 0:
                continue

            if afstand_xz(self.krampus.position, deur.position) < 1.8:
                deur.krampus_auto_dicht_timer = 0.2
                continue

            if not self.verstopt_in_kast and afstand_xz(self.speler.position, deur.position) < 1.8:
                deur.krampus_auto_dicht_timer = 0.2
                continue

            if deur in self.klik_deuren:
                self.zet_klikdeur_open(deur, False)
            else:
                self.zet_slotdeur_open(deur, False)

    def maak_krampus_pad(self, doel_plek):
        """Zoek een slim pad door het doolhof."""
        if doel_plek is None:
            self.krampus_pad = []
            self.krampus_pad_doel = None
            return

        start = wereld_naar_kaart(self.krampus.position)
        doel = wereld_naar_kaart(doel_plek)
        self.krampus_pad_doel = doel

        if start == doel:
            self.krampus_pad = []
            return

        wachtrij = deque([start])
        vorige_stap = {start: None}

        # Zo vindt Krampus een route door gangen en gewone deuren.
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

    def pak_krampus_doelpunt(self, doel_plek):
        """Pak het volgende punt waar Krampus naartoe moet."""
        while self.krampus_pad:
            doelpunt = self.krampus_pad[0]
            if afstand_xz(self.krampus.position, doelpunt) <= KRAMPUS_WEGPUNT_BEREIK:
                self.krampus_pad.pop(0)
                continue
            return doelpunt

        if doel_plek is not None and wereld_naar_kaart(self.krampus.position) == wereld_naar_kaart(doel_plek):
            return Vec3(doel_plek.x, 0, doel_plek.z)

        return None

    def pak_krampus_jacht_plek(self):
        """Bepaal waar Krampus de speler denkt te vinden."""
        if self.verstopt_in_kast:
            if self.krampus_laatste_speler_plek is None:
                return None

            if self.krampus_vlucht_plek is None:
                self.krampus_vlucht_plek = self.pak_verste_loopplek_van(self.krampus_laatste_speler_plek)

            if self.krampus_vlucht_plek is None:
                return None
            if afstand_xz(self.krampus.position, self.krampus_vlucht_plek) <= 0.8:
                return None
            return self.krampus_vlucht_plek

        doel_plek = Vec3(self.speler.x, 0, self.speler.z)
        self.krampus_laatste_speler_plek = doel_plek
        self.krampus_vlucht_plek = None
        return doel_plek

    def beweeg_krampus_stap(self, stap):
        """Beweeg Krampus stap voor stap langs muren."""
        nieuwe_x = self.krampus.x + stap.x
        self.open_deuren_bij_krampus(nieuwe_x, self.krampus.z)
        if not self.krampus_botst_met_muur(nieuwe_x, self.krampus.z):
            self.krampus.x = nieuwe_x

        nieuwe_z = self.krampus.z + stap.z
        self.open_deuren_bij_krampus(self.krampus.x, nieuwe_z)
        if not self.krampus_botst_met_muur(self.krampus.x, nieuwe_z):
            self.krampus.z = nieuwe_z

    def beweeg_krampus(self):
        """Laat Krampus langzaam naar de speler lopen."""
        self.krampus_beweegt = False
        doel_plek = self.pak_krampus_jacht_plek()
        if doel_plek is None:
            self.zet_krampus_hoogte()
            return

        doel_tegel = wereld_naar_kaart(doel_plek)
        krampus_tegel = wereld_naar_kaart(self.krampus.position)
        self.krampus_pad_timer -= time.dt

        if self.krampus_pad_timer <= 0 or self.krampus_pad_doel != doel_tegel or (not self.krampus_pad and krampus_tegel != doel_tegel):
            self.maak_krampus_pad(doel_plek)
            self.krampus_pad_timer = KRAMPUS_PAD_INTERVAL

        doelpunt = self.pak_krampus_doelpunt(doel_plek)
        if doelpunt is None:
            self.krampus.look_at_2d(doel_plek, "y")
            self.zet_krampus_hoogte()
            return

        richting = Vec3(
            doelpunt.x - self.krampus.x,
            0,
            doelpunt.z - self.krampus.z,
        )
        if richting.length() <= 0.2:
            return

        snelheid = KRAMPUS_SNELHEID
        stap_lengte = min(snelheid * time.dt, richting.length())
        stap = richting.normalized() * stap_lengte
        oude_positie = Vec3(self.krampus.x, 0, self.krampus.z)
        self.beweeg_krampus_stap(stap)
        nieuwe_positie = Vec3(self.krampus.x, 0, self.krampus.z)
        if afstand_xz(oude_positie, nieuwe_positie) <= 0.01:
            self.krampus_pad = []
            self.krampus_pad_timer = 0.0
        else:
            self.krampus_beweegt = True
        self.krampus.look_at_2d(doelpunt, "y")
        self.zet_krampus_hoogte()

    def draai_sleutels(self):
        """Laat alle sleutels draaien en zweven."""
        for sleutel in self.sleutels:
            if not sleutel.enabled:
                continue
            sleutel.rotation_y += 120 * time.dt
            sleutel.y = sleutel.start_positie.y + math.sin(self.tijd_seconden * 4 + sleutel.start_positie.x * 0.05) * 0.12

    def werk_krampus_geluid_bij(self):
        """Speel stapgeluiden als Krampus dichterbij komt."""
        if self.krampus_stap_geluid is None or self.status != "spelen":
            return

        afstand = afstand_xz(self.speler.position, self.krampus.position)
        if not self.krampus_beweegt or afstand > KRAMPUS_GELUID_AFSTAND:
            self.krampus_stap_timer = 0.0
            return

        dichtbij_factor = max(0.0, min(1.0, 1.0 - (afstand / KRAMPUS_GELUID_AFSTAND)))
        self.krampus_stap_timer -= time.dt
        if self.krampus_stap_timer > 0:
            return

        self.krampus_stap_geluid.volume = 0.08 + dichtbij_factor * 0.55
        self.krampus_stap_geluid.pitch = 0.88 + dichtbij_factor * 0.18
        self.krampus_stap_geluid.play()
        self.krampus_stap_timer = 0.78 - dichtbij_factor * 0.46

    def update(self):
        """Werk alles elke frame bij."""
        self.draai_sleutels()
        self.werk_krampus_deuren_bij()

        if self.status != "spelen":
            return

        self.tijd_seconden += time.dt
        self.speler.y = 1.5

        if self.verstopt_in_kast and self.actieve_kast is not None:
            self.speler.position = self.actieve_kast.verstop_plek
            self.speler.speed = 0
        elif self.speler.speed != SPELER_SNELHEID:
            self.speler.speed = SPELER_SNELHEID

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
        self.werk_krampus_geluid_bij()

        for sleutel in self.sleutels:
            if sleutel.enabled and afstand_xz(self.speler.position, sleutel.position) < 1.4:
                self.pak_sleutel(sleutel)

        if afstand_xz(self.speler.position, self.deur.position) < 1.7:
            if self.heeft_sleutel:
                self.win_spel()
            else:
                nog_nodig = len(SLEUTEL_INFO) - len(self.gevonden_sleutels)
                self.melding = f"De uitgang zit nog op slot. Je mist nog {nog_nodig} sleutels."
                self.werk_tekst_bij()

        if not self.verstopt_in_kast and afstand_xz(self.speler.position, self.krampus.position) < 1.3:
            self.verlies_spel()

        self.werk_tekst_bij()

    def input(self, toets):
        """Reageer op toetsen van de speler."""
        if toets == "r":
            self.reset_spel()
        elif toets == "left mouse down" and self.status == "spelen":
            self.gebruik_interactie()
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
