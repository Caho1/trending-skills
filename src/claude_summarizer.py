"""
LLM Summarizer - AI 总结和分类技能
使用 Apimart Chat Completions API（OpenAI 兼容）对技能进行分析、总结和分类
"""
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

from src.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)


# 分类定义
CATEGORIES = {
    "frontend": "前端开发",
    "backend": "后端开发",
    "mobile": "移动开发",
    "devops": "运维/部署",
    "video": "视频处理",
    "animation": "动画",
    "data": "数据处理",
    "ai": "AI/ML",
    "testing": "测试",
    "marketing": "营销/SEO",
    "documentation": "文档",
    "design": "设计",
    "database": "数据库",
    "security": "安全",
    "other": "其他"
}


SYSTEM_PROMPT = """你是一个“结构化信息抽取 + 分类”助手。
你的输出会被程序直接 json.loads 解析并写入数据库，因此必须严格遵守格式要求。

硬性规则：
- 只输出一个 JSON 数组（不要 Markdown、不要代码块、不要解释文字）。
- 每个数组元素都是一个对象，且必须包含字段：name、summary、description、use_case、solves、category、category_zh。
- name 必须与输入的技能名称完全一致（区分大小写，不要补前后缀）。
- summary：中文一句话，≤30字；不要换行；不要带引号/括号等多余符号。
- description：中文 50-100字；不要虚构未提供的具体数字/事实；信息不足时用更泛化但仍有用的描述。
- use_case：中文 1 句；描述典型使用场景与人群。
- solves：JSON 数组，3-5 个中文短语（每个尽量≤8字），去重，不要空值。
- category：只能从给定的分类 key 中选择 1 个；category_zh 必须与 category 对应。

如果输入信息不完整：宁可保守概括，也不要编造。"""


class ClaudeSummarizer:
    """AI 总结和分类技能"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """
        初始化 Apimart Chat Completions 客户端

        Args:
            api_key: API 密钥，默认从环境变量读取
            base_url: API URL（完整 chat/completions 端点），默认从环境变量读取
            model: 模型名，默认从环境变量读取
            max_retries: 最大重试次数（API 调用失败时）
            timeout: 请求超时（秒）
        """
        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE
        self.max_retries = max_retries if max_retries is not None else LLM_MAX_RETRIES
        self.timeout = timeout if timeout is not None else LLM_TIMEOUT

        if not self.api_key:
            raise ValueError("LLM_API_KEY（或 APIMART_API_KEY / OPENAI_API_KEY）环境变量未设置")

        self.session = requests.Session()
        self.system_prompt = SYSTEM_PROMPT

        # 初始化时测试 API 连通性
        self._test_connection()

    def _test_connection(self) -> None:
        """
        测试 API 连通性，发送一个最小请求验证 API key 和端点是否可用

        Raises:
            RuntimeError: API 连接失败时抛出
        """
        print(f"[测试] 正在验证 API 连通性 (endpoint: {self.base_url})...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # 发送一个最小的测试请求
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "stream": False,
        }

        try:
            resp = self.session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            # 检查响应状态
            if resp.status_code == 401:
                raise RuntimeError("API 认证失败：API key 无效")
            if resp.status_code == 400:
                # 尝试解析错误信息
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", {}).get("message", resp.text[:200])
                except Exception:
                    error_msg = resp.text[:200]
                raise RuntimeError(f"API 请求错误：{error_msg}")
            if resp.status_code >= 500:
                raise RuntimeError(f"API 服务端错误：HTTP {resp.status_code}")

            resp.raise_for_status()
            print(f"[OK] LLM 客户端初始化成功 (endpoint: {self.base_url}, model: {self.model})")

        except requests.Timeout:
            raise RuntimeError(f"API 连接超时：无法连接到 {self.base_url}")
        except requests.ConnectionError as e:
            raise RuntimeError(f"API 连接失败：{e}")

    def summarize_and_classify(self, details: List[Dict]) -> List[Dict]:
        """
        并发总结和分类技能（20并发）

        Args:
            details: 技能详情列表

        Returns:
            技能分析结果列表
        """
        if not details:
            return []

        print(f"[AI] 正在并发调用 LLM 分析 {len(details)} 个技能（20并发）...")

        results = []
        failed = []

        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_detail = {
                executor.submit(self._analyze_single_skill, detail): detail
                for detail in details
            }

            for future in as_completed(future_to_detail):
                detail = future_to_detail[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  [OK] {result['name']}")
                except Exception as e:
                    print(f"  [失败] {detail.get('name')}: {e}", file=sys.stderr)
                    failed.append(detail)

        # 对失败的使用降级方案
        for detail in failed:
            results.append(self._fallback_single(detail))

        print(f"[OK] 完成 {len(results)} 个技能分析（失败 {len(failed)} 个）")
        return results

    def _analyze_single_skill(self, detail: Dict) -> Dict:
        """分析单个技能"""
        name = detail.get("name", "")
        prompt = self._build_single_prompt(detail)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        result_text = self._chat_completions(messages)
        return self._parse_single_response(result_text, detail)

    def _build_single_prompt(self, detail: Dict) -> str:
        """构建单个技能的分析提示"""
        category_text = "\n".join([f"  - {k}: {v}" for k, v in CATEGORIES.items()])

        return f"""请分析以下技能并输出 JSON 对象：

