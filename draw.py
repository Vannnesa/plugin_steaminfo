import time
import tempfile
import asyncio
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from colorsys import rgb_to_hsv, hsv_to_rgb

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2

from nonebot.log import logger

from .utils import hex_to_rgb
from .models import DrawPlayerStatusData, Achievements, PlayerData

WIDTH = 400
PARENT_AVATAR_SIZE = 72
MEMBER_AVATAR_SIZE = 50

unknown_avatar_path = Path(__file__).parent / "res/unknown_avatar.jpg"
parent_status_path = Path(__file__).parent / "res/parent_status.png"
friends_search_path = Path(__file__).parent / "res/friends_search.png"
busy_path = Path(__file__).parent / "res/busy.png"
zzz_online_path = Path(__file__).parent / "res/zzz_online.png"
zzz_gaming_path = Path(__file__).parent / "res/zzz_gaming.png"
gaming_path = Path(__file__).parent / "res/gaming.png"

font_regular_path = None
font_light_path = None
font_bold_path = None


def set_font_paths(regular_path, light_path, bold_path):
    global font_regular_path, font_light_path, font_bold_path
    base_dir = Path().cwd()
    font_regular_path = str((base_dir / regular_path).resolve())
    font_light_path = str((base_dir / light_path).resolve())
    font_bold_path = str((base_dir / bold_path).resolve())


def check_font():
    if not Path(font_regular_path).exists():
        raise FileNotFoundError(f"Font file {font_regular_path} not found.")
    if not Path(font_light_path).exists():
        raise FileNotFoundError(f"Font file {font_light_path} not found.")
    if not Path(font_bold_path).exists():
        raise FileNotFoundError(f"Font file {font_bold_path} not found.")


personastate_colors = {
    0: (hex_to_rgb("969697"), hex_to_rgb("656565")),
    1: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    2: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    3: (hex_to_rgb("45778e"), hex_to_rgb("365969")),
    4: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    5: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    6: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
}


def vertically_concatenate_images(images: List[Image.Image]) -> Image.Image:
    widths, heights = zip(*(i.size for i in images))
    total_width = max(widths)
    total_height = sum(heights)

    new_image = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for image in images:
        new_image.paste(image, (0, y_offset))
        y_offset += image.size[1]

    return new_image


def draw_start_gaming(
    avatar: Image.Image, friend_name: str, game_name: str, nickname: str = None
):
    canvas = Image.open(gaming_path)
    canvas.paste(avatar.resize((66, 66), Image.BICUBIC), (15, 20))

    draw = ImageDraw.Draw(canvas)
    draw.text(
        (104, 14),
        f"{friend_name} ({nickname})" if nickname is not None else friend_name,
        font=ImageFont.truetype(font_regular_path, 19),
        fill=hex_to_rgb("e3ffc2"),
    )

    draw.text(
        (103, 42),
        "正在玩",
        font=ImageFont.truetype(font_regular_path, 17),
        fill=hex_to_rgb("969696"),
    )

    draw.text(
        (104, 66),
        game_name,
        font=ImageFont.truetype(font_bold_path, 14),
        fill=hex_to_rgb("91c257"),
    )

    return canvas


def draw_parent_status(parent_avatar: Image.Image, parent_name: str) -> Image.Image:
    parent_avatar = parent_avatar.resize(
        (PARENT_AVATAR_SIZE, PARENT_AVATAR_SIZE), Image.BICUBIC
    )

    canvas = Image.open(parent_status_path).resize((WIDTH, 120), Image.BICUBIC)

    draw = ImageDraw.Draw(canvas)

    avatar_height = 120 - 16 - PARENT_AVATAR_SIZE
    canvas.paste(parent_avatar, (16, avatar_height))

    draw.text(
        (16 + PARENT_AVATAR_SIZE + 16, avatar_height + 12),
        parent_name,
        font=ImageFont.truetype(font_bold_path, 20),
        fill=hex_to_rgb("6dcff6"),
    )

    draw.text(
        (16 + PARENT_AVATAR_SIZE + 16, avatar_height + 20 + 16),
        "在线",
        font=ImageFont.truetype(font_light_path, 18),
        fill=hex_to_rgb("4c91ac"),
    )

    return canvas


