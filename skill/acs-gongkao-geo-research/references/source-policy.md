# 来源、证据与引用政策 v2.2

## A1
政府、高校、监管、官方公共数据等高质量独立来源。只支持其直接陈述的事实与关系。

## A2
机构官网、官方账号、课程/招生页。适合确认实体、产品、老师、地址和机构自述。

## B
稳定实名平台、长期内容账号、可确认身份的老师/专家内容。适合 Expert/IP、主题绑定和跨平台存在。

## C
营销榜单、软文、聚合、站群。只证明语料存在或主动铺量，不能单独证明本地市场地位、教学水平或真实口碑。

## Source Owner

每条 evidence 增加 owned / independent / platform / unknown。Owned Source Dependency 只作解释指标，不直接改 AI Visibility。

## 搜索结果与网页正文

搜索 Result title/snippet 与打开页面后的 body mention 必须分表。正文品牌列表不得回填成 SERP rank 或 AI nomination。

SERP 中出现 Stage 1 Universe 外主体时不得丢弃。先登记 Stage 2 emergent registry，再让 `serp_mentions.csv` 引用该 entity_id；实体 unresolved 也可以保留 raw SERP mention。

## AI 回答与 Mention

原始 AI Answer 必须完整保存。每条实体出现先记录 raw mention：

- `mention_rank`：原文出现顺序；
- `mention_intent`：recommended / listed / comparison / caveat / excluded；
- `resolution_status`：resolved / unresolved。

只有 resolved、entity_correct、explicit/verified alias 且 intent 为 recommended/listed 的记录进入正式 Nomination Metrics。否定、排除、比较语境仍保留审计但不加分。

## Citation Linkage

`citation_linked` 必须是实体级关联。若为 true：

1. `citation_refs` 至少有一条 URL；
2. URL 必须真实存在于该 Answer Cell 的 `citations`；
3. 采样员需确认它指向该实体、其官方域或明确绑定该实体的页面。

“该回答整体有引用”不能推导为“回答中的每个主体都被引用”。

## Answer Context

必须区分 native / engine-native-search / external-search-augmented。外部 Web Search/RAG 后再让模型回答属于 `external-search-augmented`，只能解释为外部检索增强场景下的 AI Answer Visibility，不能包装成模型原生 Recall。
