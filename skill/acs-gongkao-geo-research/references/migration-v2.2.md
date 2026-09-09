# v2.1.1 → v2.2 迁移说明

v2.2 是方法论升级，不是简单字段补丁。

## 保留
- User-specified 不加分；
- Evidence 分级与去重；
- IP 与机构分开；
- 观察组不静默消失；
- 目录幂等；
- Report Model；
- strict validation 思路。

## 替换
- Candidate Freeze → Market Universe Confirmation；
- Web Proxy Recall → AI Answer Measurement；
- 混合总榜 → 全国 / 本土 / IP 分榜；
- 公开网页五维“GEO总分” → GEO Asset Readiness；
- HTML/PDF/DOCX 三 Renderer → Single DOCX Renderer。

## 新增
- Seed-first Preflight；
- market_scope / market_role；
- ai_answers.jsonl / ai_mentions.csv；
- serp_results / serp_mentions / page_mentions 物理分离；
- 20% Blind Recheck；
- Golden Reality Check 后验发布门禁。
