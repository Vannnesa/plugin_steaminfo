import re
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
from nonebot.log import logger
from typing import List, Optional
from datetime import datetime, timezone

from .models import PlayerSummaries, PlayerData

STEAM_ID_OFFSET = 76561197960265728


def get_steam_id(steam_id_or_steam_friends_code: str) -> str:
    if not steam_id_or_steam_friends_code.isdigit():
        return None

    id_ = int(steam_id_or_steam_friends_code)

    if id_ < STEAM_ID_OFFSET:
        return str(id_ + STEAM_ID_OFFSET)

    return steam_id_or_steam_friends_code


async def get_steam_users_info(
    steam_ids: List[str], steam_api_key: List[str], proxy: str = None
) -> PlayerSummaries:
    if len(steam_ids) == 0:
        return {"response": {"players": []}}

    if len(steam_ids) > 100:
        # 分批获取
        result = {"response": {"players": []}}
        for i in range(0, len(steam_ids), 100):
            batch_result = await get_steam_users_info(
                steam_ids[i : i + 100], steam_api_key, proxy
            )
            result["response"]["players"].extend(batch_result["response"]["players"])
        return result

    for api_key in steam_api_key:
        try:
            async with httpx.AsyncClient(proxy=proxy) as client:
                response = await client.get(
                    f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={",".join(steam_ids)}'
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"API key {api_key} failed to get steam users info.")
        except httpx.RequestError as exc:
            logger.warning(f"API key {api_key} encountered an error: {exc}")

    logger.error("All API keys failed to get steam users info.")
    return {"response": {"players": []}}


async def _fetch(
    url: str, default: bytes, cache_file: Optional[Path] = None, proxy: str = None
) -> bytes:
    if cache_file is not None and cache_file.exists():
        return cache_file.read_bytes()
    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(url)
            if response.status_code == 200:
                if cache_file is not None:
                    cache_file.write_bytes(response.content)
                return response.content
            else:
                response.raise_for_status()
    except Exception as exc:
        logger.error(f"Failed to get image: {exc}")
        return default


