import urllib.robotparser
import urllib.parse
import asyncio
from urllib.error import URLError

async def is_allowed(url: str, user_agent: str) -> bool:
    """비동기적으로 robots.txt를 확인하여 크롤링 허용 여부를 반환합니다.

    robots.txt 파싱은 블로킹 I/O이므로 asyncio.to_thread로 감쌉니다.
    robots.txt가 없거나 네트워크 오류가 발생하면 허용(True)으로 간주하여
    크롤링이 중단되지 않도록 합니다.

    Args:
        url: 크롤링하려는 대상 URL.
        user_agent: robots.txt 규칙 조회에 사용할 User-Agent 문자열.

    Returns:
        크롤링이 허용되면 True, 차단되면 False.
    """
    parsed_url = urllib.parse.urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    
    # I/O 블로킹 방지를 위해 asyncio.to_thread 사용
    try:
        await asyncio.to_thread(rp.read)
        return rp.can_fetch(user_agent, url)
    except (URLError, Exception):
        # robots.txt가 없거나 에러가 발생하면 허용하는 것으로 간주
        return True
