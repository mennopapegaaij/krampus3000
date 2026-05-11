"""Krampus3000 - een simpel top-down horrorspel met pygame."""

import random
import sys

import pygame


# Dit zijn de basisinstellingen van het spelvenster.
BREEDTE = 960
HOOGTE = 640
FPS = 60
TITEL = "Krampus3000"

# Dit zijn de belangrijkste kleuren van het spel.
ACHTERGROND = (16, 10, 18)
PANEEL = (35, 22, 40)
TEKST = (240, 235, 240)
SUBTEKST = (190, 175, 195)
MIST = (60, 44, 68)
MUUR = (74, 54, 82)
MUUR_RAND = (116, 84, 128)
SPELER = (210, 230, 255)
SPELER_LICHT = (255, 245, 190)
MONSTER = (135, 40, 54)
MONSTER_OOG = (255, 215, 120)
SLEUTEL = (245, 210, 80)
DEUR_DICHT = (125, 50, 60)
DEUR_OPEN = (70, 165, 100)


def maak_muren():
    """Maak een simpele doolhof-kaart."""
    return [
        pygame.Rect(0, 0, BREEDTE, 20),
        pygame.Rect(0, HOOGTE - 20, BREEDTE, 20),
        pygame.Rect(0, 0, 20, HOOGTE),
        pygame.Rect(BREEDTE - 20, 0, 20, HOOGTE),
        pygame.Rect(180, 60, 20, 380),
        pygame.Rect(340, 20, 20, 240),
        pygame.Rect(500, 180, 20, 360),
        pygame.Rect(680, 60, 20, 300),
        pygame.Rect(820, 260, 20, 220),
        pygame.Rect(180, 420, 260, 20),
        pygame.Rect(360, 240, 260, 20),
        pygame.Rect(520, 520, 220, 20),
    ]


# Dit zijn veilige plekken waar de sleutel kan verschijnen.
SLEUTEL_PLEKKEN = [
    (90, 90),
    (250, 520),
    (430, 120),
    (620, 420),
    (760, 110),
    (880, 550),
]


def beweeg_rechthoek(rechthoek, snelheid_x, snelheid_y, muren):
    """Beweeg een rechthoek en stop netjes tegen muren."""
    rechthoek.x += snelheid_x
    for muur in muren:
        if rechthoek.colliderect(muur):
            if snelheid_x > 0:
                rechthoek.right = muur.left
            elif snelheid_x < 0:
                rechthoek.left = muur.right

    rechthoek.y += snelheid_y
    for muur in muren:
        if rechthoek.colliderect(muur):
            if snelheid_y > 0:
                rechthoek.bottom = muur.top
            elif snelheid_y < 0:
                rechthoek.top = muur.bottom


