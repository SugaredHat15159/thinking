import json
import math
import random
from pathlib import Path

import pygame

WIDTH = 480
HEIGHT = 640
PLAYER_SIZE = 30
PLAYER_SPEED = 320  # pixels per second
SPAWN_INTERVAL_MS = 900
SPAWN_INTERVAL_MIN_MS = 250
SPAWN_ACCELERATION = 0.98
BEST_FILE = Path("best_score.json")
BULLET_SPEED = 520
BULLET_COOLDOWN = 0.18
BULLET_WIDTH = 6
BULLET_HEIGHT = 16
BOSS_BULLET_DAMAGE = 5
BOSS_TRIGGER_SCORE = 5000
BOSS_HEALTH = 300
BOSS_SPEED = 120
BOSS_ATTACK_COOLDOWN_RANGE = (2.5, 4.5)
LASER_WARNING_DURATION = 1.2
LASER_ACTIVE_DURATION = 1.0
LASER_WIDTH = 100
FAN_WARNING_DURATION = 0.8
FAN_VOLLEYS = 3
FAN_COOLDOWN = 0.65
BOSS_PROJECTILE_SPEED = 280
BOSS_PROJECTILE_SIZE = (12, 18)


def load_best_score() -> int:
  if BEST_FILE.exists():
    try:
      with BEST_FILE.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
      return int(data.get("best", 0))
    except (ValueError, json.JSONDecodeError):
      return 0
  return 0


def save_best_score(score: int) -> None:
  BEST_FILE.write_text(json.dumps({"best": score}), encoding="utf-8")


class Meteor:
  def __init__(self, score: int) -> None:
    self.size = random.randint(20, 50)
    self.x = random.randint(0, WIDTH - self.size)
    self.y = -self.size
    self.speed = 140 + random.random() * 120 + score * 1.6
    self.rotation = random.random() * math.tau
    self.spin = (random.random() * 2 - 1) * 2.5  # degrees per frame

  def update(self, dt: float) -> None:
    self.y += self.speed * dt
    self.rotation = (self.rotation + math.radians(self.spin)) % math.tau

  def offscreen(self) -> bool:
    return self.y > HEIGHT + self.size

  def rect(self) -> pygame.Rect:
    return pygame.Rect(self.x, self.y, self.size, self.size)

  def draw(self, surface: pygame.Surface) -> None:
    cx = self.x + self.size / 2
    cy = self.y + self.size / 2
    radius = self.size / 2
    points = []
    for i in range(6):
      angle = self.rotation + i * (math.tau / 6)
      r = radius * (0.6 + random.random() * 0.4)
      px = cx + math.cos(angle) * r
      py = cy + math.sin(angle) * r
      points.append((px, py))
    pygame.draw.polygon(surface, (255, 179, 71), points)


class Bullet:
  def __init__(self, x: float, y: float) -> None:
    self.x = x
    self.y = y
    self.rect = pygame.Rect(self.x, self.y, BULLET_WIDTH, BULLET_HEIGHT)

  def update(self, dt: float) -> None:
    self.y -= BULLET_SPEED * dt
    self.rect.topleft = (self.x, self.y)

  def offscreen(self) -> bool:
    return self.y + BULLET_HEIGHT < 0

  def draw(self, surface: pygame.Surface) -> None:
    pygame.draw.rect(surface, (255, 255, 160), self.rect)


class Boss:
  def __init__(self) -> None:
    self.width = 200
    self.height = 70
    self.x = WIDTH // 2 - self.width // 2
    self.y = 80
    self.direction = 1
    self.health = BOSS_HEALTH

  def rect(self) -> pygame.Rect:
    return pygame.Rect(self.x, self.y, self.width, self.height)

  def update(self, dt: float) -> None:
    self.x += self.direction * BOSS_SPEED * dt
    if self.x <= 20 or self.x + self.width >= WIDTH - 20:
      self.direction *= -1
      self.x = clamp(self.x, 20, WIDTH - 20 - self.width)

  def draw(self, surface: pygame.Surface) -> None:
    body_rect = self.rect()
    pygame.draw.rect(surface, (180, 90, 255), body_rect, border_radius=12)
    pygame.draw.rect(surface, (60, 15, 120), (body_rect.x + 20, body_rect.y + 15, self.width - 40, 20), border_radius=10)
    pygame.draw.circle(surface, (255, 255, 255), (body_rect.centerx, body_rect.y + 10), 8)


