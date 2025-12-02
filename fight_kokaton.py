import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
NUM_OF_BOMBS = 5  # 爆弾の数
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


class Bird:
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -5),
        pg.K_DOWN: (0, +5),
        pg.K_LEFT: (-5, 0),
        pg.K_RIGHT: (+5, 0),
    }
    img0 = pg.transform.rotozoom(pg.image.load("fig/3.png"), 0, 0.9)
    img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん（右向き）
    imgs = {  # 0度から反時計回りに定義
        (+5, 0): img,  # 右
        (+5, -5): pg.transform.rotozoom(img, 45, 0.9),  # 右上
        (0, -5): pg.transform.rotozoom(img, 90, 0.9),  # 上
        (-5, -5): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
        (-5, 0): img0,  # 左
        (-5, +5): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
        (0, +5): pg.transform.rotozoom(img, -90, 0.9),  # 下
        (+5, +5): pg.transform.rotozoom(img, -45, 0.9),  # 右下
    }

    def __init__(self, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数 xy：こうかとん画像の初期位置座標タプル
        """
        self.img = __class__.imgs[(+5, 0)]
        self.rct: pg.Rect = self.img.get_rect()
        self.rct.center = xy
        self.dire = (+5, 0)  # 向きを追加
        self.charge = 0  # チャージ量

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.img = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.img, self.rct)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rct.move_ip(sum_mv)
        if check_bound(self.rct) != (True, True):
            self.rct.move_ip(-sum_mv[0], -sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.img = __class__.imgs[tuple(sum_mv)]
            self.dire = tuple(sum_mv)  # 向きを更新
        
        # チャージ中は赤くする
        display_img = self.img.copy()
        if self.charge > 0:
            red_intensity = min(255, int(self.charge * 2.55))  # 0-100を0-255に変換
            red_overlay = pg.Surface(display_img.get_size())
            red_overlay.fill((red_intensity, 0, 0))
            display_img.blit(red_overlay, (0, 0), special_flags=pg.BLEND_ADD)
        
        screen.blit(display_img, self.rct)


class Beam:
    """
    こうかとんが放つビームに関するクラス
    """
    def __init__(self, bird: "Bird", charge: int):
        """
        ビーム画像Surfaceを生成する
        引数1 bird：ビームを放つこうかとん（Birdインスタンス）
        引数2 charge：チャージ量（0-150）
        """
        self.charge = charge
        self.vx, self.vy = bird.dire  # こうかとんの向き
        
        # チャージ量に応じてサイズを変更（1.0倍～5.0倍）
        scale = 1.0 + (charge / 100) * 4.0
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.img = pg.transform.rotozoom(pg.image.load("fig/beam.png"), angle, scale)
        self.rct = self.img.get_rect()
        
        # 向きに応じた初期位置
        self.rct.centerx = bird.rct.centerx + bird.rct.width * self.vx // 5
        self.rct.centery = bird.rct.centery + bird.rct.height * self.vy // 5
        
        # 速度もチャージに応じて増加
        speed_multiplier = 1.0 + (charge / 100) * 2.0
        self.vx = int(self.vx * speed_multiplier)
        self.vy = int(self.vy * speed_multiplier)

    def update(self, screen: pg.Surface):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rct.move_ip(self.vx, self.vy)
        screen.blit(self.img, self.rct)


class Bomb:
    """
    爆弾に関するクラス
    """
    def __init__(self, color: tuple[int, int, int], rad: int):
        """
        引数に基づき爆弾円Surfaceを生成する
        引数1 color：爆弾円の色タプル
        引数2 rad：爆弾円の半径
        """
        self.img = pg.Surface((2*rad, 2*rad))
        pg.draw.circle(self.img, color, (rad, rad), rad)
        self.img.set_colorkey((0, 0, 0))
        self.rct = self.img.get_rect()
        self.rct.center = random.randint(0, WIDTH), random.randint(0, HEIGHT)
        self.vx, self.vy = +5, +5

    def update(self, screen: pg.Surface):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        yoko, tate = check_bound(self.rct)
        if not yoko:
            self.vx *= -1
        if not tate:
            self.vy *= -1
        self.rct.move_ip(self.vx, self.vy)
        screen.blit(self.img, self.rct)


class Score:
    """
    スコア表示に関するクラス
    """
    def __init__(self):
        """
        スコアの初期化
        """
        self.fonto = pg.font.SysFont("hgp創英角ポップ体", 30)
        self.color = (0, 0, 255)
        self.score = 0
        self.img = self.fonto.render(f"Score: {self.score}", 0, self.color)
        self.rct = self.img.get_rect()
        self.rct.center = (100, HEIGHT - 50)
    
    def update(self, screen: pg.Surface):
        """
        スコアを画面に表示
        引数 screen：画面Surface
        """
        self.img = self.fonto.render(f"Score: {self.score}", 0, self.color)
        screen.blit(self.img, self.rct)


class Particle:
    """
    爆発パーティクルに関するクラス
    """
    def __init__(self, x: int, y: int, vx: float, vy: float, color: tuple[int, int, int], size: int, life: int):
        """
        パーティクルの初期化
        引数1 x：初期x座標
        引数2 y：初期y座標
        引数3 vx：x方向の速度
        引数4 vy：y方向の速度
        引数5 color：パーティクルの色
        引数6 size：パーティクルのサイズ
        引数7 life：パーティクルの寿命
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
    
    def update(self, screen: pg.Surface):
        """
        パーティクルを更新して描画
        引数 screen：画面Surface
        """
        self.life -= 1
        if self.life > 0:
            # 重力効果
            self.vy += 0.3
            self.x += self.vx
            self.y += self.vy
            
            # フェードアウト効果
            current_size = max(1, int(self.size * (self.life / self.max_life)))
            
            # 色を徐々に暗くする
            fade_color = tuple(int(c * (self.life / self.max_life)) for c in self.color)
            
            pg.draw.circle(screen, fade_color, (int(self.x), int(self.y)), current_size)


class BigExplosion:
    """
    オーバーチャージ時の大爆発に関するクラス
    """
    def __init__(self, center: tuple[int, int], charge: int):
        """
        大爆発の初期化
        引数1 center：爆発の中心座標
        引数2 charge：チャージ量
        """
        self.particles = []
        self.center = center
        self.life = 60
        
        # チャージ量に応じてパーティクル数を増やす
        num_particles = int(100 + (charge - 150) * 2)
        
        # 爆発の色バリエーション
        colors = [
            (255, 100, 0),   # オレンジ
            (255, 50, 0),    # 赤オレンジ
            (255, 200, 0),   # 黄色
            (255, 0, 0),     # 赤
            (255, 150, 50),  # 明るいオレンジ
        ]
        
        # パーティクルを放射状に生成
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 20)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice(colors)
            size = random.randint(5, 15)
            life = random.randint(40, 70)
            
            self.particles.append(Particle(center[0], center[1], vx, vy, color, size, life))
        
        # 衝撃波用の円
        self.shockwave_radius = 0
        self.shockwave_max = 200 + (charge - 150)
    
    def update(self, screen: pg.Surface):
        """
        爆発エフェクトを更新
        引数 screen：画面Surface
        """
        self.life -= 1
        
        # 衝撃波の描画
        if self.shockwave_radius < self.shockwave_max:
            self.shockwave_radius += 15
            alpha = int(255 * (1 - self.shockwave_radius / self.shockwave_max))
            if alpha > 0:
                # 複数の衝撃波の輪を描画
                for i in range(3):
                    radius = self.shockwave_radius - i * 20
                    if radius > 0:
                        thickness = max(1, 5 - i)
                        pg.draw.circle(screen, (255, 200 - i * 50, 0), self.center, int(radius), thickness)
        
        # パーティクルの更新
        self.particles = [p for p in self.particles if p.life > 0]
        for particle in self.particles:
            particle.update(screen)


