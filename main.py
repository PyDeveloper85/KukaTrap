import pygame
import os
import math
import random
import asyncio

# ============================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================
ANCHO = 900
ALTO = 650
FPS = 60
MAX_COMPUTADORAS = 24
MAX_BILLS = 10
TAMANO_PC = 52
TAMANO_BILL = 42
TAMANO_BALDE = 90
TIEMPO_NIVEL_BASE = 180.0  # 3 minutos

COLOR_FONDO = (40, 44, 52)
COLOR_BG =(178, 255, 255)
COLOR_TEXTO = (0, 220, 220)
COLOR_NEGRO = (0, 0, 0)
COLOR_ROJO = (220, 60, 60)
COLOR_VERDE = (80, 200, 120)
COLOR_AMARILLO = (255, 180, 50)

NOMBRES_PC = [
    "Buenos Aires", "CABA", "Catamarca", "Chaco", "Chubut", "Córdoba",
    "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja",
    "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan",
    "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero",
    "Tierra del Fuego", "Tucumán"
]

# Variables globales
nivel_actual = 1
puntuacion = 0
estado_juego = "MENU"  # MENU | JUGANDO | GAMEOVER


def obtener_config_nivel(nivel):
    return {
        "max_bills": min(4 + nivel * 2, MAX_BILLS),
        "velocidad_bill": min(1.2 + (nivel * 0.3), 3.5),
        "tiempo_instalacion": max(6.0 - (nivel * 0.5), 1.8),
        "spawn_cooldown": max(3.0 - (nivel * 0.4), 0.7)
    }


def cargar_imagen(ruta, tamano=None):
    try:
        img = pygame.image.load(ruta).convert_alpha()
        if tamano:
            img = pygame.transform.scale(img, tamano)
        return img
    except Exception as e:
        print(f"No se pudo cargar {ruta}: {e}")
        return None