def teken_speler(scherm, speler_rect):
    """Teken de speler als een kleine held met licht."""
    pygame.draw.circle(scherm, SPELER_LICHT, speler_rect.center, 46)
    pygame.draw.circle(scherm, SPELER, speler_rect.center, speler_rect.width // 2)
    pygame.draw.circle(scherm, (30, 30, 40), (speler_rect.centerx - 6, speler_rect.centery - 4), 3)
    pygame.draw.circle(scherm, (30, 30, 40), (speler_rect.centerx + 6, speler_rect.centery - 4), 3)
    pygame.draw.arc(
        scherm,
        (30, 30, 40),
        pygame.Rect(speler_rect.x + 6, speler_rect.y + 10, speler_rect.width - 12, speler_rect.height - 10),
        0.3,
        2.8,
        2,
    )


def teken_monster(scherm, monster_rect):
    """Teken Krampus als een eng rood monster."""
    pygame.draw.ellipse(scherm, MONSTER, monster_rect)
    pygame.draw.ellipse(scherm, (35, 15, 20), monster_rect, 3)

    # Deze hoorntjes maken het monster extra eng.
    linker_hoorn = [(monster_rect.x + 4, monster_rect.y + 10), (monster_rect.x + 14, monster_rect.y - 14), (monster_rect.x + 24, monster_rect.y + 10)]
    rechter_hoorn = [(monster_rect.right - 24, monster_rect.y + 10), (monster_rect.right - 14, monster_rect.y - 14), (monster_rect.right - 4, monster_rect.y + 10)]
    pygame.draw.polygon(scherm, (220, 220, 220), linker_hoorn)
    pygame.draw.polygon(scherm, (220, 220, 220), rechter_hoorn)

    pygame.draw.circle(scherm, MONSTER_OOG, (monster_rect.centerx - 9, monster_rect.centery - 4), 4)
    pygame.draw.circle(scherm, MONSTER_OOG, (monster_rect.centerx + 9, monster_rect.centery - 4), 4)
    pygame.draw.circle(scherm, (0, 0, 0), (monster_rect.centerx - 9, monster_rect.centery - 4), 2)
    pygame.draw.circle(scherm, (0, 0, 0), (monster_rect.centerx + 9, monster_rect.centery - 4), 2)
    pygame.draw.arc(
        scherm,
        (255, 230, 230),
        pygame.Rect(monster_rect.x + 8, monster_rect.y + 12, monster_rect.width - 16, monster_rect.height - 12),
        0.2,
        2.9,
        2,
    )


def teken_sleutel(scherm, sleutel_rect):
    """Teken de gouden sleutel."""
    pygame.draw.circle(scherm, SLEUTEL, (sleutel_rect.x + 10, sleutel_rect.y + 10), 8, 3)
    pygame.draw.rect(scherm, SLEUTEL, (sleutel_rect.x + 16, sleutel_rect.y + 8, 18, 4))
    pygame.draw.rect(scherm, SLEUTEL, (sleutel_rect.x + 26, sleutel_rect.y + 8, 4, 10))
    pygame.draw.rect(scherm, SLEUTEL, (sleutel_rect.x + 32, sleutel_rect.y + 8, 4, 6))


def teken_achtergrond(scherm, speler_rect):
    """Teken de donkere kamer met een lichte kring rond de speler."""
    scherm.fill(ACHTERGROND)

    # Deze mist maakt de kamer spannender.
    for index in range(6):
        pygame.draw.ellipse(scherm, MIST, (index * 170 - 60, HOOGTE - 130 + (index % 2) * 12, 220, 90))

    # Deze lichtkringen geven het idee van een zaklamp.
    for straal, alpha in ((120, 40), (90, 55), (60, 75)):
        licht = pygame.Surface((BREEDTE, HOOGTE), pygame.SRCALPHA)
        pygame.draw.circle(licht, (255, 240, 170, alpha), speler_rect.center, straal)
        scherm.blit(licht, (0, 0))


def teken_tekst(scherm, font_groot, font_klein, heeft_sleutel, status, tijd_seconden, beste_tijd, melding):
    """Teken de titel en uitleg bovenaan."""
    titel = font_groot.render("Krampus3000", True, TEKST)
    if status == "spelen":
        opdracht = "Pak de sleutel en ontsnap via de deur!" if not heeft_sleutel else "Je hebt de sleutel! Ren nu naar de deur!"
    elif status == "gewonnen":
        opdracht = "Goed gedaan! Druk op R voor een nieuw potje."
    else:
        opdracht = "Krampus had je te pakken... Druk op R om opnieuw te beginnen."

    regel1 = font_klein.render(opdracht, True, TEKST)
    regel2 = font_klein.render(f"Tijd: {tijd_seconden:.1f} sec", True, SPELER_LICHT)
    regel3_tekst = "Beste tijd: -" if beste_tijd is None else f"Beste tijd: {beste_tijd:.1f} sec"
    regel3 = font_klein.render(regel3_tekst, True, SUBTEKST)
    regel4 = font_klein.render(melding, True, SUBTEKST)

    scherm.blit(titel, (24, 20))
    scherm.blit(regel1, (28, 72))
    scherm.blit(regel2, (28, 100))
    scherm.blit(regel3, (220, 100))
    scherm.blit(regel4, (28, 128))


def reset_spel():
    """Maak een nieuw spelrondje."""
    speler_rect = pygame.Rect(60, 70, 28, 28)
    monster_rect = pygame.Rect(840, 90, 34, 34)
    sleutel_x, sleutel_y = random.choice(SLEUTEL_PLEKKEN)
    sleutel_rect = pygame.Rect(sleutel_x, sleutel_y, 36, 20)
    deur_rect = pygame.Rect(860, 540, 54, 54)
    return speler_rect, monster_rect, sleutel_rect, deur_rect, False, "spelen", "Blijf uit de buurt van Krampus!"


def speel():
    """Start het spel en laat alles bewegen."""
    pygame.init()
    scherm = pygame.display.set_mode((BREEDTE, HOOGTE))
    pygame.display.set_caption(TITEL)
    klok = pygame.time.Clock()
    font_groot = pygame.font.SysFont("Arial", 38, bold=True)
    font_klein = pygame.font.SysFont("Arial", 24)

    muren = maak_muren()
    speler_rect, monster_rect, sleutel_rect, deur_rect, heeft_sleutel, status, melding = reset_spel()
    start_tijd = pygame.time.get_ticks()
    eind_tijd = None
    beste_tijd = None

    while True:
        delta_ms = klok.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Met R kun je snel opnieuw beginnen.
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                speler_rect, monster_rect, sleutel_rect, deur_rect, heeft_sleutel, status, melding = reset_spel()
                start_tijd = pygame.time.get_ticks()
                eind_tijd = None

        if status == "spelen":
            toetsen = pygame.key.get_pressed()
            snelheid = 4
            beweeg_x = 0
            beweeg_y = 0

            # Hier leest het spel welke kant jij op wilt lopen.
            if toetsen[pygame.K_LEFT] or toetsen[pygame.K_a]:
                beweeg_x -= snelheid
            if toetsen[pygame.K_RIGHT] or toetsen[pygame.K_d]:
                beweeg_x += snelheid
            if toetsen[pygame.K_UP] or toetsen[pygame.K_w]:
                beweeg_y -= snelheid
            if toetsen[pygame.K_DOWN] or toetsen[pygame.K_s]:
                beweeg_y += snelheid

            if beweeg_x != 0 and beweeg_y != 0:
                beweeg_x = int(beweeg_x * 0.7)
                beweeg_y = int(beweeg_y * 0.7)

            beweeg_rechthoek(speler_rect, beweeg_x, beweeg_y, muren)

            # Krampus jaagt op de speler en wordt sneller als jij de sleutel hebt.
            monster_snelheid = 2 if not heeft_sleutel else 3
            stap_x = 0
            stap_y = 0
            if speler_rect.centerx > monster_rect.centerx + 2:
                stap_x = monster_snelheid
            elif speler_rect.centerx < monster_rect.centerx - 2:
                stap_x = -monster_snelheid
            if speler_rect.centery > monster_rect.centery + 2:
                stap_y = monster_snelheid
            elif speler_rect.centery < monster_rect.centery - 2:
                stap_y = -monster_snelheid
            beweeg_rechthoek(monster_rect, stap_x, stap_y, muren)

            # Als je de sleutel raakt, gaat de deur open.
            if not heeft_sleutel and speler_rect.colliderect(sleutel_rect):
                heeft_sleutel = True
                melding = "Je hebt de sleutel gevonden!"

            # Zonder sleutel kun je de deur nog niet uit.
            if speler_rect.colliderect(deur_rect):
                if heeft_sleutel:
                    status = "gewonnen"
                    eind_tijd = (pygame.time.get_ticks() - start_tijd) / 1000
                    if beste_tijd is None or eind_tijd < beste_tijd:
                        beste_tijd = eind_tijd
                    melding = "Je bent ontsnapt aan Krampus!"
                else:
                    melding = "De deur zit nog op slot. Zoek de sleutel!"

            # Als Krampus jou raakt, verlies je.
            if speler_rect.colliderect(monster_rect):
                status = "verloren"
                melding = "Ai! Krampus heeft je gevangen."

        # Dit stukje bepaalt welke tijd bovenaan staat.
        if status == "spelen":
            tijd_seconden = (pygame.time.get_ticks() - start_tijd) / 1000
        else:
            tijd_seconden = 0.0 if eind_tijd is None else eind_tijd

        teken_achtergrond(scherm, speler_rect)

        # Eerst tekenen we de muren en de deur.
        for muur in muren:
            pygame.draw.rect(scherm, MUUR, muur, border_radius=8)
            pygame.draw.rect(scherm, MUUR_RAND, muur, 2, border_radius=8)

        deur_kleur = DEUR_OPEN if heeft_sleutel else DEUR_DICHT
        pygame.draw.rect(scherm, deur_kleur, deur_rect, border_radius=10)
        pygame.draw.rect(scherm, TEKST, deur_rect, 2, border_radius=10)

        if not heeft_sleutel:
            teken_sleutel(scherm, sleutel_rect)

        teken_speler(scherm, speler_rect)
        teken_monster(scherm, monster_rect)
        teken_tekst(scherm, font_groot, font_klein, heeft_sleutel, status, tijd_seconden, beste_tijd, melding)

        pygame.display.flip()


if __name__ == "__main__":
    speel()
