"""
HTML Reporter - 生成 HTML 邮件报告
专业邮件排版，无 emoji，符合最佳实践
"""
from typing import Dict, List


class HTMLReporter:
    """生成 HTML 邮件报告"""

    def __init__(self):
        """初始化"""
        self.base_url = "https://skills.sh"

    def generate_email_html(self, trends: Dict, date: str) -> str:
        """
        生成完整的 HTML 邮件

        Args:
            trends: 趋势数据
            date: 日期

        Returns:
            HTML 字符串
        """
        html_parts = []

        # HTML 头部
        html_parts.append(self._get_header(date))

        # Top 20 榜单
        html_parts.append(self._render_top_20(trends.get("top_20", [])))

        # Rising/Falling 两列并排
        rising = self._render_rising_top5(trends.get("rising_top5", []))
        falling = self._render_falling_top5(trends.get("falling_top5", []))
        if rising or falling:
            html_parts.append(self._render_rising_falling_section(rising, falling))

        # 新晋/掉榜
        html_parts.append(self._render_new_dropped(
            trends.get("new_entries", []),
            trends.get("dropped_entries", [])
        ))

        # 暴涨告警
        surging = trends.get("surging", [])
        if surging:
            html_parts.append(self._render_surging(surging))

        # HTML 尾部
        html_parts.append(self._get_footer(date))

        return "\n".join(html_parts)

    def _get_header(self, date: str) -> str:
        """生成 HTML 头部 - 邮件兼容内联样式"""
        # 邮件优先使用 table 布局，避免 flex/复杂 CSS 在 Outlook 等客户端渲染异常
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>技能趋势日报</title>
</head>
<body style="margin:0; padding:0; background-color:#F1F5F9; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F1F5F9; border-collapse:collapse;">
    <tr>
      <td align="center" style="padding:16px;">
        <table role="presentation" width="680" cellpadding="0" cellspacing="0" border="0" style="width:680px; max-width:680px; background-color:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; overflow:hidden; border-collapse:separate;">
          <tr>
            <td style="background-color:#2563EB; color:#FFFFFF; padding:32px 24px; text-align:center;">
              <div style="margin:0; font-size:28px; font-weight:700; line-height:1.2;">技能趋势日报</div>
              <div style="margin-top:12px; color:#BFDBFE; font-size:14px; line-height:1.4;">{date}</div>
            </td>
          </tr>"""

    def _get_footer(self, date: str) -> str:
        """生成 HTML 尾部 - 邮件兼容内联样式"""
        return """
          <tr>
            <td style="background-color:#F8FAFC; text-align:center; padding:24px; border-top:1px solid #E2E8F0;">
              <p style="margin:0; color:#64748B; font-size:13px; line-height:1.5;">
                由 <a href="https://skills.sh/trending" style="color:#2563EB; font-weight:600; text-decoration:none;">Skills.sh</a> 提供支持
              </p>
              <p style="margin:8px 0 0 0; color:#94A3B8; font-size:12px; line-height:1.5;">数据来源: skills.sh/trending</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    def _render_top_20(self, skills: List[Dict]) -> str:
        """渲染 Top 20 榜单 - 邮件兼容内联样式"""
        if not skills:
            return self._section_html("Top 20 排行榜", '<p style="text-align: center; color: #94A3B8; padding: 24px 0;">暂无数据</p>')

        # 使用表格实现两列布局（邮件兼容）
        cards = [self._format_skill_card(skill) for skill in skills[:20]]

        # 两列布局
        rows = []
        for i in range(0, len(cards), 2):
            left = cards[i]
            right = cards[i+1] if i+1 < len(cards) else '<td style="width: 50%; padding: 6px;"></td>'
            if i+1 < len(cards):
                right = f'<td style="width: 50%; padding: 6px; vertical-align: top;">{cards[i+1]}</td>'
            else:
                right = '<td style="width: 50%; padding: 6px;"></td>'
            rows.append(f'<tr><td style="width: 50%; padding: 6px; vertical-align: top;">{left}</td>{right}</tr>')

        content = f'<table style="width: 100%; border-collapse: collapse;">{"".join(rows)}</table>'
        return self._section_html("Top 20 排行榜", content)

    def _render_rising_top5(self, skills: List[Dict]) -> str:
        """渲染上升 Top 5 - 邮件兼容内联样式"""
        if not skills:
            return '<p style="color: #94A3B8; font-size: 13px; text-align: center; padding: 16px 0;">暂无数据</p>'
        cards = [self._format_compact_card(skill, trend="up") for skill in skills]
        return "".join(cards)

    def _render_falling_top5(self, skills: List[Dict]) -> str:
        """渲染下降 Top 5 - 邮件兼容内联样式"""
        if not skills:
            return '<p style="color: #94A3B8; font-size: 13px; text-align: center; padding: 16px 0;">暂无数据</p>'
        cards = [self._format_compact_card(skill, trend="down") for skill in skills]
        return "".join(cards)

    def _render_rising_falling_section(self, rising_html: str, falling_html: str) -> str:
        """渲染 Rising/Falling 两列并排 - 邮件兼容内联样式"""
        content = f'''<table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="width: 50%; padding: 0 8px 0 0; vertical-align: top;">
                    <h3 style="margin: 0 0 12px 0; font-size: 12px; font-weight: 600; color: #10B981; text-transform: uppercase; letter-spacing: 1px;">
                        <span style="display: inline-block; width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; margin-right: 8px;"></span>上升榜
                    </h3>
                    {rising_html}
                </td>
                <td style="width: 50%; padding: 0 0 0 8px; vertical-align: top;">
                    <h3 style="margin: 0 0 12px 0; font-size: 12px; font-weight: 600; color: #EF4444; text-transform: uppercase; letter-spacing: 1px;">
                        <span style="display: inline-block; width: 8px; height: 8px; background-color: #EF4444; border-radius: 50%; margin-right: 8px;"></span>下降榜
                    </h3>
                    {falling_html}
                </td>
            </tr>
        </table>'''
        return self._section_html("趋势变化", content)

    def _render_new_dropped(self, new_entries: List[Dict], dropped: List[Dict]) -> str:
        """渲染新晋/掉榜 - 邮件兼容内联样式"""
        if not new_entries and not dropped:
            return ""

        new_html = '<p style="color: #94A3B8; font-size: 13px; text-align: center; padding: 16px 0;">暂无新晋</p>'
        if new_entries:
            items = [self._format_compact_card(s, is_new=True) for s in new_entries[:10]]
            new_html = "".join(items)

        dropped_html = '<p style="color: #94A3B8; font-size: 13px; text-align: center; padding: 16px 0;">暂无掉榜</p>'
        if dropped:
            items = [self._format_dropped_card(s) for s in dropped[:10]]
            dropped_html = "".join(items)

        content = f'''<table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="width: 50%; padding: 0 8px 0 0; vertical-align: top;">
                    <h3 style="margin: 0 0 12px 0; font-size: 12px; font-weight: 600; color: #10B981; text-transform: uppercase; letter-spacing: 1px;">
                        <span style="display: inline-block; width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; margin-right: 8px;"></span>新晋
                    </h3>
                    {new_html}
                </td>
                <td style="width: 50%; padding: 0 0 0 8px; vertical-align: top;">
                    <h3 style="margin: 0 0 12px 0; font-size: 12px; font-weight: 600; color: #EF4444; text-transform: uppercase; letter-spacing: 1px;">
                        <span style="display: inline-block; width: 8px; height: 8px; background-color: #EF4444; border-radius: 50%; margin-right: 8px;"></span>掉榜
                    </h3>
                    {dropped_html}
                </td>
            </tr>
        </table>'''
        return self._section_html("新晋与掉榜", content)

    def _render_surging(self, skills: List[Dict]) -> str:
        """渲染暴涨告警 - 邮件兼容内联样式"""
        if not skills:
            return ""
        cards = [self._format_compact_card(skill, is_surging=True) for skill in skills]
        content = "".join(cards)
        return self._section_html("暴涨告警", content)

    def _format_skill_card(self, skill: Dict, show_details: bool = True) -> str:
        """格式化单个技能卡片 - 邮件兼容内联样式"""
        rank = skill.get("rank", 0)
        name = skill.get("name", "")
        rank_delta = skill.get("rank_delta", 0)
        installs = skill.get("installs", 0)
        url = skill.get("url", f"{self.base_url}/{skill.get('owner', '')}/{name}")

        # 排名变化徽章
        if rank_delta > 0:
            rank_badge = f'<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 10px; background-color: #D1FAE5; color: #059669;">+{rank_delta}</span>'
        elif rank_delta < 0:
            rank_badge = f'<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 10px; background-color: #FEE2E2; color: #DC2626;">{rank_delta}</span>'
        else:
            rank_badge = '<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 10px; background-color: #F1F5F9; color: #64748B;">-</span>'

        # 安装量格式化
        installs_display = f"{installs/1000:.1f}k" if installs >= 1000 else f"{installs:,}"

        # 分类标签
        category = skill.get("category_zh", "")
        cat_html = f'<span style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 500; border-radius: 12px; background-color: #DBEAFE; color: #2563EB;">{category}</span>' if category else ""

        # 摘要
        summary = skill.get("summary", "")
        sum_html = f'<p style="margin: 0 0 8px 0; color: #475569; font-size: 13px; line-height: 1.5;">{summary}</p>' if summary else ""

        # 标签
        solves = skill.get("solves", [])[:3]
        tags = "".join([f'<span style="display: inline-block; padding: 3px 8px; margin: 2px; font-size: 11px; background-color: #F1F5F9; color: #475569; border-radius: 4px;">{s}</span>' for s in solves])
        tags_html = f'<div style="margin-top: 8px;">{tags}</div>' if solves else ""

        return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; border-collapse:separate; border-spacing:0; background-color:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px;">
            <tr>
                <td style="padding:12px 14px; background-color:#F8FAFC; border-bottom:1px solid #F1F5F9;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
                        <tr>
                            <td style="width:52px; white-space:nowrap; font-size:16px; font-weight:700; color:#2563EB;">#{rank}</td>
                            <td style="font-size:14px; font-weight:600; line-height:1.4; color:#1E293B; padding-right:8px;">
                                <a href="{url}" style="color:#1E293B; text-decoration:none;">{name}</a>
                            </td>
                            <td align="right" style="white-space:nowrap;">
                                {rank_badge}
                                <span style="font-size:12px; color:#64748B; font-weight:500; margin-left:8px;">{installs_display}</span>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td style="padding:12px 14px;">
                    {sum_html}
                    <div style="margin-top:4px;">{cat_html}</div>
                    {tags_html}
                </td>
            </tr>
        </table>'''

    def _format_compact_card(self, skill: Dict, trend: str = None, is_new: bool = False, is_surging: bool = False) -> str:
        """格式化紧凑卡片 - 邮件兼容内联样式"""
        rank = skill.get("rank", 0)
        name = skill.get("name", "")
        url = skill.get("url", f"{self.base_url}/{skill.get('owner', '')}/{name}")
        installs = skill.get("installs", 0)
        installs_display = f"{installs/1000:.1f}k" if installs >= 1000 else f"{installs:,}"

        # 徽章样式
        if is_new:
            badge = '<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 700; border-radius: 10px; background-color: #10B981; color: #FFFFFF;">新</span>'
        elif is_surging:
            rate = skill.get("installs_rate", 0)
            badge = f'<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 700; border-radius: 10px; background-color: #F97316; color: #FFFFFF;">+{int(rate*100)}%</span>'
        elif trend == "up":
            delta = skill.get("rank_delta", 0)
            badge = f'<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 10px; background-color: #D1FAE5; color: #059669;">+{delta}</span>'
        elif trend == "down":
            delta = skill.get("rank_delta", 0)
            badge = f'<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 10px; background-color: #FEE2E2; color: #DC2626;">{delta}</span>'
        else:
            badge = ""

        return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
            <tr>
                <td style="padding:0 0 8px 0;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; border-collapse:separate; border-spacing:0; background-color:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px;">
                        <tr>
                            <td style="padding:10px 14px;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
                                    <tr>
                                        <td style="width:40px; white-space:nowrap; padding-right:8px;">{badge}</td>
                                        <td style="width:56px; white-space:nowrap; font-weight:700; color:#2563EB;">#{rank}</td>
                                        <td style="font-size:13px; font-weight:500; color:#1E293B; line-height:1.4;">
                                            <a href="{url}" style="color:#1E293B; text-decoration:none;">{name}</a>
                                        </td>
                                        <td align="right" style="white-space:nowrap; font-size:12px; color:#64748B;">{installs_display}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>'''

    def _format_dropped_card(self, skill: Dict) -> str:
        """格式化掉榜卡片 - 邮件兼容内联样式"""
        name = skill.get("name", "")
        yesterday_rank = skill.get("yesterday_rank", 0)

        return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
            <tr>
                <td style="padding:0 0 8px 0;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%; border-collapse:separate; border-spacing:0; background-color:#FEF2F2; border:1px solid #FECACA; border-radius:8px;">
                        <tr>
                            <td style="padding:10px 14px;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
                                    <tr>
                                        <td style="width:40px; white-space:nowrap; padding-right:8px;">
                                            <span style="display:inline-block; padding:2px 8px; font-size:11px; font-weight:700; border-radius:10px; background-color:#EF4444; color:#FFFFFF;">出</span>
                                        </td>
                                        <td style="width:56px; white-space:nowrap; font-weight:700; color:#DC2626;">#{yesterday_rank}</td>
                                        <td style="font-size:13px; color:#64748B; line-height:1.4;">{name}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>'''

    def _section_html(self, title: str, content: str) -> str:
        """生成一个完整的 section - 邮件兼容内联样式"""
        return f'''
          <tr>
            <td style="padding:24px; border-bottom:1px solid #E2E8F0;">
              <p style="margin:0 0 16px 0; font-size:12px; font-weight:600; color:#2563EB; text-transform:uppercase; letter-spacing:2px; line-height:1.4;">{title}</p>
              {content}
            </td>
          </tr>'''


def generate_email_html(trends: Dict, date: str) -> str:
    """便捷函数：生成邮件 HTML"""
    reporter = HTMLReporter()
    return reporter.generate_email_html(trends, date)