# ============================================
# CLASES
# ============================================
class Computer:
    def __init__(self, x, y, nombre, sprites_casa):
        self.x = x
        self.y = y
        self.nombre = nombre
        self.estado = "libre"  # libre | siendo_infectada | infectada
        self.bill_asignado = None
        self.progreso = 0.0
        self.rect = pygame.Rect(x, y, TAMANO_PC, TAMANO_PC)
        self.sprites_casa = sprites_casa
        self.partido_inicial = random.choice(["PRO", "UCR", "LLA"])

    def actualizar(self, dt, tiempo_instalacion):
        if self.estado == "siendo_infectada" and self.bill_asignado:
            self.progreso += dt / tiempo_instalacion
            if self.progreso >= 1.0:
                self.estado = "infectada"
                self.bill_asignado.estado = "caminando"
                self.bill_asignado.objetivo = None
                self.bill_asignado = None
                self.progreso = 0.0

    def sanar(self):
        """Vuelve el distrito a estado libre."""
        if self.estado == "infectada":
            self.estado = "libre"
            self.progreso = 0.0
            self.bill_asignado = None
            return True
        return False

    def dibujar(self, pantalla, fuente):
        img = None
        color_fallback = COLOR_VERDE

        if self.estado == "infectada":
            img = self.sprites_casa.get("PJ")
            color_fallback = COLOR_ROJO
        else:
            img = self.sprites_casa.get(self.partido_inicial)
            color_fallback = COLOR_AMARILLO if self.estado == "siendo_infectada" else COLOR_VERDE

        if img:
            pantalla.blit(pygame.transform.scale(img, (TAMANO_PC, TAMANO_PC)), (self.x, self.y))
        else:
            pygame.draw.rect(pantalla, color_fallback, self.rect, border_radius=6)

        if self.estado == "siendo_infectada" and (pygame.time.get_ticks() // 200) % 2 == 0:
            pygame.draw.rect(pantalla, COLOR_ROJO, self.rect, width=2, border_radius=6)

        texto = fuente.render(self.nombre, True, COLOR_NEGRO)
        pantalla.blit(texto, (self.x + TAMANO_PC // 2 - texto.get_width() // 2, self.y + TAMANO_PC + 3))

        if self.estado == "siendo_infectada":
            pygame.draw.rect(pantalla, (50, 50, 50), (self.x, self.y - 12, TAMANO_PC, 7))
            pygame.draw.rect(pantalla, COLOR_ROJO, (self.x, self.y - 12, int(TAMANO_PC * self.progreso), 7))


class Bill:
    def __init__(self, x, y, frames_caminando, frames_infectando, img_mancha_verde):
        self.x = x
        self.y = y
        self.estado = "caminando"  # caminando | trabajando | muerto
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.objetivo = None
        self.rect = pygame.Rect(x, y, TAMANO_BILL, TAMANO_BILL)
        self.frames_caminando = frames_caminando
        self.frames_infectando = frames_infectando
        self.img_mancha_verde = img_mancha_verde
        self.frame_actual = 0
        self.frame_timer = 0.0
        self.velocidad_animacion = 0.12
        self.tiempo_muerto = 0.0

    def actualizar(self, dt, computadoras, velocidad_bill):
        if self.estado == "muerto":
            self.tiempo_muerto += dt
            return

        if self.estado in ("caminando", "trabajando"):
            self.frame_timer += dt
            if self.frame_timer >= self.velocidad_animacion:
                self.frame_timer = 0.0
                self.frame_actual += 1

        if self.estado == "caminando":
            if self.objetivo is None or self.objetivo.estado != "libre":
                libres = [c for c in computadoras if c.estado == "libre" and c.bill_asignado is None]
                self.objetivo = min(libres, key=lambda c: math.hypot(c.x - self.x, c.y - self.y)) if libres else None

            if self.objetivo:
                dx = self.objetivo.x - self.x
                dy = self.objetivo.y - self.y
                dist = math.hypot(dx, dy)

                if dist < 12:
                    self.estado = "trabajando"
                    self.objetivo.estado = "siendo_infectada"
                    self.objetivo.bill_asignado = self
                    self.vel_x = self.vel_y = 0
                else:
                    self.vel_x = (dx / dist) * velocidad_bill
                    self.vel_y = (dy / dist) * velocidad_bill
                    self.x += self.vel_x
                    self.y += self.vel_y

            self.rect.topleft = (self.x, self.y)

    def dibujar(self, pantalla):
        if self.estado == "muerto":
            if self.img_mancha_verde:
                pantalla.blit(self.img_mancha_verde, (self.x, self.y))
            return

        img = None
        if self.estado == "caminando":
            if self.frames_caminando:
                self.frame_actual %= len(self.frames_caminando)
                img = self.frames_caminando[self.frame_actual]
        elif self.estado == "trabajando":
            if self.frames_infectando:
                self.frame_actual %= len(self.frames_infectando)
                img = self.frames_infectando[self.frame_actual]

        if img:
            if self.vel_x < 0:
                img = pygame.transform.flip(img, True, False)
            pantalla.blit(pygame.transform.scale(img, (TAMANO_BILL, TAMANO_BILL)), (self.x, self.y))
        else:
            pygame.draw.rect(pantalla, (255, 180, 40), self.rect, border_radius=8)


class Trash:
    def __init__(self, img_balde):
        self.pos_original_x = ANCHO - TAMANO_BALDE - 25
        self.pos_original_y = ALTO - TAMANO_BALDE - 25
        self.x = self.pos_original_x
        self.y = self.pos_original_y
        self.rect = pygame.Rect(self.x, self.y, TAMANO_BALDE, TAMANO_BALDE)
        self.img_balde = img_balde
        self.seleccionado = False

    def reset_posicion(self):
        self.x = self.pos_original_x
        self.y = self.pos_original_y
        self.rect.topleft = (self.x, self.y)
        self.seleccionado = False

    def dibujar(self, pantalla, fuente):
        if self.img_balde:
            pantalla.blit(self.img_balde, (self.x, self.y))
        else:
            pygame.draw.rect(pantalla, (70, 70, 70), self.rect, border_radius=12)
            pygame.draw.rect(pantalla, (130, 130, 130), self.rect, width=3, border_radius=12)
            texto = fuente.render("BALDE", True, COLOR_TEXTO)
            pantalla.blit(texto, (self.x + TAMANO_BALDE // 2 - texto.get_width() // 2,
                                  self.y + TAMANO_BALDE // 2 - 6))

        # Indicador visual cuando está seleccionado
        if self.seleccionado:
            pygame.draw.rect(pantalla, COLOR_AMARILLO, self.rect, width=3, border_radius=12)


# ============================================
# PANTALLAS UI
# ============================================
def dibujar_menu(pantalla, fuente, fuente_grande):
    pantalla.fill(COLOR_FONDO)
    txt_titulo = fuente_grande.render("KukaTrap", True, COLOR_AMARILLO)
    txt_subtitulo = fuente.render("Evita que los Kukas te copen los distritos", True, COLOR_TEXTO)
    pantalla.blit(txt_titulo, (ANCHO // 2 - txt_titulo.get_width() // 2, ALTO // 3))
    pantalla.blit(txt_subtitulo, (ANCHO // 2 - txt_subtitulo.get_width() // 2, ALTO // 3 + 40))

    if (pygame.time.get_ticks() // 400) % 2 == 0:
        txt_start = fuente.render("PRESIONA ENTER PARA EMPEZAR", True, COLOR_VERDE)
        pantalla.blit(txt_start, (ANCHO // 2 - txt_start.get_width() // 2, ALTO // 2 + 50))


def dibujar_gameover(pantalla, fuente, fuente_grande):
    pantalla.fill((20, 20, 25))
    txt_gameover = fuente_grande.render("¡Estamos perdidos!", True, COLOR_ROJO)
    txt_motivo = fuente.render("Hiciste volver al kukismo", True, COLOR_TEXTO)
    txt_final_pts = fuente_grande.render(f"PUNTUACION FINAL: {puntuacion}", True, COLOR_AMARILLO)
    txt_final_lvl = fuente.render(f"Llegaste al Nivel: {nivel_actual}", True, COLOR_TEXTO)

    pantalla.blit(txt_gameover, (ANCHO // 2 - txt_gameover.get_width() // 2, ALTO // 4))
    pantalla.blit(txt_motivo, (ANCHO // 2 - txt_motivo.get_width() // 2, ALTO // 4 + 40))
    pantalla.blit(txt_final_pts, (ANCHO // 2 - txt_final_pts.get_width() // 2, ALTO // 2 - 20))
    pantalla.blit(txt_final_lvl, (ANCHO // 2 - txt_final_lvl.get_width() // 2, ALTO // 2 + 20))

    if (pygame.time.get_ticks() // 400) % 2 == 0:
        txt_reiniciar = fuente.render("PRESIONA 'R' PARA REINICIAR", True, COLOR_VERDE)
        pantalla.blit(txt_reiniciar, (ANCHO // 2 - txt_reiniciar.get_width() // 2, ALTO // 2 + 100))

    txt_salir = fuente.render("Presiona 'ESC' para Salir", True, COLOR_TEXTO)
    pantalla.blit(txt_salir, (ANCHO // 2 - txt_salir.get_width() // 2, ALTO // 2 + 140))


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
async def main():
    global nivel_actual, puntuacion, estado_juego

    pygame.init()
    pygame.mixer.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("KukaTrap")
    reloj = pygame.time.Clock()

    # Fuentes
    try:
        fuente = pygame.font.Font(os.path.join("Assets", "PressStart2P-Regular.ttf"), 9)
        fuente_grande = pygame.font.Font(os.path.join("Assets", "PressStart2P-Regular.ttf"), 14)
    except Exception:
        fuente = pygame.font.SysFont("Arial", 12)
        fuente_grande = pygame.font.SysFont("Arial", 18)

    # --- AUDIO ---
    sound_pop = None
    try:
        sound_pop = pygame.mixer.Sound(os.path.join("Assets", "audio", "sound03.ogg"))
        sound_pop.set_volume(0.65)
    except Exception as e:
        print(f"No se pudo cargar sound02.ogg (pop): {e}")

    try:
        pygame.mixer.music.load(os.path.join("Assets", "audio", "sound02.ogg"))
        pygame.mixer.music.set_volume(0.35)
    except Exception as e:
        print(f"No se pudo cargar sound03.ogg (música): {e}")

    try:
        sound_intro = pygame.mixer.Sound(os.path.join("Assets", "audio", "sound01.ogg"))
        sound_intro.set_volume(0.7)
        sound_intro.play()
    except Exception as e:
        print(f"No se pudo cargar sound01.ogg: {e}")

    # --- SPRITES ---
    img_spritesheet_casas = cargar_imagen(os.path.join("Assets", "Computers", "computers01.png"))
    sprites_casa = {}
    if img_spritesheet_casas:
        ancho_frame = img_spritesheet_casas.get_width() // 4
        alto_frame = img_spritesheet_casas.get_height()
        sprites_casa["PRO"] = img_spritesheet_casas.subsurface(pygame.Rect(0 * ancho_frame, 0, ancho_frame, alto_frame))
        sprites_casa["UCR"] = img_spritesheet_casas.subsurface(pygame.Rect(1 * ancho_frame, 0, ancho_frame, alto_frame))
        sprites_casa["LLA"] = img_spritesheet_casas.subsurface(pygame.Rect(2 * ancho_frame, 0, ancho_frame, alto_frame))
        sprites_casa["PJ"]  = img_spritesheet_casas.subsurface(pygame.Rect(3 * ancho_frame, 0, ancho_frame, alto_frame))

    img_spritesheet_axel = cargar_imagen(os.path.join("Assets", "Bill", "Bill_spritesheet01.png"))
    frames_caminando = []
    frames_infectando = []
    if img_spritesheet_axel:
        ancho_f = img_spritesheet_axel.get_width() // 3
        alto_f = img_spritesheet_axel.get_height() // 4
        for c in range(3):
            frames_caminando.append(img_spritesheet_axel.subsurface(pygame.Rect(c * ancho_f, 0 * alto_f, ancho_f, alto_f)))
            frames_infectando.append(img_spritesheet_axel.subsurface(pygame.Rect(c * ancho_f, 1 * alto_f, ancho_f, alto_f)))

    img_mancha_verde = cargar_imagen(os.path.join("Assets", "Bill", "mancha_verde.png"), (TAMANO_BILL, TAMANO_BILL))
    img_balde = cargar_imagen(os.path.join("Assets", "Trash", "balde.png"), (TAMANO_BALDE, TAMANO_BALDE))

    def crear_computadoras():
        comps = []
        margen_x, margen_y = 35, 55
        espacio_x = (ANCHO - 2 * margen_x - 6 * TAMANO_PC) // 5
        espacio_y = 78
        idx = 0
        for fila in range(4):
            for col in range(6):
                if idx < len(NOMBRES_PC):
                    x = margen_x + col * (TAMANO_PC + espacio_x)
                    y = margen_y + fila * (TAMANO_PC + espacio_y)
                    comps.append(Computer(x, y, NOMBRES_PC[idx], sprites_casa))
                    idx += 1
        return comps

    computadoras = crear_computadoras()
    lista_bills = []
    balde = Trash(img_balde)
    tiempo_ultimo_spawn = 0.0
    tiempo_restante_nivel = TIEMPO_NIVEL_BASE
    ejecutando = True

    # ============================================
    # BUCLE PRINCIPAL
    # ============================================
    while ejecutando:
        dt = reloj.tick(FPS) / 1000.0
        pos_mouse = pygame.mouse.get_pos()
        config = obtener_config_nivel(nivel_actual)

        # --- EVENTOS ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False

            if estado_juego == "MENU":
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN:
                    estado_juego = "JUGANDO"
                    tiempo_restante_nivel = TIEMPO_NIVEL_BASE
                    try:
                        pygame.mixer.music.play(-1)
                    except Exception:
                        pass

            elif estado_juego == "GAMEOVER":
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_r:
                        puntuacion = 0
                        nivel_actual = 1
                        tiempo_ultimo_spawn = 0.0
                        tiempo_restante_nivel = TIEMPO_NIVEL_BASE
                        lista_bills.clear()
                        computadoras = crear_computadoras()
                        balde.reset_posicion()
                        estado_juego = "JUGANDO"
                        try:
                            pygame.mixer.music.play(-1)
                        except Exception:
                            pass
                    elif evento.key == pygame.K_ESCAPE:
                        ejecutando = False

            elif estado_juego == "JUGANDO":


                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:

                    # 1. ¿Clic en el balde? → lo seleccionamos para arrastrar
                    if balde.rect.collidepoint(pos_mouse):
                        balde.seleccionado = True

                    else:
                        # 2. ¿Clic en un Bill? → lo eliminamos
                        for b in lista_bills:
                            if b.estado in ("caminando", "trabajando") and b.rect.collidepoint(pos_mouse):
                                b.estado = "muerto"
                                if sound_pop:
                                    sound_pop.play()
                                # Liberar la PC si estaba trabajando
                                if b.objetivo and b.objetivo.estado == "siendo_infectada":
                                    b.objetivo.estado = "libre"
                                    b.objetivo.bill_asignado = None
                                    b.objetivo.progreso = 0.0
                                puntuacion += 50
                                break

                elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                    if balde.seleccionado:
                        # Al soltar el balde, comprobamos si está encima de alguna PC infectada
                        for c in computadoras:
                            if c.estado == "infectada" and balde.rect.colliderect(c.rect):
                                if c.sanar():
                                    puntuacion += 150
                                    if sound_pop:
                                        sound_pop.play()
                                break  # solo sana una por soltada

                        # El balde siempre vuelve a su lugar
                        balde.reset_posicion()

        # --- LÓGICA ---
        if estado_juego == "JUGANDO":
            tiempo_restante_nivel -= dt

            # Seguir al mouse mientras el balde está seleccionado
            if balde.seleccionado:
                balde.x = pos_mouse[0] - TAMANO_BALDE // 2
                balde.y = pos_mouse[1] - TAMANO_BALDE // 2
                balde.rect.topleft = (balde.x, balde.y)

            # Subir de nivel
            if tiempo_restante_nivel <= 0:
                nivel_actual += 1
                tiempo_ultimo_spawn = 0.0
                tiempo_restante_nivel = TIEMPO_NIVEL_BASE
                lista_bills.clear()
                computadoras = crear_computadoras()
                balde.reset_posicion()

            # Spawn de Bills
            tiempo_ultimo_spawn += dt
            cant_activos = sum(1 for b in lista_bills if b.estado in ("caminando", "trabajando"))
            if tiempo_ultimo_spawn >= config["spawn_cooldown"] and cant_activos < config["max_bills"]:
                borde = random.choice(["izq", "der", "arriba"])
                if borde == "izq":
                    x, y = -TAMANO_BILL, random.randint(0, ALTO - 200)
                elif borde == "der":
                    x, y = ANCHO + TAMANO_BILL, random.randint(0, ALTO - 200)
                else:
                    x, y = random.randint(0, ANCHO), -TAMANO_BILL
                lista_bills.append(Bill(x, y, frames_caminando, frames_infectando, img_mancha_verde))
                tiempo_ultimo_spawn = 0.0

            for c in computadoras:
                c.actualizar(dt, config["tiempo_instalacion"])

            for b in lista_bills:
                b.actualizar(dt, computadoras, config["velocidad_bill"])

            lista_bills = [b for b in lista_bills if not (b.estado == "muerto" and b.tiempo_muerto >= 2.0)]

            # Game Over
            infectadas = sum(1 for c in computadoras if c.estado == "infectada")
            if infectadas == len(computadoras):
                estado_juego = "GAMEOVER"
                balde.reset_posicion()
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

        # --- RENDER ---
        if estado_juego == "MENU":
            dibujar_menu(pantalla, fuente, fuente_grande)
        elif estado_juego == "GAMEOVER":
            dibujar_gameover(pantalla, fuente, fuente_grande)
        elif estado_juego == "JUGANDO":
            pantalla.fill(COLOR_BG)

            for c in computadoras:
                c.dibujar(pantalla, fuente)
            for b in lista_bills:
                b.dibujar(pantalla)

            # El balde se dibuja al final para que quede arriba
            balde.dibujar(pantalla, fuente)

            # HUD
            infectadas = sum(1 for c in computadoras if c.estado == "infectada")
            txt_nivel = fuente_grande.render(f"NIVEL: {nivel_actual}", True, COLOR_NEGRO)
            txt_puntos = fuente_grande.render(f"PTS: {puntuacion}", True, COLOR_NEGRO)
            minutos = int(tiempo_restante_nivel) // 60
            segundos = int(tiempo_restante_nivel) % 60
            color_timer = COLOR_VERDE if tiempo_restante_nivel > 20 else COLOR_ROJO
            txt_timer = fuente_grande.render(f"TIEMPO: {minutos:02d}:{segundos:02d}", True, color_timer)
            txt_status = fuente.render(f"Tomadas: {infectadas}/{len(computadoras)}",
                                       True, COLOR_ROJO if infectadas > 0 else COLOR_VERDE)

            pantalla.blit(txt_nivel, (25, 20))
            pantalla.blit(txt_puntos, (170, 20))
            pantalla.blit(txt_timer, (340, 20))
            pantalla.blit(txt_status, (ANCHO - 210, 23))

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.mixer.music.stop()
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())