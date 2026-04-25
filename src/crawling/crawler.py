import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import urljoin
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from src.crawling.robots import is_allowed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PolicyCrawler:
    def __init__(self, config: dict):
        self.config = config.get("crawling", {})
        self.timeout = self.config.get("timeout_ms", 30000)
        self.headless = self.config.get("headless", True)
        self.user_agent = self.config.get("user_agent", "Mozilla/5.0")
        self.max_depth = self.config.get("max_bfs_depth", 2)
        self.retry_count = self.config.get("retry_count", 3)
        self.rate_limit_ms = self.config.get("rate_limit_ms", 2000)
        self.respect_robots_txt = self.config.get("respect_robots_txt", True)
        self.anchor_keywords = self.config.get("anchor_keywords", ["개인정보", "privacy"])
        self.url_heuristics = self.config.get("url_heuristics", ["privacy", "policy"])

    async def _rate_limit(self):
        if self.rate_limit_ms > 0:
            await asyncio.sleep(self.rate_limit_ms / 1000.0)

    async def _is_target_link(self, text: str, href: str) -> bool:
        text = text.lower().strip()
        href = href.lower() if href else ""
        
        for kw in self.anchor_keywords:
            if kw in text:
                return True
        for h in self.url_heuristics:
            if h in href:
                return True
        return False

    async def find_policy_url(self, page: Page, base_url: str) -> str | None:
        """현재 페이지 내에서 개인정보 처리방침 링크를 탐색합니다."""
        links = await page.locator("a").all()
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if not href or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
                
            if await self._is_target_link(text, href):
                return urljoin(base_url, href)
        return None

    async def crawl_company(self, cid: str, start_url: str, html_dir: Path) -> dict:
        """한 기업의 웹사이트를 크롤링하여 개인정보 처리방침을 찾고 HTML을 저장합니다."""
        if self.respect_robots_txt:
            allowed = await is_allowed(start_url, self.user_agent)
            if not allowed:
                logging.warning(f"[{cid}] robots.txt 블록됨: {start_url}")
                return {"cid": cid, "status": "failed", "reason": "ROBOTS_BLOCKED", "url": start_url}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()
            
            result = {"cid": cid, "status": "failed", "reason": "UNKNOWN", "url": start_url}
            
            for attempt in range(1, self.retry_count + 1):
                try:
                    logging.info(f"[{cid}] 접속 시도 {attempt}/{self.retry_count}: {start_url}")
                    await page.goto(start_url, wait_until="networkidle", timeout=self.timeout)
                    
                    policy_url = await self.find_policy_url(page, start_url)
                    
                    # BFS 1 hop으로 발견하지 못한 경우, 현재 페이지의 텍스트가 이미 처리방침일 가능성 검토
                    if not policy_url:
                        body_text = await page.inner_text("body")
                        if any(kw in body_text for kw in self.anchor_keywords):
                            policy_url = start_url # 현재 페이지가 처리방침 페이지로 추정
                            
                    if policy_url:
                        if policy_url != start_url:
                            await self._rate_limit()
                            logging.info(f"[{cid}] 처리방침 페이지 접속: {policy_url}")
                            await page.goto(policy_url, wait_until="networkidle", timeout=self.timeout)
                            
                        # HTML 저장
                        html_content = await page.content()
                        html_path = html_dir / f"{cid}_policy.html"
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                            
                        result = {"cid": cid, "status": "success", "url": policy_url, "path": str(html_path)}
                        break
                    else:
                        result["reason"] = "POLICY_NOT_FOUND"
                        break # 정책을 못 찾은 건 재시도해도 안 나옴
                        
                except PlaywrightTimeoutError:
                    result["reason"] = "TIMEOUT"
                    logging.warning(f"[{cid}] 타임아웃 발생 (시도 {attempt})")
                except Exception as e:
                    result["reason"] = f"ERROR: {str(e)}"
                    logging.error(f"[{cid}] 에러 발생: {e}")
                
                await self._rate_limit()
                
            await browser.close()
            return result

async def run_crawler(companies_df, cfg: dict, html_dir: Path, logs_dir: Path):
    crawler = PolicyCrawler(cfg)
    results = []
    
    for _, row in companies_df.iterrows():
        cid = row["company_id"]
        start_url = row["url"]
        res = await crawler.crawl_company(cid, start_url, html_dir)
        results.append(res)
        
    failures = [r for r in results if r["status"] == "failed"]
    if failures:
        with open(logs_dir / "crawling_failures.json", "w", encoding="utf-8") as f:
            json.dump(failures, f, ensure_ascii=False, indent=2)
            
    return results