async def _download_mp4(url: str, output_path: Path, proxy: str = None) -> bool:
    """异步下载MP4文件"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Referer': 'https://steamcommunity.com/',
        }
        
        async with httpx.AsyncClient(proxy=proxy, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"MP4 downloaded to {output_path}")
            return True
    except Exception as exc:
        logger.error(f"Failed to download MP4: {exc}")
        return False


def _parse_mp4_links(html: str) -> List[str]:
    """从HTML内容中解析MP4外链"""
    try:
        mp4_links = set()
        
        # 方法1：使用正则表达式直接查找绝对URL的MP4链接
        absolute_mp4_links = re.findall(r'https?://[^\s\'"]+?\.mp4', html, re.IGNORECASE)
        mp4_links.update(absolute_mp4_links)
        
        # 方法2：从HTML标签中查找可能的视频源（只获取绝对URL）
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找video标签中的source
        for video in soup.find_all('video'):
            for source in video.find_all('source'):
                src = source.get('src')
                if src and src.endswith('.mp4'):
                    mp4_links.add(src)
        
        # 方法3：查找JavaScript变量中的MP4链接（只获取绝对URL）
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                # 查找JSON格式的视频链接
                json_links = re.findall(r'"url"\s*:\s*"(https?://[^"]+?\.mp4)"', script.string, re.IGNORECASE)
                mp4_links.update(json_links)
                
                # 查找JavaScript变量中的链接
                var_links = re.findall(r'var\s+\w+\s*=\s*["\'](https?://[^"\']+?\.mp4)["\']', script.string, re.IGNORECASE)
                mp4_links.update(var_links)
        
        # 过滤掉无效链接（确保是MP4文件）
        valid_links = []
        for link in mp4_links:
            # 确保链接是有效的MP4文件
            if link.endswith('.mp4'):
                # 注意：这里不需要urljoin，因为链接已经是绝对URL
                valid_links.append(link)
        
        return valid_links
    
    except Exception as exc:
        logger.error(f"Error parsing MP4 links: {exc}")
        return []


async def get_user_data(
    steam_id: int, cache_path: Path, proxy: str = None
) -> PlayerData:
    url = f"https://steamcommunity.com/profiles/{steam_id}"
    default_background = (Path(__file__).parent / "res/bg_dots.png").read_bytes()
    default_avatar = (Path(__file__).parent / "res/unknown_avatar.jpg").read_bytes()
    default_achievement_image = (
        Path(__file__).parent / "res/default_achievement_image.png"
    ).read_bytes()
    default_header_image = (
        Path(__file__).parent / "res/default_header_image.jpg"
    ).read_bytes()

    result = {
        "description": "No information given.",
        "background": default_background,
        "avatar": default_avatar,
        "player_name": "Unknown",
        "recent_2_week_play_time": None,
        "game_data": [],
        "dynamic_background_path": None,  # 新增动态背景路径字段
    }

    local_time = datetime.now(timezone.utc).astimezone()
    utc_offset_minutes = int(local_time.utcoffset().total_seconds())
    timezone_cookie_value = f"{utc_offset_minutes},0"

    try:
        async with httpx.AsyncClient(
            proxy=proxy,
            headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
            },
            cookies={"timezoneOffset": timezone_cookie_value},
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                html = response.text
            elif response.status_code == 302:
                url = response.headers["Location"]
                response = await client.get(url)
                if response.status_code == 200:
                    html = response.text
            else:
                response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"Failed to get user data: {exc}")
        return result

    # 优先检查动态背景
    mp4_links = _parse_mp4_links(html)
    logger.info(f"Found {len(mp4_links)} potential MP4 links for dynamic background")
    
    if mp4_links:
        # 创建动态背景缓存目录
        dynamic_bg_dir = cache_path / "dynamic_bg"
        dynamic_bg_dir.mkdir(exist_ok=True, parents=True)
        
        # 尝试下载每个链接直到成功
        for idx, mp4_link in enumerate(mp4_links):
            dynamic_bg_path = dynamic_bg_dir / f"dynamic_bg_{steam_id}_{idx}.mp4"
            logger.info(f"Trying to download MP4: {mp4_link}")
            if await _download_mp4(mp4_link, dynamic_bg_path, proxy):
                result["dynamic_background_path"] = str(dynamic_bg_path)
                logger.info(f"Downloaded dynamic background: {mp4_link}")
                break
        else:
            logger.info("All dynamic background links failed to download")

    # player name
    player_name = re.search(r"<title>Steam 社区 :: (.*?)</title>", html)
    if player_name:
        result["player_name"] = player_name.group(1)

    # description
    description = re.search(
        r'<div class="profile_summary">(.*?)</div>', html, re.DOTALL | re.MULTILINE
    )
    if description:
        description = description.group(1)
        description = re.sub(r"<br>", "\n", description)
        description = re.sub(r"\t", "", description)
        result["description"] = description.strip()

    # remove emoji
    result["description"] = re.sub(r"ː.*?ː", "", result["description"])

    # remove xml
    result["description"] = re.sub(r"<.*?>", "", result["description"])

    # 只有没有动态背景时才获取静态背景
    if not result["dynamic_background_path"]:
        background_url = re.search(r"background-image: url\( \'(.*?)\' \)", html)
        if background_url:
            background_url = background_url.group(1)
            result["background"] = await _fetch(
                background_url, default_background, proxy=proxy
            )

    # avatar
    avatar_url = re.search(r'<link rel="image_src" href="(.*?)"', html)
    if avatar_url:
        avatar_url = avatar_url.group(1)
        avatar_url_split = avatar_url.split("/")
        avatar_file = cache_path / f"avatar_{avatar_url_split[-1].split('_')[0]}.jpg"
        result["avatar"] = await _fetch(
            avatar_url, default_avatar, cache_file=avatar_file, proxy=proxy
        )

    # recent 2 week play time
    play_time_text = re.search(
        r'<div class="recentgame_quicklinks recentgame_recentplaytime">\s*<div>(.*?)</div>',
        html,
    )
    if play_time_text:
        play_time_text = play_time_text.group(1)
        result["recent_2_week_play_time"] = play_time_text

    # game data
    soup = BeautifulSoup(html, "html.parser")
    game_data = []
    recent_games = soup.find_all("div", class_="recent_game")

    for game in recent_games:
        game_info = {}
        game_info["game_name"] = game.find("div", class_="game_name").text.strip()
        game_info["game_image_url"] = game.find("img", class_="game_capsule")["src"]
        game_info_split = game_info["game_image_url"].split("/")

        game_info["game_image"] = await _fetch(
            game_info["game_image_url"],
            default_header_image,
            cache_file=cache_path / f"header_{game_info_split[-2]}.jpg",
            proxy=proxy,
        )

        play_time_text = game.find("div", class_="game_info_details").text.strip()
        play_time = re.search(r"总时数\s*(.*?)\s*小时", play_time_text)
        if play_time is None:
            game_info["play_time"] = ""
        else:
            game_info["play_time"] = play_time.group(1)

        last_played = re.search(r"最后运行日期：(.*) 日", play_time_text)
        if last_played is not None:
            game_info["last_played"] = "最后运行日期：" + last_played.group(1) + " 日"
        else:
            game_info["last_played"] = "当前正在游戏"
        achievements = []
        achievement_elements = game.find_all("div", class_="game_info_achievement")
        for achievement in achievement_elements:
            if "plus_more" in achievement["class"]:
                continue
            achievement_info = {}
            achievement_info["name"] = achievement["data-tooltip-text"]
            achievement_info["image_url"] = achievement.find("img")["src"]
            achievement_info_split = achievement_info["image_url"].split("/")

            achievement_info["image"] = await _fetch(
                achievement_info["image_url"],
                default_achievement_image,
                cache_file=cache_path
                / f"achievement_{achievement_info_split[-2]}_{achievement_info_split[-1]}",
                proxy=proxy,
            )
            achievements.append(achievement_info)
        game_info["achievements"] = achievements
        game_info_achievement_summary = game.find(
            "span", class_="game_info_achievement_summary"
        )
        if game_info_achievement_summary is None:
            game_data.append(game_info)
            continue
        remain_achievement_text = game_info_achievement_summary.find(
            "span", class_="ellipsis"
        ).text
        game_info["completed_achievement_number"] = int(
            remain_achievement_text.split("/")[0].strip()
        )
        game_info["total_achievement_number"] = int(
            remain_achievement_text.split("/")[1].strip()
        )

        game_data.append(game_info)

    result["game_data"] = game_data

    return result


if __name__ == "__main__":
    from nonebot.log import logger
    import asyncio

    data = asyncio.run(get_user_data(76561199135038179, Path("cache"), None))

    with open("bg.jpg", "wb") as f:
        f.write(data["background"])
    logger.info(data["description"])