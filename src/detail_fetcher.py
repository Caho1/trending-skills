"""
Detail Fetcher - 抓取技能详情页
"""
import re
import time
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import requests

from src.config import FETCH_REQUEST_DELAY, SKILLS_BASE_URL


class DetailFetcher:
    """抓取技能详情页"""

    def __init__(self, timeout: int = 30, delay: float = None):
        """
        初始化

        Args:
            timeout: 请求超时时间（秒）
            delay: 请求间隔（秒），默认使用配置中的值
        """
        self.base_url = SKILLS_BASE_URL
        self.timeout = timeout
        self.delay = delay if delay is not None else FETCH_REQUEST_DELAY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; SkillsTrendingBot/1.0)"
        })

    def fetch_top20_details(self, skills: List[Dict]) -> List[Dict]:
        """
        批量抓取 Top 20 详情

        Args:
            skills: Top 20 技能列表

        Returns:
            [
                {
                    "name": "remotion-best-practices",
                    "owner": "remotion-dev/skills",
                    "url": "...",
                    "html_content": "<html>...</html>",
                    "when_to_use": "Use this skills whenever...",
                    "rules": [
                        {"file": "3d.md", "desc": "3D content in Remotion..."},
                        ...
                    ],
                    "rules_count": 27
                },
                ...
            ]
        """
        results = []
        top_n = min(20, len(skills))

        print(f"[抓取] 开始抓取 Top {top_n} 详情...")

        for i, skill in enumerate(skills[:top_n], 1):
            url = skill.get("url", "")
            if not url:
                # 尝试构建 URL
                name = skill.get("name", "")
                owner = skill.get("owner", "")
                url = f"{self.base_url}/{owner}/{name}"

            print(f"  [{i}/{top_n}] 抓取: {skill.get('name')}")

            detail = self.fetch_detail_page(url, skill)
            if detail:
                results.append(detail)
            else:
                # 即使失败也保留基本信息
                results.append({
                    "name": skill.get("name"),
                    "owner": skill.get("owner"),
                    "url": url,
                    "when_to_use": "",
                    "rules": [],
                    "rules_count": 0,
                    "error": "Failed to fetch details"
                })

            # 限速
            if i < top_n:
                time.sleep(self.delay)

        print(f"[OK] 成功抓取 {len(results)} 个技能详情")
        return results

    def fetch_detail_page(self, url: str, skill_info: Dict = None) -> Optional[Dict]:
        """
        获取单个技能详情

        Args:
            url: 技能详情页 URL
            skill_info: 技能基本信息

        Returns:
            技能详情字典或 None
        """
        if not skill_info:
            skill_info = {}

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            html_content = response.text

            # 解析页面
            detail = self.parse_detail_page(html_content, url, skill_info)
            return detail

        except requests.RequestException as e:
            print(f"    [警告] 请求失败: {e}")
            return None
        except Exception as e:
            print(f"    [警告] 解析失败: {e}")
            return None

    def parse_detail_page(self, html_content: str, url: str, skill_info: Dict) -> Dict:
        """
        解析技能详情页

        Args:
            html_content: 页面 HTML
            url: 页面 URL
            skill_info: 技能基本信息

        Returns:
            技能详情字典
        """
        soup = BeautifulSoup(html_content, "lxml")

        # 提取简介（详情页 h1 后的首段说明）
        tagline = self._extract_tagline(soup)

        # 提取 "When to use" 部分
        when_to_use = self._extract_when_to_use(soup)

        # 提取规则列表
        rules = self._extract_rules(soup)

        # 提取技能名称（如果未提供）
        name = skill_info.get("name")
        if not name:
            name = self._extract_name_from_soup(soup, url)

        # 提取拥有者
        owner = skill_info.get("owner", "unknown")

        return {
            "name": name,
            "owner": owner,
            "url": url,
            "html_content": html_content,
            "tagline": tagline,
            "when_to_use": when_to_use,
            "rules": rules,
            "rules_count": len(rules)
        }

    def _extract_tagline(self, soup: BeautifulSoup) -> str:
        """
        提取详情页简介（通常为 h1 后的第一段文字）

        Args:
            soup: BeautifulSoup 对象

        Returns:
            简介文本
        """
        h1 = soup.find("h1")
        if not h1:
            return ""

        p = h1.find_next("p")
        if not p:
            return ""

        text = p.get_text(" ", strip=True)
        return text.strip()

    def _extract_section_text(self, soup: BeautifulSoup, keywords: List[str], max_chars: int = 800) -> str:
        """
        从页面中根据标题关键词提取一个 section 的正文文本（用于 When to use 等）

        Args:
            soup: BeautifulSoup 对象
            keywords: 标题关键词（小写）
            max_chars: 最大字符数，避免抓取过长内容

        Returns:
            section 文本
        """
        headings = soup.find_all(["h2", "h3"])
        for h in headings:
            title = h.get_text(" ", strip=True).lower()
            if not title:
                continue
            if not any(k in title for k in keywords):
                continue

            parts: List[str] = []
            total = 0
            for sib in h.find_next_siblings():
                if sib.name in ("h2", "h3"):
                    break
                chunk = sib.get_text("\n", strip=True)
                if not chunk:
                    continue
                parts.append(chunk)
                total += len(chunk)
                if total >= max_chars:
                    break

            return "\n".join(parts).strip()

        return ""

    def _extract_when_to_use(self, soup: BeautifulSoup) -> str:
        """
        提取 "When to use" 部分

        Args:
            soup: BeautifulSoup 对象

        Returns:
            when_to_use 文本
        """
        # 优先使用标题定位，兼容 "When to Use This Skill" 等变体
        section = self._extract_section_text(soup, keywords=["when to use"])
        if section:
            return section

        # 兜底：基于纯文本行扫描
        lines = [l.strip() for l in soup.get_text("\n", strip=True).split("\n") if l.strip()]
        for i, line in enumerate(lines):
            if line.lower().startswith("when to use"):
                # 取后续若干行，直到遇到下一个可能的标题（简单启发式）
                collected: List[str] = []
                for next_line in lines[i + 1 : i + 15]:
                    low = next_line.lower()
                    if low.startswith(("what is ", "how to ", "install ", "commands", "related ", "reference ", "common ")):
                        break
                    collected.append(next_line)
                return "\n".join(collected).strip()

        return ""

    def _extract_rules(self, soup: BeautifulSoup) -> List[Dict]:
        """
        提取规则列表

        Args:
            soup: BeautifulSoup 对象

        Returns:
            规则列表
        """
        rules = []

        # 尝试找到规则列表
        # 通常在 "How to use" 或类似的标题下
        list_selectors = [
            "ul",
            "ol",
            '[class*="rules"]',
            '[class*="list"]',
        ]

        for selector in list_selectors:
            lists = soup.select(selector)

            for lst in lists:
                items = lst.find_all("li", recursive=False)
                if len(items) >= 3:  # 至少 3 项才认为是规则列表
                    for item in items:
                        link = item.find("a", href=True)
                        if link:
                            href = link.get("href", "")
                            text = link.get_text(strip=True)
                            # 描述可能在链接后面
                            desc = item.get_text(strip=True).replace(text, "", 1).strip()

                            rules.append({
                                "file": href.split("/")[-1] if href else text,
                                "desc": desc or text
                            })

                    if rules:
                        return rules

        # 备用方案：从 HTML 中提取所有看起来像规则的链接
        pattern = r'rules/([a-z0-9_-]+)\.md'
        matches = re.finditer(pattern, str(soup))

        for match in matches:
            rules.append({
                "file": f"{match.group(1)}.md",
                "desc": f"Rule: {match.group(1)}"
            })

        return rules

    def _extract_name_from_soup(self, soup: BeautifulSoup, url: str) -> str:
        """
        从 URL 或页面中提取技能名称

        Args:
            soup: BeautifulSoup 对象
            url: 页面 URL

        Returns:
            技能名称
        """
        # 从 URL 提取
        parts = url.strip("/").split("/")
        if len(parts) >= 1:
            return parts[-1]

        # 从页面标题提取
        title = soup.find("title")
        if title:
            title_text = title.get_text()
            # 通常格式是 "skill-name by owner"
            name = title_text.split(" by ")[0].strip()
            return name

        return "unknown"

    def get_skill_detail_summary(self, detail: Dict) -> str:
        """
        获取技能详情摘要（用于 AI 分析）

        Args:
            detail: 技能详情

        Returns:
            摘要文本
        """
        lines = [
            f"【技能名称】{detail.get('name')}",
            f"【拥有者】{detail.get('owner')}",
            f"【URL】{detail.get('url')}",
        ]

        if detail.get("when_to_use"):
            lines.append(f"\n【用途说明】")
            lines.append(detail.get("when_to_use"))

        if detail.get("rules"):
            lines.append(f"\n【规则列表】({len(detail.get('rules'))} 条)")
            for rule in detail.get("rules")[:10]:  # 最多显示 10 条
                lines.append(f"  - {rule.get('file')}: {rule.get('desc')}")

            if len(detail.get("rules")) > 10:
                lines.append(f"  ... 还有 {len(detail.get('rules')) - 10} 条规则")

        return "\n".join(lines)


def fetch_details(skills: List[Dict]) -> List[Dict]:
    """便捷函数：获取技能详情"""
    fetcher = DetailFetcher()
    return fetcher.fetch_top20_details(skills)