名称: {detail.get('name')}
拥有者: {detail.get('owner')}
URL: {detail.get('url')}
用途说明: {detail.get('when_to_use', '无')}

可选分类: {category_text}

输出格式（只输出 JSON，不要其他内容）:
{{"name": "...", "summary": "中文≤30字", "description": "中文50-100字", "use_case": "使用场景", "solves": ["功能1", "功能2", "功能3"], "category": "分类key", "category_zh": "分类中文"}}"""

    def _parse_single_response(self, text: str, detail: Dict) -> Dict:
        """解析单个技能的响应"""
        name = detail.get("name", "")
        cleaned = text.strip()

        # 清理 markdown
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试提取 JSON
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(cleaned[start:end])
            else:
                raise

        # 如果返回的是数组，取第一个元素
        if isinstance(data, list):
            data = data[0] if data else {}

        # 验证分类
        category = data.get("category", "other")
        if category not in CATEGORIES:
            category = "other"

        return {
            "name": name,
            "summary": data.get("summary", f"{name} 技能"),
            "description": data.get("description", ""),
            "use_case": data.get("use_case", ""),
            "solves": data.get("solves", [])[:5] or ["待分析"],
            "category": category,
            "category_zh": CATEGORIES.get(category, "其他"),
            "rules_count": detail.get("rules_count", 0),
            "owner": detail.get("owner", ""),
            "url": detail.get("url", ""),
            "fallback": False,
        }

    def _fallback_single(self, detail: Dict) -> Dict:
        """单个技能的降级方案"""
        name = detail.get("name", "unknown")
        return {
            "name": name,
            "summary": f"{name} - AI 分析暂不可用",
            "description": f"技能名称: {name}",
            "use_case": "待分析",
            "solves": ["待分析"],
            "category": "other",
            "category_zh": "其他",
            "rules_count": detail.get("rules_count", 0),
            "owner": detail.get("owner", ""),
            "url": detail.get("url", ""),
            "fallback": True,
        }

    def _should_retry(self, exc: Exception, status_code: Optional[int]) -> bool:
        """判断是否需要重试（网络错误 / 限流 / 5xx 等）"""
        if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            return True
        if isinstance(exc, json.JSONDecodeError):
            return True
        if isinstance(exc, requests.HTTPError) and status_code is not None:
            if status_code in (408, 409, 429):
                return True
            if 500 <= status_code <= 599:
                return True
        # 兜底：某些代理会返回 200 但内容为空/格式错，允许短暂重试
        if isinstance(exc, ValueError):
            return True
        return False

    def _chat_completions(self, messages: List[Dict[str, Any]]) -> str:
        """
        调用 Apimart Chat Completions API，并带重试机制

        Returns:
            生成的文本内容（choices[0].message.content）
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            resp: Optional[requests.Response] = None
            try:
                resp = self.session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                # 429/5xx 先当作可重试错误处理
                if resp.status_code in (408, 409, 429) or resp.status_code >= 500:
                    raise requests.HTTPError(
                        f"HTTP {resp.status_code}",
                        response=resp,
                    )

                resp.raise_for_status()
                data = resp.json()

                content = (
                    (data.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content")
                )
                if not content or not isinstance(content, str):
                    raise ValueError(f"LLM 响应缺少 content: {str(data)[:500]}")

                return content

            except Exception as exc:
                last_exc = exc
                status_code = getattr(resp, "status_code", None) if resp is not None else None
                response_text = ""
                if resp is not None:
                    try:
                        response_text = (resp.text or "")[:800]
                    except Exception:
                        response_text = ""

                print(
                    f"[错误] LLM 调用失败 (第 {attempt}/{self.max_retries} 次)",
                    file=sys.stderr,
                )
                if status_code is not None:
                    print(f"       HTTP {status_code}", file=sys.stderr)
                print(f"       {exc}", file=sys.stderr)
                if response_text:
                    print(f"       响应片段: {response_text}", file=sys.stderr)

                if attempt >= self.max_retries or not self._should_retry(exc, status_code):
                    break

                sleep_s = min(20.0, (1.6 ** (attempt - 1)) + random.random())
                print(f"[重试] {sleep_s:.1f}s 后重试...", file=sys.stderr)
                time.sleep(sleep_s)

        raise last_exc or RuntimeError("LLM 调用失败")

    def _build_batch_prompt(self, details: List[Dict]) -> str:
        """
        构建批量分析的 Prompt

        Args:
            details: 技能详情列表

        Returns:
            Prompt 字符串
        """
        # 构建技能列表
        skills_text = ""
        for i, detail in enumerate(details, 1):
            skills_text += f"\n{'='*60}\n"
            skills_text += f"【技能 {i}】\n"
            skills_text += f"名称: {detail.get('name')}\n"
            skills_text += f"拥有者: {detail.get('owner')}\n"
            skills_text += f"URL: {detail.get('url')}\n"

            if detail.get("when_to_use"):
                skills_text += f"\n用途说明:\n{detail.get('when_to_use')}\n"

            if detail.get("rules"):
                skills_text += f"\n规则列表 ({len(detail.get('rules'))} 条):\n"
                for rule in detail.get("rules")[:5]:
                    skills_text += f"  - {rule.get('file')}: {rule.get('desc')}\n"
                if len(detail.get("rules")) > 5:
                    skills_text += f"  ... 还有 {len(detail.get('rules')) - 5} 条\n"

        # 构建分类说明
        category_text = "\n".join([
            f"  - {key}: {zh}"
            for key, zh in CATEGORIES.items()
        ])

        prompt = f"""请对下面 {len(details)} 个技能做信息抽取与分类，并生成结构化结果。

{skills_text}

---

【字段要求】（每个技能都要输出全部字段）
1) name: 必须与输入名称完全一致
2) summary: 中文一句话，≤30字
3) description: 中文 50-100字，不要虚构具体数字/事实
4) use_case: 中文 1 句，说明典型使用场景与人群
5) solves: JSON 数组，3-5 个中文短语（去重）
6) category: 只能从下列 key 中选择 1 个
7) category_zh: 必须与 category 对应的中文名称一致

可选分类（key: 中文名）：
{category_text}

【输出格式】
- 只输出 JSON 数组本身（不要 Markdown、不要代码块、不要任何额外文字）
- 数组长度必须为 {len(details)}，并按输入顺序输出
- 使用标准 JSON：双引号、无尾随逗号

【重要】
- 若输入信息不足，保守概括即可，但字段必须完整
"""

        return prompt

    def _parse_batch_response(self, result_text: str, original_details: List[Dict]) -> List[Dict]:
        """
        解析 LLM 的批量响应

        Args:
            result_text: LLM 响应文本
            original_details: 原始技能详情

        Returns:
            解析后的技能列表
        """
        cleaned = (result_text or "").strip()

        # 清理可能的 markdown 代码块标记（有些模型仍会包一层）
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # 多策略提取 JSON（尽量救回可解析的数组/对象）
        candidates: List[str] = [cleaned]
        bracket_start = cleaned.find("[")
        bracket_end = cleaned.rfind("]")
        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            candidates.insert(0, cleaned[bracket_start: bracket_end + 1])

        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidates.append(cleaned[brace_start: brace_end + 1])

        parsed: Any = None
        last_json_error: Optional[Exception] = None
        for cand in candidates:
            try:
                parsed = json.loads(cand)
                break
            except json.JSONDecodeError as e:
                last_json_error = e

        if parsed is None:
            print(f"[错误] JSON 解析失败: {last_json_error}", file=sys.stderr)
            print(f"       原始响应片段: {cleaned[:500]}...", file=sys.stderr)
            return self._fallback_summaries(original_details)

        results = parsed if isinstance(parsed, list) else [parsed]

        # LLM 返回的结果先按 name 建索引
        result_by_name: Dict[str, Dict[str, Any]] = {}
        for item in results:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                result_by_name[name.strip()] = item

        validated_results: List[Dict[str, Any]] = []

        # 按输入顺序输出，缺失项用保守值填充
        for original in original_details:
            name = original.get("name")
            if not name:
                continue

            raw = result_by_name.get(name, {})

            # 分类校验
            category = raw.get("category")
            if category not in CATEGORIES:
                category = "other"
            category_zh = CATEGORIES.get(category, "其他")

            # solves 清洗 + 去重
            solves_raw = raw.get("solves", [])
            if isinstance(solves_raw, str):
                normalized = (
                    solves_raw.replace("；", ",")
                    .replace("，", ",")
                    .replace("、", ",")
                    .replace("\n", ",")
                )
                solves_raw = [s.strip() for s in normalized.split(",") if s.strip()]

            solves: List[str] = []
            if isinstance(solves_raw, list):
                for s in solves_raw:
                    if s is None:
                        continue
                    s = str(s).strip()
                    if not s:
                        continue
                    if s not in solves:
                        solves.append(s)
            solves = solves[:5]
            if not solves:
                solves = ["待分析"]

            summary = raw.get("summary") or f"{name} 技能"
            if not isinstance(summary, str):
                summary = str(summary)
            summary = summary.strip().replace("\r", " ").replace("\n", " ")

            description = raw.get("description") or ""
            if not isinstance(description, str):
                description = str(description)
            description = description.strip()

            use_case = raw.get("use_case") or ""
            if not isinstance(use_case, str):
                use_case = str(use_case)
            use_case = use_case.strip()

            validated_results.append({
                "name": name,
                "summary": summary,
                "description": description,
                "use_case": use_case,
                "solves": solves,
                "category": category,
                "category_zh": category_zh,
                "rules_count": original.get("rules_count", 0),
                "owner": original.get("owner", ""),
                "url": original.get("url", ""),
                "fallback": bool(not raw),
            })

        print(f"[OK] 成功解析 {len(validated_results)} 个技能的 AI 分析")
        return validated_results

    def _fallback_summaries(self, details: List[Dict]) -> List[Dict]:
        """
        降级方案：当 AI 分析失败时使用基本信息

        Args:
            details: 技能详情列表

        Returns:
            基本的技能摘要列表
        """
        results = []

        for detail in details:
            name = detail.get("name", "unknown")
            results.append({
                "name": name,
                "summary": f"{name} - AI 分析暂不可用",
                "description": f"技能名称: {name}",
                "use_case": "待分析",
                "solves": ["待分析"],
                "category": "other",
                "category_zh": "其他",
                "rules_count": detail.get("rules_count", 0),
                "owner": detail.get("owner", ""),
                "url": detail.get("url", ""),
                "fallback": True
            })

        return results


def summarize_skills(details: List[Dict]) -> List[Dict]:
    """便捷函数：总结和分类技能"""
    summarizer = ClaudeSummarizer()
    return summarizer.summarize_and_classify(details)