def draw_friends_search() -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, 50), hex_to_rgb("434953"))

    friends_search = Image.open(friends_search_path)

    canvas.paste(friends_search, (WIDTH - friends_search.width, 0))

    draw = ImageDraw.Draw(canvas)

    draw.text(
        (24, 10),
        "好友",
        hex_to_rgb("b7ccd5"),
        font=ImageFont.truetype(font_regular_path, 20),
    )

    return canvas


def draw_friend_status(
    friend_avatar: Image.Image,
    friend_name: str,
    status: str,
    personastate: int,
    nickname: str = None,
) -> Image.Image:
    friend_avatar = friend_avatar.resize(
        (MEMBER_AVATAR_SIZE, MEMBER_AVATAR_SIZE), Image.BICUBIC
    )

    canvas = Image.new("RGB", (WIDTH, 64), hex_to_rgb("1e2024"))

    draw = ImageDraw.Draw(canvas)

    display_name = (
        f"{friend_name} ({nickname})" if nickname is not None else friend_name
    )

    if personastate == 2:
        canvas = draw_friend_status(friend_avatar, friend_name, status, 1, nickname)
        draw = ImageDraw.Draw(canvas)

        busy = Image.open(busy_path)

        name_width = int(
            draw.textlength(display_name, font=ImageFont.truetype(font_bold_path, 20))
        )

        canvas.paste(busy, (22 + MEMBER_AVATAR_SIZE + 16 + name_width + 4, 18))

        return canvas

    if personastate == 4:
        canvas = draw_friend_status(friend_avatar, friend_name, status, 1, nickname)
        draw = ImageDraw.Draw(canvas)

        zzz = Image.open(zzz_online_path if status == "在线" else zzz_gaming_path)

        name_width = int(
            draw.textlength(display_name, font=ImageFont.truetype(font_bold_path, 20))
        )

        canvas.paste(zzz, (22 + MEMBER_AVATAR_SIZE + 16 + name_width + 8, 18))

        return canvas

    canvas.paste(friend_avatar, (22, 8))

    if status != "在线" and personastate == 1:
        fill = (hex_to_rgb("e3ffc2"), hex_to_rgb("8ebe56"))
    elif status != "离开" and personastate == 3:
        fill = (hex_to_rgb("e3ffc2"), hex_to_rgb("8ebe56"))
    else:
        fill = personastate_colors[personastate]

    draw.text(
        (22 + MEMBER_AVATAR_SIZE + 18, 12),
        display_name,
        font=ImageFont.truetype(font_bold_path, 20),
        fill=fill[0],
    )

    draw.text(
        (22 + MEMBER_AVATAR_SIZE + 16, 36),
        status,
        font=ImageFont.truetype(font_regular_path, 18),
        fill=fill[1],
    )

    return canvas


def draw_gaming_friends_status(data: List[Dict[str, str]]) -> Image.Image:
    data.sort(key=lambda x: x["status"])

    canvas = Image.new(
        "RGB",
        (WIDTH, 64 + (MEMBER_AVATAR_SIZE + 16) * len(data) + 16),
        hex_to_rgb("1e2024"),
    )

    draw = ImageDraw.Draw(canvas)

    draw.text(
        (22, 22),
        "游戏中",
        hex_to_rgb("c5d6d4"),
        font=ImageFont.truetype(font_regular_path, 22),
    )

    friends_status_list = [
        draw_friend_status(
            d["avatar"], d["name"], d["status"], d["personastate"], d["nickname"]
        )
        for d in data
    ]

    for i, friend_status in enumerate(friends_status_list):
        canvas.paste(friend_status, (0, 64 + (MEMBER_AVATAR_SIZE + 16) * i))

    return canvas


