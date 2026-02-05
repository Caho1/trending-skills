"""
Trend Analyzer - 趋势计算引擎
计算技能的排名变化、安装量变化、新晋/掉榜等趋势
"""
from typing import Dict, List
from datetime import datetime, timedelta

from src.database import Database
from src.config import SURGE_THRESHOLD


class TrendAnalyzer:
    """趋势计算引擎"""

    def __init__(self, db: Database):
        """
        初始化

        Args:
            db: 数据库实例
        """
        self.db = db

    def calculate_trends(self, today_data: List[Dict], date: str, ai_summaries: Dict = None) -> Dict:
        """
        计算今日趋势

        Args:
            today_data: 今日技能列表
            date: 今日日期 YYYY-MM-DD
            ai_summaries: AI 分析的技能详情 {name: detail}

        Returns:
            {
                "date": "2026-01-23",
                "top_20": [...],           # Top 20 (带 AI 总结)
                "rising_top5": [...],      # 上升幅度 Top 5
                "falling_top5": [...],     # 下降幅度 Top 5
                "new_entries": [...],      # 新晋榜单
                "dropped_entries": [...],  # 跌出榜单
                "surging": []              # 安装量暴涨 (>30%)
            }
        """
        # 获取昨日数据
        yesterday_data = self.db.get_yesterday_data(date)

        # 构建昨日数据的映射
        yesterday_map = {s["name"]: s for s in yesterday_data} if yesterday_data else {}

        # 计算变化
        today_with_delta = self._calculate_deltas(today_data, yesterday_map)

        # 保存今日数据（包含变化值）
        self.db.save_today_data(date, today_with_delta)

        # 获取 AI 摘要
        if ai_summaries is None:
            ai_summaries = self.db.get_all_skill_details()

        # 找出各种趋势
        results = {
            "date": date,
            "top_20": self._get_top_20_with_summary(today_with_delta, ai_summaries),
            "rising_top5": self._get_top_movers(today_with_delta, direction="up", limit=5, ai_summaries=ai_summaries),
            "falling_top5": self._get_top_movers(today_with_delta, direction="down", limit=5, ai_summaries=ai_summaries),
            "new_entries": self._find_new_entries(today_with_delta, yesterday_map, ai_summaries),
            "dropped_entries": self._find_dropped_entries(today_with_delta, yesterday_map, ai_summaries),
            "surging": self._find_surging_skills(today_with_delta, ai_summaries)
        }

        return results

    def _calculate_deltas(self, today: List[Dict], yesterday_map: Dict[str, Dict]) -> List[Dict]:
        """
        计算排名和安装量变化

        Args:
            today: 今日技能列表
            yesterday_map: 昨日技能映射 {name: skill}

        Returns:
            包含变化值的技能列表
        """
        for skill in today:
            name = skill["name"]

            if name in yesterday_map:
                yesterday_skill = yesterday_map[name]

                # 排名变化（昨日排名 - 今日排名，正数=上升）
                yesterday_rank = yesterday_skill.get("rank", skill["rank"])
                skill["rank_delta"] = yesterday_rank - skill["rank"]

                # 安装量变化
                yesterday_installs = yesterday_skill.get("installs", skill["installs"])
                installs_delta = skill["installs"] - yesterday_installs
                skill["installs_delta"] = installs_delta

                # 安装量变化率
                if yesterday_installs > 0:
                    skill["installs_rate"] = round(installs_delta / yesterday_installs, 4)
                else:
                    skill["installs_rate"] = 0
            else:
                # 新技能，没有历史数据
                skill["rank_delta"] = 0
                skill["installs_delta"] = 0
                skill["installs_rate"] = 0

        return today

    def _get_top_20_with_summary(self, today: List[Dict], ai_summaries: Dict) -> List[Dict]:
        """
        获取 Top 20 并附加 AI 摘要

        Args:
            today: 今日技能列表
            ai_summaries: AI 摘要映射

        Returns:
            Top 20 技能列表（带 AI 摘要）
        """
        top_20 = today[:20]

        for i, skill in enumerate(top_20, 1):
            # 保存原始排名，使用 TOP 20 内的排名显示
            skill["original_rank"] = skill.get("rank", i)
            skill["rank"] = i
            name = skill["name"]
            if name in ai_summaries:
                summary = ai_summaries[name]
                skill["summary"] = summary.get("summary", "")
                skill["description"] = summary.get("description", "")
                skill["use_case"] = summary.get("use_case", "")
                skill["solves"] = summary.get("solves", [])
                skill["category"] = summary.get("category", "")
                skill["category_zh"] = summary.get("category_zh", "")
            else:
                skill["summary"] = ""
                skill["description"] = ""
                skill["use_case"] = ""
                skill["solves"] = []
                skill["category"] = ""
                skill["category_zh"] = ""

        return top_20

    def _get_top_movers(self, today: List[Dict], direction: str = "up", limit: int = 5, ai_summaries: Dict = None) -> List[Dict]:
        """
        获取排名变化最大的技能

        Args:
            today: 今日技能列表
            direction: "up"=上升, "down"=下降
            limit: 返回数量
            ai_summaries: AI 摘要映射

        Returns:
            技能列表
        """
        # 过滤有变化的技能
        if direction == "up":
            movers = [s for s in today if s.get("rank_delta", 0) > 0]
            movers.sort(key=lambda x: x["rank_delta"], reverse=True)
        else:
            movers = [s for s in today if s.get("rank_delta", 0) < 0]
            movers.sort(key=lambda x: x["rank_delta"])

        # 取前 N 个
        result = movers[:limit]

        # 附加 AI 摘要
        if ai_summaries:
            for skill in result:
                name = skill["name"]
                if name in ai_summaries:
                    summary = ai_summaries[name]
                    skill["summary"] = summary.get("summary", "")
                    skill["category_zh"] = summary.get("category_zh", "")

        return result

    def _find_new_entries(self, today: List[Dict], yesterday_map: Dict[str, Dict], ai_summaries: Dict = None) -> List[Dict]:
        """
        找出新晋榜单的技能

        Args:
            today: 今日技能列表
            yesterday_map: 昨日技能映射
            ai_summaries: AI 摘要映射

        Returns:
            新晋技能列表
        """
        new_entries = [s for s in today if s["name"] not in yesterday_map]

        # 附加 AI 摘要
        if ai_summaries:
            for skill in new_entries:
                name = skill["name"]
                if name in ai_summaries:
                    summary = ai_summaries[name]
                    skill["summary"] = summary.get("summary", "")
                    skill["category_zh"] = summary.get("category_zh", "")

        return new_entries

    def _find_dropped_entries(self, today: List[Dict], yesterday_map: Dict[str, Dict], ai_summaries: Dict = None) -> List[Dict]:
        """
        找出跌出榜单的技能

        Args:
            today: 今日技能列表
            yesterday_map: 昨日技能映射
            ai_summaries: AI 摘要映射

        Returns:
            跌出榜单的技能列表
        """
        today_names = {s["name"] for s in today}
        dropped = []

        for name, yesterday_skill in yesterday_map.items():
            if name not in today_names:
                dropped.append({
                    "name": name,
                    "yesterday_rank": yesterday_skill.get("rank"),
                    "installs": yesterday_skill.get("installs", 0),
                    "url": yesterday_skill.get("url", "")
                })

                # 尝试附加 AI 摘要
                if ai_summaries and name in ai_summaries:
                    summary = ai_summaries[name]
                    dropped[-1]["summary"] = summary.get("summary", "")
                    dropped[-1]["category_zh"] = summary.get("category_zh", "")

        return dropped

    def _find_surging_skills(self, today: List[Dict], ai_summaries: Dict = None) -> List[Dict]:
        """
        找出安装量暴涨的技能

        Args:
            today: 今日技能列表
            ai_summaries: AI 摘要映射

        Returns:
            暴涨技能列表
        """
        surging = []

        for skill in today:
            rate = skill.get("installs_rate", 0)
            if rate >= SURGE_THRESHOLD:
                surging.append(skill)

        # 附加 AI 摘要
        if ai_summaries:
            for skill in surging:
                name = skill["name"]
                if name in ai_summaries:
                    summary = ai_summaries[name]
                    skill["summary"] = summary.get("summary", "")
                    skill["category_zh"] = summary.get("category_zh", "")

        return surging


def analyze_trends(today_data: List[Dict], date: str, db: Database = None, ai_summaries: Dict = None) -> Dict:
    """便捷函数：分析趋势"""
    if db is None:
        db = Database()
        db.connect()

    analyzer = TrendAnalyzer(db)
    return analyzer.calculate_trends(today_data, date, ai_summaries)
