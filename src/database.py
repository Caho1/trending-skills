"""
SQLite 数据库操作模块
管理技能趋势数据的存储和查询
"""
import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.config import DB_PATH, DB_RETENTION_DAYS


class Database:
    """SQLite 数据库操作类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认使用配置中的路径
        """
        self.db_path = db_path or DB_PATH
        self._ensure_db_dir()
        self.conn = None

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def connect(self):
        """建立数据库连接"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 返回字典格式

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def init_db(self) -> None:
        """初始化数据库表"""
        self.connect()
        cursor = self.conn.cursor()

        # 1. skills_daily - 每日快照表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                rank INTEGER NOT NULL,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                installs INTEGER NOT NULL,
                installs_delta INTEGER DEFAULT 0,
                installs_rate REAL DEFAULT 0,
                rank_delta INTEGER DEFAULT 0,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, name)
            )
        """)

        # 2. skills_details - 技能详情缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                summary TEXT NOT NULL,
                description TEXT,
                use_case TEXT,
                solves TEXT,
                category TEXT NOT NULL,
                category_zh TEXT NOT NULL,
                rules_count INTEGER,
                owner TEXT NOT NULL,
                url TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. skills_history - 历史趋势表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                date TEXT NOT NULL,
                rank INTEGER NOT NULL,
                installs INTEGER NOT NULL,
                UNIQUE(skill_name, date)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON skills_daily(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_name ON skills_daily(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_rank ON skills_daily(date, rank)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_details_category ON skills_details(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_details_owner ON skills_details(owner)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_name ON skills_history(skill_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_date ON skills_history(date)")

        self.conn.commit()
        print(f"[OK] 数据库初始化完成: {self.db_path}")

    def save_today_data(self, date: str, skills: List[Dict]) -> None:
        """
        保存今日数据

        Args:
            date: 日期 YYYY-MM-DD
            skills: 技能列表
        """
        self.connect()
        cursor = self.conn.cursor()

        for skill in skills:
            cursor.execute("""
                INSERT OR REPLACE INTO skills_daily
                (date, rank, name, owner, installs, installs_delta, installs_rate, rank_delta, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date,
                skill.get("rank"),
                skill.get("name"),
                skill.get("owner"),
                skill.get("installs"),
                skill.get("installs_delta", 0),
                skill.get("installs_rate", 0),
                skill.get("rank_delta", 0),
                skill.get("url", "")
            ))

            # 同时写入历史表
            cursor.execute("""
                INSERT OR REPLACE INTO skills_history
                (skill_name, date, rank, installs)
                VALUES (?, ?, ?, ?)
            """, (
                skill.get("name"),
                date,
                skill.get("rank"),
                skill.get("installs")
            ))

        self.conn.commit()
        print(f"[OK] 保存今日数据: {len(skills)} 条记录")

    def get_skills_by_date(self, date: str) -> List[Dict]:
        """
        获取指定日期的数据

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            技能列表
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT rank, name, owner, installs, installs_delta, installs_rate, rank_delta, url
            FROM skills_daily
            WHERE date = ?
            ORDER BY rank
        """, (date,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_yesterday_data(self, date: str) -> List[Dict]:
        """
        获取昨日数据

        Args:
            date: 当前日期 YYYY-MM-DD

        Returns:
            昨日的技能列表
        """
        yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.get_skills_by_date(yesterday)

    def save_skill_details(self, details: List[Dict]) -> None:
        """
        保存/更新技能详情

        Args:
            details: AI 分析的技能详情列表
        """
        self.connect()
        cursor = self.conn.cursor()

        for detail in details:
            solves_json = json.dumps(detail.get("solves", []), ensure_ascii=False)

            cursor.execute("""
                INSERT OR REPLACE INTO skills_details
                (name, summary, description, use_case, solves, category, category_zh, rules_count, owner, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detail.get("name"),
                detail.get("summary"),
                detail.get("description"),
                detail.get("use_case"),
                solves_json,
                detail.get("category"),
                detail.get("category_zh"),
                detail.get("rules_count"),
                detail.get("owner"),
                detail.get("url")
            ))

        self.conn.commit()
        print(f"[OK] 保存技能详情: {len(details)} 条记录")

    def get_skill_details(self, name: str) -> Optional[Dict]:
        """
        获取技能详情

        Args:
            name: 技能名称

        Returns:
            技能详情字典，如果不存在返回 None
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT name, summary, description, use_case, solves, category, category_zh, rules_count, owner, url
            FROM skills_details
            WHERE name = ?
        """, (name,))

        row = cursor.fetchone()
        if row:
            result = dict(row)
            # 解析 JSON 字段
            if result.get("solves"):
                result["solves"] = json.loads(result["solves"])
            return result
        return None

    def get_all_skill_details(self) -> Dict[str, Dict]:
        """
        获取所有技能详情

        Returns:
            {skill_name: detail_dict} 的字典
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT name, summary, description, use_case, solves, category, category_zh, rules_count, owner, url
            FROM skills_details
        """)

        result = {}
        for row in cursor.fetchall():
            detail = dict(row)
            if detail.get("solves"):
                detail["solves"] = json.loads(detail["solves"])
            result[detail["name"]] = detail

        return result

    def cleanup_old_data(self, days: int = None) -> int:
        """
        清理过期数据

        Args:
            days: 保留天数，默认使用配置中的值

        Returns:
            删除的记录数
        """
        retention_days = days or DB_RETENTION_DAYS
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")

        self.connect()
        cursor = self.conn.cursor()

        # 清理每日快照
        cursor.execute("""
            DELETE FROM skills_daily
            WHERE date < ?
        """, (cutoff_date,))

        deleted_daily = cursor.rowcount

        # 清理历史数据
        cursor.execute("""
            DELETE FROM skills_history
            WHERE date < ?
        """, (cutoff_date,))

        deleted_history = cursor.rowcount

        self.conn.commit()
        total_deleted = deleted_daily + deleted_history

        if total_deleted > 0:
            print(f"🗑️ 清理过期数据: {total_deleted} 条记录 (早于 {cutoff_date})")

        return total_deleted

    def get_skill_history(self, name: str, days: int = 7) -> List[Dict]:
        """
        获取技能历史趋势

        Args:
            name: 技能名称
            days: 查询天数

        Returns:
            历史数据列表，按日期升序排列
        """
        self.connect()
        cursor = self.conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT date, rank, installs
            FROM skills_history
            WHERE skill_name = ? AND date >= ?
            ORDER BY date ASC
        """, (name, cutoff_date))

        return [dict(row) for row in cursor.fetchall()]

    def get_available_dates(self, limit: int = 30) -> List[str]:
        """
        获取可用的日期列表

        Args:
            limit: 返回的最大日期数

        Returns:
            日期列表，按降序排列（最新的在前）
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT date
            FROM skills_daily
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))

        return [row["date"] for row in cursor.fetchall()]

    def get_category_stats(self, date: str) -> List[Dict]:
        """
        获取指定日期的分类统计

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            分类统计列表
        """
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT d.category, d.category_zh, COUNT(*) as count
            FROM skills_daily s
            LEFT JOIN skills_details d ON s.name = d.name
            WHERE s.date = ?
            GROUP BY d.category
            ORDER BY count DESC
        """, (date,))

        return [dict(row) for row in cursor.fetchall()]

    def get_top_movers(self, date: str, limit: int = 5) -> Dict[str, List[Dict]]:
        """
        获取排名变化最大的技能

        Args:
            date: 日期 YYYY-MM-DD
            limit: 返回数量

        Returns:
            {"rising": [...], "falling": [...]}
        """
        self.connect()
        cursor = self.conn.cursor()

        # 上升最多
        cursor.execute("""
            SELECT s.name, s.rank, s.rank_delta, d.summary, d.category
            FROM skills_daily s
            LEFT JOIN skills_details d ON s.name = d.name
            WHERE s.date = ? AND s.rank_delta > 0
            ORDER BY s.rank_delta DESC, s.rank ASC
            LIMIT ?
        """, (date, limit))

        rising = [dict(row) for row in cursor.fetchall()]

        # 下降最多
        cursor.execute("""
            SELECT s.name, s.rank, s.rank_delta, d.summary, d.category
            FROM skills_daily s
            LEFT JOIN skills_details d ON s.name = d.name
            WHERE s.date = ? AND s.rank_delta < 0
            ORDER BY s.rank_delta ASC, s.rank ASC
            LIMIT ?
        """, (date, limit))

        falling = [dict(row) for row in cursor.fetchall()]

        return {"rising": rising, "falling": falling}


def get_database() -> Database:
    """获取数据库实例（便捷函数）"""
    return Database()