def draw_online_friends_status(data: List[Dict[str, str]]) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (WIDTH, 64 + (MEMBER_AVATAR_SIZE + 16) * len(data) + 16),
        hex_to_rgb("1e2024"),
    )

    draw = ImageDraw.Draw(canvas)

    draw.text(
        (22, 22),
        "在线好友",
        hex_to_rgb("c5d6d4"),
        font=ImageFont.truetype(font_regular_path, 22),
    )

    draw.text(
        (115, 25),
        f"({len(data)})",
        hex_to_rgb("67665c"),
        font=ImageFont.truetype(font_regular_path, 18),
    )

    friends_status_list = [
        draw_friend_status(
            d["avatar"], d["name"], d["status"], d["personastate"], d["nickname"]
        )
        for d in data
    ]

    for i, friend_status in enumerate(friends_status_list):
        canvas.paste(friend_status, (0, 64 + (MEMBER_AVATAR_SIZE + 16) * i))

    return canvas


def draw_offline_friends_status(data: List[Dict[str, str]]) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (WIDTH, 64 + (MEMBER_AVATAR_SIZE + 16) * len(data) + 16),
        hex_to_rgb("1e2024"),
    )

    draw = ImageDraw.Draw(canvas)

    draw.text(
        (22, 22),
        "离线",
        hex_to_rgb("c5d6d4"),
        font=ImageFont.truetype(font_regular_path, 22),
    )

    draw.text(
        (72, 25),
        f"({len(data)})",
        hex_to_rgb("67665c"),
        font=ImageFont.truetype(font_regular_path, 18),
    )

    friends_status_list = [
        draw_friend_status(
            d["avatar"], d["name"], d["status"], d["personastate"], d["nickname"]
        )
        for d in data
    ]

    for i, friend_status in enumerate(friends_status_list):
        canvas.paste(friend_status, (0, 64 + (MEMBER_AVATAR_SIZE + 16) * i))

    return canvas


def draw_friends_status(
    parent_avatar: Image.Image, parent_name: str, data: List[Dict[str, str]]
):
    data.sort(key=lambda x: x["personastate"])

    parent_status = draw_parent_status(parent_avatar, parent_name)
    friends_search = draw_friends_search()

    status_images: List[Image.Image] = []
    height = parent_status.height + friends_search.height

    gaming_data = [
        d
        for d in data
        if (d["personastate"] == 1 and d["status"] != "在线")
        or (d["personastate"] == 3 and d["status"] != "离开")
        or (d["personastate"] == 4 and d["status"] != "在线")
    ]

    if gaming_data:
        status_images.append(draw_gaming_friends_status(gaming_data))
        height += status_images[-1].height

    online_data = [
        d
        for d in data
        if (d["personastate"] == 1 and d["status"] == "在线")
        or (d["personastate"] == 3 and d["status"] == "离开")
        or (d["personastate"] == 4 and d["status"] == "在线")
        or (d["personastate"] in [2, 5, 6])
    ]
    online_data.sort(key=lambda x: (7 if x["personastate"] == 3 else x["personastate"]))

    if online_data:
        status_images.append(draw_online_friends_status(online_data))
        height += status_images[-1].height

    offline_data = [d for d in data if d["personastate"] == 0]
    if offline_data:
        status_images.append(draw_offline_friends_status(offline_data))
        height += status_images[-1].height

    canvas = Image.new("RGB", (WIDTH, height), hex_to_rgb("1e2024"))
    draw = ImageDraw.Draw(canvas)

    canvas.paste(parent_status, (0, 0))
    canvas.paste(friends_search, (0, parent_status.height))

    y = parent_status.height + friends_search.height

    for i, status_image in enumerate(status_images):
        canvas.paste(status_image, (0, y))
        y += status_image.height

        if i != len(status_images) - 1:
            draw.rectangle([0, y - 1, WIDTH, y], fill=hex_to_rgb("333439"))

    return canvas


def get_average_color(image: Image.Image) -> tuple[int, int, int]:
    image_np = np.array(image)
    average_color = image_np.mean(axis=(0, 1)).astype(int)
    return tuple(average_color)


def split_image(
    image: Image.Image, rows: int, cols: int
) -> tuple[list[Image.Image], int, int]:
    width, height = image.size
    piece_width = width // cols
    piece_height = height // rows
    pieces = []

    for r in range(rows):
        for c in range(cols):
            box = (
                c * piece_width,
                r * piece_height,
                (c + 1) * piece_width,
                (r + 1) * piece_height,
            )
            piece = image.crop(box)
            pieces.append(piece)

    return pieces, piece_width, piece_height