class Explosion:
    """
    爆発エフェクトに関するクラス
    """
    def __init__(self, bomb: Bomb, charge: int = 0):
        """
        爆発エフェクトの初期化
        引数1 bomb：爆発する爆弾
        引数2 charge：チャージ量
        """
        # 通常の爆発（gifベース）
        img = pg.image.load("fig/explosion.gif")
        scale = 1.0 + (charge / 100) * 2.0
        self.imgs = [
            pg.transform.rotozoom(img, 0, scale),
            pg.transform.rotozoom(pg.transform.flip(img, True, False), 0, scale),
            pg.transform.rotozoom(pg.transform.flip(img, False, True), 0, scale),
            pg.transform.rotozoom(pg.transform.flip(img, True, True), 0, scale)
        ]
        self.life = 20
        
        self.img = self.imgs[0]
        self.rct = self.img.get_rect()
        self.rct.center = bomb.rct.center if hasattr(bomb, 'rct') else bomb
    
    def update(self, screen: pg.Surface):
        """
        爆発エフェクトを表示
        引数 screen：画面Surface
        """
        self.life -= 1
        if self.life > 0:
            self.img = self.imgs[self.life % 4]
            screen.blit(self.img, self.rct)


class ChargeBar:
    """
    チャージゲージ表示に関するクラス
    """
    def __init__(self):
        """
        チャージバーの初期化
        """
        self.width = 200
        self.height = 20
        self.x = WIDTH // 2 - self.width // 2
        self.y = 30
    
    def update(self, screen: pg.Surface, charge: int):
        """
        チャージゲージを表示
        引数1 screen：画面Surface
        引数2 charge：現在のチャージ量
        """
        if charge > 0:
            # 枠
            pg.draw.rect(screen, (255, 255, 255), (self.x, self.y, self.width, self.height), 2)
            
            # ゲージの色（100以上で赤く点滅）
            if charge > 100:
                color = (255, 0, 0) if (pg.time.get_ticks() // 100) % 2 == 0 else (255, 100, 0)
            else:
                color = (0, 255, 0)
            
            # チャージ量に応じたゲージ
            bar_width = min(self.width, int(self.width * charge / 100))
            pg.draw.rect(screen, color, (self.x, self.y, bar_width, self.height))
            
            # オーバーチャージ警告
            if charge > 100:
                font = pg.font.Font(None, 30)
                warning = font.render("DANGER!", True, (255, 0, 0))
                screen.blit(warning, (self.x + self.width + 10, self.y))


def main():
    """
    ゲームのメイン処理
    """
    pg.display.set_caption("たたかえ！こうかとん")
    screen = pg.display.set_mode((WIDTH, HEIGHT))    
    bg_img = pg.image.load("fig/pg_bg.jpg")
    bird = Bird((300, 200))
    clock = pg.time.Clock()
    tmr = 0

    # 複数の爆弾を生成
    bombs = [Bomb((255, 0, 0), 10) for _ in range(NUM_OF_BOMBS)]
    # スコア表示用のインスタンスを生成
    score = Score()
    # ビームのリスト
    beams = []  
    # 爆発エフェクトのリスト
    explosions = []
    # チャージバー
    charge_bar = ChargeBar()
    # チャージ中かどうか
    charging = False

    while True:
        # イベント処理（入力の受付）
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                charging = True
                bird.charge = 0
            if event.type == pg.KEYUP and event.key == pg.K_SPACE:
                charging = False
                # 150以下の場合のみビーム発射
                if bird.charge <= 150:
                    beams.append(Beam(bird, bird.charge))
                bird.charge = 0
        
        # チャージ中はチャージ量を増やす
        if charging:
            bird.charge += 2  # 1フレームあたり2増加
            # マックス（150超過）で即座に爆発
            if bird.charge > 150:
                charging = False
                big_explosion = BigExplosion(bird.rct.center, bird.charge)
                bird.charge = 0
                
                # 爆発アニメーションを表示してからゲームオーバー
                explosion_timer = 0
                while explosion_timer < 60:  # 爆発の表示時間
                    screen.blit(bg_img, [0, 0])
                    
                    # 爆弾を表示
                    for bomb in bombs:
                        bomb.update(screen)
                    
                    # こうかとんは表示しない（消す）
                    
                    # 大爆発エフェクトを表示
                    big_explosion.update(screen)
                    
                    score.update(screen)
                    pg.display.update()
                    clock.tick(50)
                    explosion_timer += 1
                
                # ゲームオーバー表示
                bird.change_img(8, screen)
                fonto = pg.font.Font(None, 80)
                txt = fonto.render("Game Over", True, (255, 0, 0))
                screen.blit(txt, [WIDTH//2-150, HEIGHT//2])
                pg.display.update()
                time.sleep(2)
                return
        
        # 画面の描画           
        screen.blit(bg_img, [0, 0])

        # 爆弾とビームの衝突時
        for i, bomb in enumerate(bombs):
            for j, beam in enumerate(beams):
                if bomb is not None and beam is not None:
                    if beam.rct.colliderect(bomb.rct):
                        explosions.append(Explosion(bomb, beam.charge))  # 爆発生成
                        bombs[i] = None
                        beams[j] = None
                        # チャージ量に応じてスコア加算
                        score.score += int(100 * (1 + beam.charge / 50))

        # lifeが0より大きい爆発だけ残す
        explosions = [exp for exp in explosions if exp.life > 0]

        # Noneでないビームだけに更新
        beams = [beam for beam in beams if beam is not None]

        # 画面外に出たビームを削除
        beams = [beam for beam in beams if check_bound(beam.rct) == (True, True)]
        
        # Noneでない爆弾だけに更新
        bombs = [bomb for bomb in bombs if bomb is not None]

        # 各爆弾とこうかとんの衝突判定
        for bomb in bombs:
            if bird.rct.colliderect(bomb.rct):
                bird.change_img(8, screen)
                fonto = pg.font.Font(None, 80)
                txt = fonto.render("Game Over", True, (255, 0, 0))
                screen.blit(txt, [WIDTH//2-150, HEIGHT//2])
                pg.display.update()
                time.sleep(2)
                return
            
        # 各爆弾の更新
        for bomb in bombs:
            bomb.update(screen)
        
        # キャラクターの更新（移動/描画）
        key_lst = pg.key.get_pressed()
        bird.update(key_lst, screen)
        
        # 各ビームの更新
        for beam in beams:
            beam.update(screen)

        # 爆発エフェクトの更新
        for exp in explosions:
            exp.update(screen)

        # スコアの更新
        score.update(screen)
        
        # チャージバーの更新
        charge_bar.update(screen, bird.charge)
        
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()