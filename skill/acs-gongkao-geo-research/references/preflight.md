# v2.1 Preflight：启动前只确认三件事

Preflight 的目的不是增加流程感，而是防止一次完整 GEO Research Run 在研究范围、强制关注主体或正式交付格式上跑偏。

## 1. 三个必填参数

```text
requested_region
requested_entities
requested_output_format
```

并写入 `run_metadata.json`：

```json
{
  "schema_version": "2.1",
  "skill_version": "2.1",
  "run_status": "ready",
  "region_confirmed": true,
  "specified_entities_confirmed": true,
  "output_format_confirmed": true,
  "requested_region": "天津",
  "normalized_region": "天津市",
  "region_type": "municipality",
  "research_scope": ["天津市"],
  "requested_entities": ["津仕教育", "北宋教育"],
  "requested_output_format": ["docx"]
}
```

若任一确认字段不是 `true`：

```text
run_status = preflight-incomplete
```

不得进入正式完整 Research Run。

## 2. 第一问：地区

只在用户尚未提供地区时问：

> 这次要调查哪个省份、城市或区域的公考 GEO？例如广东省、天津市、广州市、珠三角、粤东地区。

标准化：

- 天津 → 天津市 → `municipality`
- 广东 → 广东省 → `province`
- 广州 → 广州市 → `city`

非行政区如珠三角、苏南、粤东：建立明确 `research_scope`；边界存在明显争议时再问用户，不自行猜模糊范围。

## 3. 第二问：指定关注主体

只在用户尚未表达“有 / 没有指定主体”时问：

> 是否有你特别希望调查的机构、品牌或老师/IP？没有就由系统自动发现；有的话可以一次输入多个名称。

指定主体：

- `user_specified=true`
- 强制进入 Candidate Pool
- 不得产生 Score Bonus
- 不得改变 Measurement 题池
- 不得提高 Evidence Grade / Entity Confidence / External Diversity / Concept Ownership / Freshness
- 最终必须有明确状态，不得静默消失

## 4. 第三问：唯一正式交付格式

只在用户尚未提供格式时问：

> 本次正式报告需要 Word（.docx）、PDF（.pdf）还是 HTML（.html）？请选择一种；只有明确要求时才生成多个格式。

映射：

- Word / docx → `docx`
- PDF → `pdf`
- HTML / 网页 → `html`

内部研究资产不算正式交付物。

## 5. 典型对话

### Case A：信息全缺

用户：

> 做一个公考 GEO 报告。

先只问：

> 这次调查哪个地区？

### Case B：部分已知

用户：

> 做天津公考 GEO。

不重复问天津。继续确认：

> 是否有指定关注的机构、品牌或老师/IP？

之后再问正式报告格式。

### Case C：只缺格式

用户：

> 做天津公考 GEO，把津仕和北宋放进去。

只问：

> 最终要 Word、PDF 还是 HTML？

### Case D：三个参数都明确

用户：

> 做天津公考 GEO，把津仕和北宋放进去，出 Word。

不再提问。直接确认：

```text
调查地区：天津市
指定关注：津仕、北宋
正式产出：Word（.docx）
```

然后开始。