def recolor_image(image: Image.Image, rows: int, cols: int) -> Image.Image:
    total_average_color = get_average_color(image)
    pieces, piece_width, piece_height = split_image(image, rows, cols)

    diameter = min(pieces[0].size)
    radius = diameter // 2
    new_image = Image.new("RGB", image.size, total_average_color)

    for i, piece in enumerate(pieces):
        average_color = get_average_color(piece)

        row, col = divmod(i, cols)
        x = col * piece_width + piece_width // 2
        y = row * piece_height + piece_height // 2

        circle = Image.new("RGBA", (piece_width, piece_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, piece_width, piece_height), fill=average_color)

        new_image.paste(circle, (x - radius, y - radius), circle)

    new_image = new_image.filter(ImageFilter.SMOOTH)
    new_image = new_image.filter(ImageFilter.GaussianBlur(50))

    return new_image


def create_gradient_image(
    size: Tuple[int, int], color1: Tuple[int, int, int], color2: Tuple[int, int, int]
) -> Image.Image:
    color1 = tuple(max(0, min(255, c)) for c in color1)
    color2 = tuple(max(0, min(255, c)) for c in color2)
    gradient_array = np.linspace(color1, color2, size[0])
    gradient_image = np.tile(gradient_array, (size[1], 1, 1)).astype(np.uint8)
    return Image.fromarray(gradient_image, "RGBA")


def create_vertical_gradient_rect(width, height, start_color, end_color):
    if width <= 0 or height <= 0:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    start_color = tuple(max(0, min(255, c)) for c in start_color)
    end_color = tuple(max(0, min(255, c)) for c in end_color)
    gradient_array = np.linspace(start_color, end_color, num=height, dtype=np.uint8)
    gradient_array = np.tile(gradient_array[:, np.newaxis, :], (1, width, 1))
    image = Image.fromarray(gradient_array)
    return image


def random_color_offset(
    color: Tuple[int, int, int], offset: int
) -> Tuple[int, int, int]:
    return tuple(
        min(255, max(0, c + np.random.randint(-offset, offset + 1))) for c in color
    )


