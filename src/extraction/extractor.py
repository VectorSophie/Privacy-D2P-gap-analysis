from bs4 import BeautifulSoup, Comment
import re
from typing import List

class PolicyExtractor:
    """
    개인정보 처리방침 HTML에서 순수 본문 텍스트를 추출하는 휴리스틱 기반 추출기입니다.
    
    [Heuristic 기준 명시]
    1. Boilerplate 제거: <nav>, <footer>, <header>, <aside> 등 본문과 무관한 시맨틱 태그 제거.
    2. 불필요 요소 제거: <script>, <style>, <noscript>, <iframe>, SVG, 주석 등 렌더링/동작 요소 제거.
    3. Main Content 식별: 
       - <main> 태그가 있으면 우선 고려.
       - 없으면 id나 class에 'content', 'privacy', 'policy', 'terms', 'main', 'container'가 포함된 가장 큰 <div> 탐색.
       - 특정 컨테이너를 찾지 못하면 <body> 전체를 대상으로 추출.
    4. 문단 단위 Segmentation: 블록 레벨 태그(p, div, li, h1~h6 등)를 기준으로 텍스트를 분리하고, 
       연속된 공백문자는 단일 공백으로 정규화하여 가독성 높은 문단 리스트 반환.
    """
    
    BOILERPLATE_TAGS = ['nav', 'footer', 'header', 'aside', 'menu']
    NON_CONTENT_TAGS = ['script', 'style', 'noscript', 'iframe', 'svg', 'button', 'input', 'form']
    MAIN_HINTS = ['content', 'privacy', 'policy', 'terms', 'main', 'container']

    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, "lxml")
        
    def _clean_dom(self):
        """1 & 3 단계: Script/Style 및 Boilerplate 제거"""
        # 주석 제거
        comments = self.soup.find_all(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
            
        # Non-content 및 Boilerplate 태그 일괄 제거
        for tag in self.BOILERPLATE_TAGS + self.NON_CONTENT_TAGS:
            for element in self.soup.find_all(tag):
                element.decompose()

    def _find_main_content(self) -> BeautifulSoup:
        """4 단계: Heuristic 기반 본문 컨테이너 탐색"""
        # 1. 시맨틱 <main> 태그 확인
        main_tag = self.soup.find("main")
        if main_tag:
            return main_tag
            
        # 2. id/class 휴리스틱 기반 가장 적합한(내용이 가장 긴) div 탐색
        candidates = []
        for div in self.soup.find_all("div"):
            attr_str = " ".join(div.get("class", [])) + " " + div.get("id", "")
            attr_str = attr_str.lower()
            if any(hint in attr_str for hint in self.MAIN_HINTS):
                # 텍스트 길이 기준으로 가중치 산정 (가장 본문이 많은 컨테이너 선택)
                text_len = len(div.get_text(strip=True))
                candidates.append((text_len, div))
                
        if candidates:
            # 텍스트 길이가 가장 긴 컨테이너를 Main Content로 간주
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
            
        # 3. 휴리스틱 실패 시 body 또는 문서 전체 반환
        return self.soup.body if self.soup.body else self.soup

    def _segment_text(self, container: BeautifulSoup) -> List[str]:
        """2 & 5 단계: HTML Tag Stripping 및 문단 단위 Segmentation"""
        # 줄바꿈 태그를 실제 개행 문자로 변환
        for br in container.find_all("br"):
            br.replace_with("\n")
        
        paragraphs = []
        # get_text(separator="\n")를 활용하면 블록 레벨별로 텍스트가 줄바꿈 됨
        raw_text = container.get_text(separator="\n")
        
        for line in raw_text.split('\n'):
            cleaned = re.sub(r'\s+', ' ', line).strip()
            # 1글자 이상의 의미 있는 텍스트만 문단으로 간주
            if len(cleaned) > 1:
                paragraphs.append(cleaned)
                
        return paragraphs

    def extract(self) -> List[str]:
        """추출 파이프라인(Boilerplate 제거 -> Main 탐색 -> Segmentation) 실행"""
        self._clean_dom()
        main_container = self._find_main_content()
        return self._segment_text(main_container)
