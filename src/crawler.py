import asyncio
import random
import re
import ssl
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from logging import INFO, Formatter, StreamHandler, getLogger

import aiohttp
import certifi
import fire


def setup_logger(name, level=INFO):
    """
    ロガーを設定する関数

    Args:
        name (str): ロガーの名前
        level (int): ログレベル（デフォルト: INFO）

    Returns:
        logging.Logger: 設定されたロガー
    """
    logger = getLogger(name)
    logger.setLevel(level)
    if not logger.hasHandlers():

        handler = StreamHandler()
        handler.setLevel(level)
        formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger(__name__)


async def fetch(
    session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore
) -> str:
    """
    指定されたURLからHTMLを取得する関数
    :param session: aiohttp.ClientSession
    :param url: str
    :param semaphore:asyncio.Semaphore
    :return: str
    """
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                await asyncio.sleep(0.1)
                return await response.text()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Client response error {e.status}: {url}")
            if e.status == 404:
                return ""
        except aiohttp.ClientConnectionError:
            logger.error(f"Connection error: {url}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout when fetching: {url}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return ""


def get_links(html: str) -> list[str]:
    """
    HTMLからWikipediaのリンクを取得する関数。
    日付や年を含むリンクは除外され、取得したリンクはランダムに並べ替えられる。

    Args:
        html (str): HTMLテキスト

    Returns:
        list[str]: 取得したリンクのリスト
    """
    pattern = r'<a href="(/wiki/[^:"]+)"'
    links = re.findall(pattern, html)
    decoded_links = [urllib.parse.unquote(link) for link in links]
    filtered_links = [
        link
        for link in decoded_links
        if not re.search(r"\d{4}年|\d{1,2}月(?:\d{1,2}日)?", link) and ":" not in link
    ]
    random.shuffle(filtered_links)
    return [link.split("/")[-1] for link in filtered_links]


async def find_path(start_title: str, end_title: str) -> list[str]:
    """
    指定された開始ページから終了ページまでのパスを探索する関数
    :param start_title: str
    :param end_title: str
    :return: list[str]
    """
    base_url = "https://ja.wikipedia.org/wiki/"
    visited = {}
    queue = asyncio.PriorityQueue()
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    semaphore = asyncio.Semaphore(20)
    async with aiohttp.ClientSession(connector=connector) as session:
        with ThreadPoolExecutor() as executor:
            await queue.put((0, start_title, None))
            while not queue.empty():
                depth, title, prev_title = await queue.get()

                if title in visited:
                    continue

                visited[title] = (depth, prev_title)
                url = base_url + urllib.parse.quote(title)
                logger.info(f"Fetching: {title} (Depth: {depth})")
                try:
                    html = await fetch(session, url, semaphore)
                    links = await asyncio.get_running_loop().run_in_executor(
                        executor, get_links, html
                    )
                    tasks = []
                    for link in links:
                        if link == end_title:
                            visited[link] = (depth + 1, title)
                            path = []
                            current_title = end_title
                            while current_title is not None:
                                path.append(current_title)
                                _, current_title = visited[current_title]
                            path.reverse()
                            logger.info("Answer: " + " -> ".join(path))
                            return path
                        if link not in visited:
                            tasks.append((queue.put((depth + 1, link, title))))
                    await asyncio.gather(*tasks)
                except Exception as e:
                    logger.exception(f"Error fetching {title}: {e}")

    return []


async def find_distant_page(
        start_title: str, max_depth: int, max_results: int = 3
) -> list[tuple[str, list[str]]]:
    """
    指定された最大の深さまでのページを探索し、結果を返す関数。
    指定された結果数に達したら探索を終了する。

    Args:
        start_title (str): 開始ページのタイトル
        max_depth (int): 探索する最大の深さ
        max_results (int): 返す結果の最大数（デフォルト: 3）

    Returns:
        list[tuple[str, list[str]]]: 結果のリスト（ページタイトルとその経路）
    """
    base_url = "https://ja.wikipedia.org/wiki/"
    visited = {}
    queue = asyncio.PriorityQueue()
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    semaphore = asyncio.Semaphore(20)

    async with aiohttp.ClientSession(connector=connector) as session:
        with ThreadPoolExecutor() as executor:
            await queue.put((0, start_title, None))
            results = []

            while not queue.empty() and len(results) < max_results:
                depth, title, prev_title = await queue.get()

                if title in visited or depth > max_depth:
                    continue

                visited[title] = (depth, prev_title)
                url = base_url + urllib.parse.quote(title)
                logger.info(f"Fetching: {title} (Depth: {depth})")

                try:
                    html = await fetch(session, url, semaphore)
                    links = await asyncio.get_running_loop().run_in_executor(
                        executor, get_links, html
                    )
                    tasks = []
                    for link in links:
                        if link not in visited and depth < max_depth:
                            tasks.append(queue.put((depth + 1, link, title)))
                    await asyncio.gather(*tasks)
                except Exception as e:
                    logger.exception(f"Error fetching {title}: {e}")

                logger.info(
                    f"Progress: Visited {len(visited)} pages, {queue.qsize()} in queue"
                )

                if depth == max_depth:
                    path = []
                    current_title = title
                    while current_title is not None:
                        path.append(current_title)
                        _, current_title = visited[current_title]
                    path.reverse()
                    results.append((title, path))

    return results


async def main(
        start_title: str,
        end_title: str | None = None,
        max_depth: int | None = None,
        max_results: int = 3
) -> None:
    """
    メイン関数

    Args:
        start_title (str): 開始ページのタイトル
        end_title: str | None = None: 終了ページのタイトル（指定された場合）
        max_depth: int | None = None: 探索する最大の深さ（指定された場合）
        max_results: int: 返す結果の最大数（デフォルト: 3）
    """
    if end_title:
        path = await find_path(start_title, end_title)
        if path:
            answer = " -> ".join(path)
            logger.info(f"Found path of length {len(path)}")
        else:
            answer = f"No path found from {start_title} to {end_title}"
            logger.info(answer)
    elif max_depth:
        distant_pages = await find_distant_page(start_title, max_depth, max_results)
        answers = [f"{' -> '.join(path)}" for title, path in distant_pages]
        answer = "\n".join(answers)
        logger.info(f"Found {len(distant_pages)} pages at depth {max_depth}")
    else:
        logger.error("Please provide either end_title or max_depth.")
        return

    with open("answers.txt", "a") as file:
        file.write(answer + "\n")
    logger.info("Answer saved to answers.txt")


if __name__ == "__main__":
    fire.Fire(main)