class BossProjectile:
  def __init__(self, x: float, y: float, angle: float, speed: float = BOSS_PROJECTILE_SPEED) -> None:
    self.x = x
    self.y = y
    self.vx = math.sin(angle) * speed
    self.vy = math.cos(angle) * speed
    self.rect = pygame.Rect(self.x, self.y, BOSS_PROJECTILE_SIZE[0], BOSS_PROJECTILE_SIZE[1])

  def update(self, dt: float) -> None:
    self.x += self.vx * dt
    self.y += self.vy * dt
    self.rect.topleft = (self.x, self.y)

  def offscreen(self) -> bool:
    return self.y > HEIGHT + 40 or self.x < -50 or self.x > WIDTH + 50

  def draw(self, surface: pygame.Surface) -> None:
    pygame.draw.rect(surface, (255, 120, 200), self.rect, border_radius=4)
    pygame.draw.rect(surface, (255, 255, 255), self.rect.inflate(-4, -4), border_radius=4)


def clamp(value: float, minimum: float, maximum: float) -> float:
  return max(minimum, min(maximum, value))


def draw_background(surface: pygame.Surface, score: int) -> None:
  surface.fill((4, 4, 13))
  # subtle gradient
  overlay = pygame.Surface((WIDTH, HEIGHT))
  overlay.fill((0, 0, 0))
  pygame.draw.rect(overlay, (30, 60, 160), pygame.Rect(0, 0, WIDTH, HEIGHT // 2))
  overlay.set_alpha(30)
  surface.blit(overlay, (0, 0))

  random.seed(score // 25)
  for _ in range(40):
    px = random.randint(0, WIDTH - 2)
    py = random.randint(0, HEIGHT - 2)
    surface.fill((255, 255, 255), pygame.Rect(px, py, 2, 2))


def draw_text(surface: pygame.Surface, text: str, font: pygame.font.Font, color: tuple[int, int, int], pos: tuple[int, int]) -> None:
  surface.blit(font.render(text, True, color), pos)


def create_boss_attack() -> tuple[dict, str]:
  attack_type = random.choice(["laser", "fan"])
  if attack_type == "laser":
    column = random.randint(40, WIDTH - LASER_WIDTH - 40)
    return (
        {"type": "laser", "phase": "warning", "timer": LASER_WARNING_DURATION, "column": column, "width": LASER_WIDTH},
        "Boss charging a laser lane! Clear the highlight.",
    )
  return (
      {"type": "fan", "phase": "warning", "timer": FAN_WARNING_DURATION, "volleys": FAN_VOLLEYS, "cooldown": FAN_COOLDOWN},
      "Boss prepping a missile barrage! Get ready to dodge.",
  )


def spawn_fan_volley(projectiles: list[BossProjectile], boss: Boss) -> None:
  origin = boss.rect().midbottom
  angles = [-0.4, -0.2, 0, 0.2, 0.4]
  for angle in angles:
    proj_x = origin[0] - BOSS_PROJECTILE_SIZE[0] / 2
    projectiles.append(BossProjectile(proj_x, origin[1], angle))


def update_boss_attack(
    attack: dict,
    dt: float,
    player: pygame.Rect,
    boss: Boss,
    boss_projectiles: list[BossProjectile],
) -> tuple[dict | None, bool, bool]:
  player_hit = False
  finished = False

  if attack["type"] == "laser":
    attack["timer"] -= dt
    beam_rect = pygame.Rect(attack["column"], 0, attack["width"], HEIGHT)
    attack["rect"] = beam_rect
    if attack["phase"] == "warning":
      if attack["timer"] <= 0:
        attack["phase"] = "active"
        attack["timer"] = LASER_ACTIVE_DURATION
    elif attack["phase"] == "active":
      if player.colliderect(beam_rect):
        player_hit = True
      if attack["timer"] <= 0:
        finished = True

  elif attack["type"] == "fan":
    if attack["phase"] == "warning":
      attack["timer"] -= dt
      if attack["timer"] <= 0:
        attack["phase"] = "firing"
        attack["timer"] = 0
    elif attack["phase"] == "firing":
      attack["timer"] -= dt
      if attack["timer"] <= 0 and attack["volleys"] > 0:
        spawn_fan_volley(boss_projectiles, boss)
        attack["volleys"] -= 1
        attack["timer"] = attack["cooldown"]
      if attack["volleys"] == 0 and attack["timer"] <= 0:
        finished = True

  if finished:
    return None, True, player_hit
  return attack, False, player_hit


def draw_boss_attack(surface: pygame.Surface, attack: dict | None, boss: Boss | None) -> None:
  if not attack or not boss:
    return
  if attack["type"] == "laser":
    rect = pygame.Rect(attack["column"], 0, attack["width"], HEIGHT)
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if attack["phase"] == "warning":
      overlay.fill((255, 240, 150, 90))
    else:
      overlay.fill((255, 80, 20, 180))
    surface.blit(overlay, rect.topleft)
  elif attack["type"] == "fan" and attack["phase"] == "warning":
    body = boss.rect()
    warn_rect = pygame.Rect(body.x - 15, body.bottom, body.width + 30, 70)
    overlay = pygame.Surface(warn_rect.size, pygame.SRCALPHA)
    overlay.fill((255, 210, 150, 80))
    surface.blit(overlay, warn_rect.topleft)
    pygame.draw.polygon(
        surface,
        (255, 210, 150),
        [
            (body.centerx - 50, body.bottom + 15),
            (body.centerx + 50, body.bottom + 15),
            (body.centerx, body.bottom + 70),
        ],
        width=2,
    )


def main() -> None:
  pygame.init()
  pygame.display.set_caption("Meteor Escape - Desktop")
  screen = pygame.display.set_mode((WIDTH, HEIGHT))
  clock = pygame.time.Clock()

  font_large = pygame.font.SysFont("segoeui", 36) or pygame.font.SysFont(None, 36)
  font_medium = pygame.font.SysFont("segoeui", 24) or pygame.font.SysFont(None, 24)
  font_small = pygame.font.SysFont("segoeui", 18) or pygame.font.SysFont(None, 18)

  player = pygame.Rect(WIDTH // 2 - PLAYER_SIZE // 2, HEIGHT - 80, PLAYER_SIZE, PLAYER_SIZE)
  meteors: list[Meteor] = []
  bullets: list[Bullet] = []
  boss_projectiles: list[BossProjectile] = []
  spawn_timer = 0.0
  spawn_interval = SPAWN_INTERVAL_MS
  shoot_timer = 0.0
  score = 0
  best_score = load_best_score()
  boss: Boss | None = None
  boss_triggered = False
  boss_attack: dict | None = None
  boss_next_attack = 2.5
  game_state = "idle"  # idle | running | over | won
  status_message = "Press Space to launch (hold Space during play to shoot)"

  running = True
  while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        running = False
      elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
        if game_state in {"idle", "over", "won"}:
          meteors.clear()
          bullets.clear()
          boss_projectiles.clear()
          spawn_timer = 0.0
          spawn_interval = SPAWN_INTERVAL_MS
          shoot_timer = 0.0
          score = 0
          player.x = WIDTH // 2 - PLAYER_SIZE // 2
          player.y = HEIGHT - 80
          boss = None
          boss_triggered = False
          boss_attack = None
          boss_next_attack = 2.5
          game_state = "running"
          status_message = "Survive! Hold Space to fire."

    keys = pygame.key.get_pressed()
    player_hit = False
    if game_state == "running":
      shoot_timer = max(0.0, shoot_timer - dt)
      dx = (1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) - (1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
      dy = (1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0) - (1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0)

      if dx or dy:
        length = math.hypot(dx, dy)
        dx /= length if length else 1
        dy /= length if length else 1
      player.x += dx * PLAYER_SPEED * dt
      player.y += dy * PLAYER_SPEED * dt
      player.x = clamp(player.x, 0, WIDTH - PLAYER_SIZE)
      player.y = clamp(player.y, 0, HEIGHT - PLAYER_SIZE)

      if keys[pygame.K_SPACE] and shoot_timer <= 0:
        bullets.append(Bullet(player.centerx - BULLET_WIDTH / 2, player.y - BULLET_HEIGHT))
        shoot_timer = BULLET_COOLDOWN

      if boss is None:
        spawn_timer += dt * 1000
        if spawn_timer >= spawn_interval:
          meteors.append(Meteor(score))
          spawn_timer = 0.0
          spawn_interval = max(SPAWN_INTERVAL_MIN_MS, spawn_interval * SPAWN_ACCELERATION)

      for meteor in list(meteors):
        meteor.update(dt)
        if meteor.offscreen():
          meteors.remove(meteor)

      if boss:
        boss.update(dt)
      elif score >= BOSS_TRIGGER_SCORE and not boss_triggered:
        boss = Boss()
        boss_triggered = True
        boss_next_attack = 2.0
        status_message = "Boss inbound! Destroy it to win."

      if boss:
        if boss_attack is None:
          boss_next_attack -= dt
          if boss_next_attack <= 0:
            boss_attack, status_message = create_boss_attack()
        else:
          boss_attack, finished, attack_hit = update_boss_attack(boss_attack, dt, player, boss, boss_projectiles)
          if attack_hit:
            player_hit = True
          if finished:
            boss_attack = None
            boss_next_attack = random.uniform(*BOSS_ATTACK_COOLDOWN_RANGE)
            if not player_hit:
              status_message = "Attack dodged! Keep firing."

      for bullet in list(bullets):
        bullet.update(dt)
        if bullet.offscreen():
          bullets.remove(bullet)
          continue

        destroyed_meteor = False
        for meteor in list(meteors):
          if bullet.rect.colliderect(meteor.rect()):
            if bullet in bullets:
              bullets.remove(bullet)
            meteors.remove(meteor)
            score += 50
            destroyed_meteor = True
            break
        if destroyed_meteor:
          continue

        if boss and bullet.rect.colliderect(boss.rect()):
          boss.health -= BOSS_BULLET_DAMAGE
          if bullet in bullets:
            bullets.remove(bullet)
          score += 5
          if boss.health <= 0:
            boss = None
            boss_attack = None
            boss_projectiles.clear()
            game_state = "won"
            status_message = "Boss defeated! Press Space to play again."
            if score > best_score:
              best_score = score
              save_best_score(best_score)
          continue

      for projectile in list(boss_projectiles):
        projectile.update(dt)
        if projectile.offscreen():
          boss_projectiles.remove(projectile)
          continue
        if projectile.rect.colliderect(player):
          player_hit = True

      if not player_hit and (any(player.colliderect(m.rect()) for m in meteors) or (boss and player.colliderect(boss.rect()))):
        player_hit = True

      if player_hit:
        game_state = "over"
        boss_attack = None
        status_message = "Impact! Press Space to retry."
        boss_projectiles.clear()
        if score > best_score:
          best_score = score
          save_best_score(best_score)
      else:
        score += int(dt * 100)

    draw_background(screen, score)
    pygame.draw.rect(screen, (139, 233, 253), player)
    for meteor in meteors:
      meteor.draw(screen)
    for bullet in bullets:
      bullet.draw(screen)
    if boss:
      boss.draw(screen)
    for projectile in boss_projectiles:
      projectile.draw(screen)
    draw_boss_attack(screen, boss_attack, boss)

    draw_text(screen, f"Score: {score}", font_medium, (255, 255, 255), (20, 20))
    draw_text(screen, f"Best: {best_score}", font_medium, (200, 210, 255), (20, 50))
    if boss:
      draw_text(screen, f"Boss HP: {boss.health}", font_medium, (255, 120, 160), (WIDTH - 180, 20))

    if game_state == "idle":
      draw_text(screen, "Meteor Escape", font_large, (255, 255, 255), (110, HEIGHT // 2 - 60))
      draw_text(screen, "Use WASD / Arrow keys", font_small, (180, 190, 255), (120, HEIGHT // 2))
      draw_text(screen, "Space to start", font_small, (180, 190, 255), (150, HEIGHT // 2 + 30))
    elif game_state == "over":
      overlay = pygame.Surface((WIDTH - 60, 180), pygame.SRCALPHA)
      overlay.fill((5, 8, 20, 220))
      screen.blit(overlay, (30, HEIGHT // 2 - 90))
      draw_text(screen, "Crash Report", font_large, (255, 107, 107), (140, HEIGHT // 2 - 60))
      draw_text(screen, f"Score: {score}", font_medium, (255, 255, 255), (170, HEIGHT // 2 - 10))
      draw_text(screen, f"Global Best: {best_score}", font_medium, (200, 210, 255), (120, HEIGHT // 2 + 25))
      draw_text(screen, "Press Space to relaunch", font_small, (150, 170, 255), (120, HEIGHT // 2 + 60))
    elif game_state == "won":
      overlay = pygame.Surface((WIDTH - 60, 200), pygame.SRCALPHA)
      overlay.fill((5, 20, 10, 230))
      screen.blit(overlay, (30, HEIGHT // 2 - 100))
      draw_text(screen, "Boss Destroyed!", font_large, (120, 255, 150), (110, HEIGHT // 2 - 60))
      draw_text(screen, f"Final Score: {score}", font_medium, (230, 255, 230), (150, HEIGHT // 2 - 10))
      draw_text(screen, "Earth is safe - for now.", font_small, (190, 230, 190), (140, HEIGHT // 2 + 25))
      draw_text(screen, "Press Space to run another mission.", font_small, (170, 210, 170), (70, HEIGHT // 2 + 55))

    draw_text(screen, status_message, font_small, (150, 170, 255), (20, HEIGHT - 30))
    pygame.display.flip()

  pygame.quit()


if __name__ == "__main__":
  main()
