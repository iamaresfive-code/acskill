# Preflight v2.2

## 目标

启动阶段只解决“范围”和“研究对象”，不开始任何正式 Measurement。

## 三个用户输入

1. `requested_region`
2. `seed_entities`
3. `allow_discovery_supplement`

正式输出固定为 `docx`，不再询问格式。

## Seed List

用户可以只给部分主体。每个 Seed 必须进入 Market Universe Review，最终只能是 `included / observation / unresolved`。Seed 不影响分数，也不自动进入主榜。

用户明确“没有名单，自己找”时，`seed_entities=[]` 且 `research_mode=blind-discovery-scan`。这种模式只能输出公开网络发现扫描，不得宣称完整地区竞争全景。

## Universe Confirmation

完成系统补充后，Agent 必须先展示四组：全国基准、本地/区域机构、Expert/IP、观察/历史/未解析主体。用户确认后才写：

```json
{"market_universe_confirmed": true, "measurement_allowed": true}
```

未确认不得继续正式测量。

## Stage 2 前的 Measurement Capability Check

这一步不是新增用户问题，而是执行者必须完成的运行环境自检。进入 AI Answer Measurement 前，实际探测可用 AI / AI Search 引擎，再用：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine-name \
  --context-mode native \
  --profile snapshot \
  --repeat-runs 1 \
  --allow-shared-context
```

正式发布型测量使用：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine-name \
  --context-mode native \
  --profile release \
  --repeat-runs 3 \
  --fresh-context
```

执行者只能传入已经实际验证可用的引擎。若没有可用 AI 引擎，应显式降级为 `asset-audit-only`，不得伪造第二模型。

`answer_context_mode_expected` 只能是 `native / engine-native-search / external-search-augmented`。不同 context mode 不得在同一 Run 混用。若执行者先做外部 Web Search/RAG 再把结果提供给模型，必须标 `external-search-augmented`，不能包装成模型原生 Recall。