def get_brightest_and_darkest_color(
    image: Image.Image,
    saturation_threshold: int = 100,
    hue_difference_threshold: int = 30,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    img_hsv = np.array(image.convert("HSV"))
    vivid_mask = img_hsv[..., 1] > saturation_threshold
    vivid_pixels = img_hsv[vivid_mask]

    if len(vivid_pixels) < 10:
        return get_brightest_and_darkest_color(image, saturation_threshold - 10)

    brightest_pixel = vivid_pixels[np.argmax(vivid_pixels[..., 2])]
    darkest_pixel = vivid_pixels[np.argmin(vivid_pixels[..., 2])]

    hue_difference = abs(int(brightest_pixel[0]) - int(darkest_pixel[0]))

    if hue_difference < hue_difference_threshold:
        possible_dark_pixels = vivid_pixels[vivid_pixels[..., 0] != brightest_pixel[0]]
        if len(possible_dark_pixels) > 0:
            darkest_pixel = possible_dark_pixels[
                np.argmin(possible_dark_pixels[..., 2])
            ]

    brightest_color = (
        Image.fromarray(np.uint8([[brightest_pixel]]), "HSV")
        .convert("RGB")
        .getpixel((0, 0))
    )
    darkest_color = (
        Image.fromarray(np.uint8([[darkest_pixel]]), "HSV")
        .convert("RGB")
        .getpixel((0, 0))
    )

    return brightest_color, darkest_color


def draw_game_info(
    header: Image.Image,
    game_name: str,
    game_time: str,
    last_play_time: str,
    achievements: List[Achievements],
    completed_achievement_number: int,
    total_achievement_number: int,
    achievement_color: Tuple[int, int, int],
) -> Image.Image:
    bg = Image.new("RGBA", (880, 110 + 64 + 10), (0, 0, 0, 110))
    header = header.resize((229, 86), Image.BICUBIC)
    bg.paste(header, (10, 110 // 2 - header.height // 2))

    draw = ImageDraw.Draw(bg)

    draw.text(
        (260, 10),
        game_name,
        font=ImageFont.truetype(font_regular_path, 26),
        fill=(255, 255, 255),
    )

    font = ImageFont.truetype(font_light_path, 22)
    display_text = last_play_time
    draw.text(
        (int(bg.width - font.getlength(display_text)) - 10, 75),
        display_text,
        font=font,
        fill=(150, 150, 150),
    )

    font = ImageFont.truetype(font_light_path, 22)
    display_text = f"总时数 {game_time}"
    draw.text(
        (int(bg.width - font.getlength(display_text)) - 10, 50),
        display_text,
        font=font,
        fill=(150, 150, 150),
    )

    if completed_achievement_number is None or total_achievement_number is None:
        return bg.crop((0, 0, bg.width, 110))

    achievement_bg = Image.new("RGBA", (860, 64), achievement_color)
    draw_achievement = ImageDraw.Draw(achievement_bg)

    font = ImageFont.truetype(font_light_path, 18)
    x = 14
    draw_achievement.text(
        (x, 20),
        "成就进度",
        font=font,
        fill=(255, 255, 255, 255),
    )
    x += font.getlength("成就进度") + 10
    draw_achievement.text(
        (int(x), 20),
        f"{completed_achievement_number} / {total_achievement_number}",
        font=font,
        fill=(130, 130, 130),
    )
    x += (
        font.getlength(f"{completed_achievement_number} / {total_achievement_number}")
        + 10
    )
    progress_bar = create_progress_bar(
        completed_achievement_number / total_achievement_number, achievement_color
    )
    achievement_bg.paste(progress_bar, (int(x), 24), progress_bar)

    x = 860 - 48 * 6 - 10 * 6
    for achievement in achievements:
        achievement_image = Image.open(BytesIO(achievement["image"])).resize((48, 48))
        achievement_bg.paste(achievement_image, (x, 8))
        x += 48 + 10

    if completed_achievement_number > 6:
        font = ImageFont.truetype(font_regular_path, 22)
        display_text = f"+{completed_achievement_number - 5}"
        draw_achievement.rectangle((x, 8, x + 48, 56), fill=(34, 34, 34))
        draw_achievement.text(
            (x + 24 - font.getlength(display_text) // 2, 18),
            display_text,
            font=font,
            fill=(255, 255, 255),
        )

    bg.paste(achievement_bg, (10, 110), achievement_bg)
    return bg


async def generate_dynamic_background_video(
    static_img: Image.Image,
    video_path: str,
    output_path: Path,
) -> Optional[Path]:
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return None

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        if not out.isOpened():
            logger.error(f"无法创建输出视频文件: {output_path}")
            cap.release()
            return None

        logger.info(f"开始处理视频: {width}x{height}, {fps:.1f} FPS, {total_frames}帧")

        static_img = static_img.convert("RGBA")
        static_img = static_img.resize((width, height), Image.LANCZOS)

        alpha = static_img.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.8)
        static_img.putalpha(alpha)

        overlay = cv2.cvtColor(np.array(static_img), cv2.COLOR_RGBA2BGRA)

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

            for c in range(0, 3):
                frame_rgba[:, :, c] = frame_rgba[:, :, c] * (1 - overlay[:, :, 3] / 255.0) + overlay[:, :, c] * (overlay[:, :, 3] / 255.0)

            out.write(cv2.cvtColor(frame_rgba, cv2.COLOR_BGRA2BGR))
            frame_count += 1

            if frame_count % 50 == 0:
                logger.info(f"处理进度: {frame_count}/{total_frames} 帧")

        logger.info(f"视频处理完成，共处理 {frame_count} 帧")

        cap.release()
        out.release()
        return output_path

    except Exception as e:
        logger.error(f"视频处理失败: {str(e)}")
        try:
            cap.release()
        except Exception:
            pass
        try:
            out.release()
        except Exception:
            pass
        return None


async def draw_player_status(
    player_bg: Image.Image,
    player_avatar: Image.Image,
    player_name: str,
    player_id: str,
    player_description: str,
    player_last_two_weeks_time: str,
    player_games: List[DrawPlayerStatusData],
    player_data: PlayerData,
):
    """
    绘制玩家状态。**不在此函数中发送消息**，而是返回一个 dict：
      - {"type":"image", "path": "<file path>"} 或
      - {"type":"video", "path": "<file path>"} 或
      - {"type":"error", "message":"..."}
    由调用方负责发送文件并清理临时文件（或由调用方决定是否删除）。
    """
    try:
        if isinstance(player_bg, bytes):
            player_bg = Image.open(BytesIO(player_bg))
        if isinstance(player_avatar, bytes):
            player_avatar = Image.open(BytesIO(player_avatar))

        bg = recolor_image(
            player_bg.crop(
                (
                    (player_bg.width - 960) // 2,
                    0,
                    (player_bg.width + 960) // 2,
                    player_bg.height,
                )
            ),
            10,
            10,
        )
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.7)
        player_avatar = player_avatar.resize((200, 200))
        bg.paste(player_avatar, (40, 40))

        draw = ImageDraw.Draw(bg)

        draw.rectangle((40, 40, 240, 240), outline=(83, 164, 196), width=3)

        draw.text(
            (280, 48),
            player_name,
            font=ImageFont.truetype(font_light_path, 40),
            fill=(255, 255, 255),
        )

        draw.text(
            (280, 100),
            f"好友代码: {player_id}",
            font=ImageFont.truetype(font_regular_path, 19),
            fill=(191, 191, 191),
        )

        line_width = 0
        offset = 0
        line = ""
        for idx, char in enumerate(player_description):
            line += char
            line_width += ImageFont.truetype(font_light_path, 22).getlength(char)
            if line_width > 640 or idx == len(player_description) - 1 or char == "\n":
                draw.text(
                    (280, 132 + offset),
                    line,
                    font=ImageFont.truetype(font_light_path, 22),
                    fill=(255, 255, 255),
                )
                line = ""
                offset += 25
                line_width = 0
            if offset >= 25 * 4:
                break

        brightest_color, darkest_color = get_brightest_and_darkest_color(player_bg)
        brightest_color = tuple(map(lambda x: x - 30 if x >= 30 else 0, brightest_color))
        darkest_color = tuple(map(lambda x: x + 30 if x <= 255 - 30 else 255, darkest_color))
        brightest_color = (brightest_color[0], brightest_color[1], brightest_color[2], 128)
        brightest_color = random_color_offset(brightest_color, 20)
        darkest_color = (darkest_color[0], darkest_color[1], darkest_color[2], 128)
        darkest_color = random_color_offset(darkest_color, 20)

        hsv_achievement_color = rgb_to_hsv(*brightest_color[:3])
        achievement_color = tuple(
            map(
                int,
                hsv_to_rgb(
                    hsv_achievement_color[0],
                    hsv_achievement_color[1] * 0.85,
                    hsv_achievement_color[2] * 0.6,
                ),
            )
        )
        game_images: List[Image.Image] = []
        for idx, game in enumerate(player_games):
            game_image = Image.open(BytesIO(game["game_header"]))
            game_info = draw_game_info(
                game_image,
                game["game_name"],
                game["game_time"],
                game["last_play_time"],
                game["achievements"],
                game["completed_achievement_number"],
                game["total_achievement_number"],
                achievement_color,
            )
            game_images.append(game_info)

        bg_game = Image.new(
            "RGBA", (920, 106 + sum([game_image.height + 26 for game_image in game_images]))
        )
        draw_game = ImageDraw.Draw(bg_game)
        draw_game.rectangle((0, 0, 920, bg_game.height), fill=(0, 0, 0, 120))
        bg.paste(bg_game, (20, 272), bg_game)

        gradient = create_gradient_image((920, 50), brightest_color, darkest_color)
        bg.paste(gradient, (20, 272), gradient)

        draw.text(
            (34, 279),
            "最新动态",
            font=ImageFont.truetype(font_light_path, 26),
            fill=(255, 255, 255),
        )
        if player_last_two_weeks_time is not None:
            width = ImageFont.truetype(font_light_path, 26).getlength(player_last_two_weeks_time)
            draw.text(
                (960 - width - 34, 279),
                player_last_two_weeks_time,
                font=ImageFont.truetype(font_light_path, 26),
                fill=(255, 255, 255),
            )

        y = 350
        for idx, game_image in enumerate(game_images):
            bg.paste(
                game_image,
                ((920 - game_image.width) // 2 + 20, y),
                game_image.convert("RGBA"),
            )
            y += game_image.height + 26

        player_bg.paste(bg, ((player_bg.width - 960) // 2, 0), bg.convert("RGBA"))

        # ===========================================
        # 动态背景处理（如果存在则尝试生成 video 并返回）
        # ===========================================
        dynamic_bg_path = player_data.get("dynamic_background_path")
        if dynamic_bg_path and Path(dynamic_bg_path).exists():
            logger.info(f"检测到动态背景: {dynamic_bg_path}")
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
                    output_path = Path(temp_video.name)

                video_path = await generate_dynamic_background_video(
                    player_bg, dynamic_bg_path, output_path
                )

                if video_path and video_path.exists():
                    logger.info(f"成功生成动态背景视频: {video_path}")
                    return {"type": "video", "path": str(video_path)}
                else:
                    logger.warning("动态背景视频生成失败，继续生成静态图片")
            except Exception as e:
                logger.error(f"动态背景处理失败: {str(e)}")

        # ===========================================
        # 静态图片处理（保存并返回路径）
        # ===========================================
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_img:
                player_bg.save(temp_img, format="JPEG", quality=90)
                img_path = temp_img.name

            logger.info(f"生成静态图片: {img_path}")
            return {"type": "image", "path": img_path}
        except Exception as e:
            logger.error(f"静态图片保存失败: {str(e)}")
            return {"type": "error", "message": f"静态图片保存失败: {e}"}

    except Exception as e:
        logger.exception(f"draw_player_status 异常: {e}")
        return {"type": "error", "message": str(e)}


def rounded_rectangle(
    image: Image.Image,
    radius: int,
    border=False,
    border_width=0,
    border_color=(0, 0, 0),
):
    width, height = image.size

    image_ = Image.new("RGBA", (width + 1, height + 1), (0, 0, 0, 0))
    image_.paste(image, (0, 0), image.convert("RGBA"))

    result = Image.new("RGBA", (width + 1, height + 1), (0, 0, 0, 0))
    mask = Image.new("L", (width + 1, height + 1), 0)
    draw = ImageDraw.Draw(mask)
    image_draw = ImageDraw.Draw(result)

    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=255)

    result.paste(image_, (0, 0), mask)

    if border:
        image_draw.rounded_rectangle(
            (0, 0, width, height),
            radius=radius,
            outline=border_color,
            width=border_width,
        )

    return result


def create_progress_bar(
    progress: float, color: Tuple[int, int, int], width=186, height=16
):
    color_hsv = rgb_to_hsv(*color)

    bar_color = tuple(
        map(int, hsv_to_rgb(color_hsv[0], color_hsv[1], color_hsv[2] * 0.8))
    )
    border_color = tuple(map(lambda x: max(x - 20, 0), color))
    border_image = rounded_rectangle(
        Image.new("RGBA", (width, height), bar_color),
        8,
        border=True,
        border_width=1,
        border_color=border_color,
    )

    bar_color_top = tuple(
        map(int, hsv_to_rgb(color_hsv[0], color_hsv[1] / 2, color_hsv[2] * 5 / 2))
    )
    bar_color_bottem = tuple(
        map(int, hsv_to_rgb(color_hsv[0], color_hsv[1] / 2, color_hsv[2]))
    )

    inner_w = max(1, int(width * progress) - 6)
    bar_image = create_vertical_gradient_rect(inner_w, height - 4, bar_color_top, bar_color_bottem)
    bar_image = rounded_rectangle(bar_image, 6)

    border_image.paste(bar_image, (3, 2), bar_image)

    return border_image
