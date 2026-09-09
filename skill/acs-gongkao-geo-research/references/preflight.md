# Preflight v2.2

## 目标

启动阶段只解决“范围”和“研究对象”，不开始任何正式 Measurement。

## 三个输入

1. `requested_region`
2. `seed_entities`
3. `allow_discovery_supplement`

正式输出固定为 `docx`，不再询问格式。

## Seed List

用户可以只给部分主体。每个 Seed 必须进入 Market Universe Review，最终只能是 included / observation / unresolved / excluded（excluded 需要用户明确接受）。Seed 不影响分数。

用户明确“没有名单，自己找”时，`seed_entities=[]` 且 `research_mode=blind-discovery-scan`。这种模式只能输出公开网络发现扫描，不得宣称完整地区竞争全景。

## Universe Confirmation

完成系统补充后，Agent 必须先展示四组：全国基准、本地/区域机构、Expert/IP、观察/历史主体。用户确认后才写：

```json
{
  "market_universe_confirmed": true,
  "measurement_allowed": true
}
```

未确认不得继续正式测量。
