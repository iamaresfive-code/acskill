#!/usr/bin/env python3
"""Generate the official Chinese customer-facing GEO DOCX report.

The report is a decision product, not a dump of research internals. Internal field names,
enums, file names and Python/JSON structures belong to the audit package, not the customer DOCX.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from fs_utils import ensure_directory

REQUIRED_NONEMPTY_LIST=("executive_summary","diagnoses","strategy","plan_90_days","risks")
REQUIRED_NONEMPTY_MAP=("measurement_protocol","robustness")

ROLE_ZH={
    "national-benchmark":"全国品牌基准","local-core":"本地核心机构","local-active":"本地活跃机构",
    "expert-ip":"老师 / 专家 IP","historical":"历史主体","observation":"观察主体","unclassified":"待分类",
}
SCOPE_ZH={"national":"全国","regional":"区域","local":"本地","unknown":"待核"}
TARGET_ZH={"institution":"机构题","ip":"老师 / IP 题","both":"机构 + 老师 / IP 双入口"}
BINDING_ZH={
    "owned-declaration":"主体主动表达","high-frequency-public-binding":"公开内容高频绑定",
    "third-party-description":"第三方稳定描述","single-incidental-mention":"单次偶发提及",
}
PROTOCOL_ZH={
    "release":"正式测量","snapshot":"快照测量","single-engine":"单引擎","limited-multi-engine":"有限多引擎","multi-engine":"多引擎",
    "native":"模型原生回答","engine-native-search":"引擎自带搜索","external-search-augmented":"外部检索增强",
    "api-isolated":"API 级隔离","product-isolated":"产品会话隔离","programmatic":"程序性隔离",
    "exact-query-repeat":"同题重复","semantic-retrieval-variants":"语义等价问法",
    "collected":"已采集网页正文","partial":"部分采集网页正文","not-collected":"未采集网页正文",
    "scoped-geo-landscape":"指定地区竞争格局","blind-discovery-scan":"盲发现扫描",
}


def _deps():
    try:
        from docx import Document
        from docx.shared import Mm,Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        return Document,Mm,Pt,WD_ALIGN_PARAGRAPH,WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT,OxmlElement,qn
    except Exception as e:raise RuntimeError(f"需要 python-docx：{e}")


def _assert_complete(model:dict):
    for key in REQUIRED_NONEMPTY_LIST:
        if not (model.get(key) or []):raise ValueError(f"report_model.{key} 为空，拒绝生成空壳报告")
    for key in REQUIRED_NONEMPTY_MAP:
        if not (model.get(key) or {}):raise ValueError(f"report_model.{key} 为空，拒绝生成空壳报告")
    if not (model.get("asset_readiness") or []):raise ValueError("report_model.asset_readiness 为空，拒绝生成空壳报告")
    if not (model.get("concept_map") or []):raise ValueError("report_model.concept_map 为空，拒绝生成空壳报告")
    if not (model.get("charts") or {}):raise ValueError("report_model.charts 为空，拒绝生成空壳报告")


def _answers(run:Path):
    p=run/"ai_answers.jsonl"
    if not p.is_file():return []
    out=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:out.append(json.loads(line))
            except Exception:pass
    return out


def _customerize(value):
    """Turn analysis-layer prose into customer-facing Chinese without serializing raw objects."""
    if value is None:return ""
    if isinstance(value,dict):
        for key in ("statement","title","name","recommendation","text"):
            if value.get(key):return _customerize(value.get(key))
        return ""
    if isinstance(value,(list,tuple)):
        return "；".join(x for x in (_customerize(v) for v in value) if x)
    text=str(value).strip().replace("**","").replace("`","")
    replacements=[
        ("AI Answer Measurement","AI 回答测量"),("AI Answer Visibility","AI 回答可见度"),("AI Answer","AI 回答"),
        ("Answer Cell","回答样本"),("Market Universe","研究主体池"),("Universe","研究主体池"),
        ("GEO Asset Readiness","GEO 资产基础"),("Asset Readiness","GEO 资产基础"),("Concept Ownership","概念占位"),
        ("Query/Retrieval Robustness","提问与检索鲁棒性"),("Query / Retrieval Robustness","提问与检索鲁棒性"),
        ("Exact Positive-set Match","正向名单完全一致率"),("Pairwise Positive-set Jaccard","不同问法推荐名单重合度"),("Jaccard","名单重合度"),
        ("Cross-model Consistency","跨模型一致性"),("Engine Coverage Rate","引擎覆盖率"),
        ("Citation Rate","引用率"),("Nomination Rate","提名率"),("Top3 Rate","前三出现率"),("First Mention Rate","首提率"),("Raw Mention Rate","原始提及率"),
        ("Expert/IP","老师 / IP"),("Expert / IP","老师 / IP"),("AI-emergent","AI 回答中新出现的主体"),("Observation","观察组"),
        ("Stage 1","研究主体确认阶段"),("Hybrid","双入口"),("Recall","记忆召回"),("N.A.","不适用"),
        ("programmatic isolation","程序性隔离"),("programmatic 隔离","程序性隔离"),("programmatic","程序性隔离"),
        ("native 上下文模式","模型原生回答模式"),("native 回答","模型原生回答"),("native","模型原生回答"),
        ("external-search-augmented","外部检索增强"),("engine-native-search","引擎自带搜索"),
        ("semantic-retrieval-variants","语义等价问法"),("exact-query-repeat","同题重复"),
        ("limited-multi-engine","有限多引擎"),("single-engine","单引擎"),("multi-engine","多引擎"),
        ("api-isolated","API 级隔离"),("product-isolated","产品会话隔离"),("not-collected","未采集"),
        ("native-recorded","原生记录"),("legacy-reconstructed","历史重建记录"),("fresh context","独立新会话"),
        ("Annotation Review","标注复核"),("Entity Resolution Recheck","实体解析复核"),("Resolution Recheck","实体解析复核"),("Citation Audit","引用审计"),
        ("owned-declaration","主体主动表达"),("high-frequency-public-binding","公开内容高频绑定"),("third-party-description","第三方稳定描述"),("single-incidental-mention","单次偶发提及"),
        ("target-specific","按测量对象分开"),("recommended + listed","推荐或正常列入名单"),("recommended","推荐"),("listed","列入名单"),
        ("institution 通道","机构通道"),("institution 组","机构题组"),("institution","机构"),
        ("unknown","暂无可核验证据"),("Tier","等级"),
    ]
    for a,b in replacements:text=text.replace(a,b)
    return re.sub(r"\s+"," ",text).strip()


def _customer_safe(text):
    """Do not send obviously engineering-only limitation lines to the customer body."""
    if not text:return False
    if re.search(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b",text):return False
    if re.search(r"\.(?:csv|jsonl?|py)\b",text,re.I):return False
    if re.search(r"\{\s*['\"]",text):return False
    return True


def render(run:Path,out:Path):
    Document,Mm,Pt,ALIGN,TALIGN,CVAL,OxmlElement,qn=_deps()
    model=json.loads((run/"report_model.json").read_text(encoding="utf-8"));_assert_complete(model)
    meta=model.get("meta",{});answers=_answers(run)
    citation_applicable=sum(len(a.get("citations") or []) for a in answers)>0
    d=Document();sec=d.sections[0]
    sec.page_width=Mm(210);sec.page_height=Mm(297);sec.top_margin=Mm(18);sec.bottom_margin=Mm(18);sec.left_margin=Mm(19);sec.right_margin=Mm(19)
    styles=d.styles
    for sname,size,bold in [("Normal",10.5,False),("Title",30,True),("Heading 1",20,True),("Heading 2",15,True),("Heading 3",12,True)]:
        s=styles[sname];s.font.name="Aptos";s.font.size=Pt(size);s.font.bold=bold;s._element.rPr.rFonts.set(qn("w:eastAsia"),"Microsoft YaHei")
    styles["Normal"].paragraph_format.line_spacing=1.42;styles["Normal"].paragraph_format.space_after=Pt(5)

    def set_run(r,size=None,bold=None):
        r.font.name="Aptos";r._element.rPr.rFonts.set(qn("w:eastAsia"),"Microsoft YaHei")
        if size:r.font.size=Pt(size)
        if bold is not None:r.bold=bold
    def page_break():d.add_page_break()
    def h(text,level=1):
        p=d.add_paragraph(style=f"Heading {level}");p.paragraph_format.keep_with_next=True;p.add_run(_customerize(text));return p
    def para(text,size=10.5,italic=False):
        p=d.add_paragraph();r=p.add_run(_customerize(text));set_run(r,size);r.italic=italic;return p
    def bullet(text):
        txt=_customerize(text)
        if not txt or not _customer_safe(txt):return None
        p=d.add_paragraph(style="List Bullet");r=p.add_run(txt);set_run(r);return p
    def set_repeat_header(row):
        trPr=row._tr.get_or_add_trPr();tblHeader=OxmlElement("w:tblHeader");tblHeader.set(qn("w:val"),"true");trPr.append(tblHeader)
    def no_split(row):
        trPr=row._tr.get_or_add_trPr();x=OxmlElement("w:cantSplit");trPr.append(x)
    def shade(cell,fill="EAF0F6"):
        tcPr=cell._tc.get_or_add_tcPr();shd=OxmlElement("w:shd");shd.set(qn("w:fill"),fill);tcPr.append(shd)
    def table(headers,rows,widths=None,font=8.5):
        t=d.add_table(rows=1,cols=len(headers));t.alignment=TALIGN.CENTER;t.style="Table Grid";set_repeat_header(t.rows[0])
        for i,x in enumerate(headers):
            c=t.rows[0].cells[i];c.text=_customerize(x);shade(c);c.vertical_alignment=CVAL.CENTER
            for p in c.paragraphs:
                for r in p.runs:set_run(r,font,True)
        for row in rows:
            cells=t.add_row().cells;no_split(t.rows[-1])
            for i,v in enumerate(row):
                cells[i].text=_customerize(v if v is not None else "");cells[i].vertical_alignment=CVAL.TOP
                for p in cells[i].paragraphs:
                    for r in p.runs:set_run(r,font)
        if widths:
            for row in t.rows:
                for i,w in enumerate(widths):row.cells[i].width=Mm(w)
        return t
    def chart(key):
        rel=(model.get("charts") or {}).get(key);p=run/rel if rel else None
        if not p or not p.is_file():raise ValueError(f"图表缺失：{rel}")
        d.add_picture(str(p),width=Mm(165));d.paragraphs[-1].alignment=ALIGN.CENTER
    def pct(v):
        try:return f"{float(v)*100:.1f}%"
        except:return "—"
    def pct_smart(v):
        try:
            x=float(v);return f"{(x*100 if abs(x)<=1 else x):.1f}%"
        except:return "—"
    def hit(r):
        m=r.get("target_metrics") or {};k=r.get("measurement_target_for_report") or ""
        row=m.get(k) or (next(iter(m.values())) if m else {})
        a=row.get("mentioned_answers");b=row.get("answer_cells");return f"{a}/{b}" if a not in (None,"") and b not in (None,"") else "—"
    def citation_value(r):return pct(r.get("citation_rate")) if citation_applicable else "不适用"
    def vis_rows(rows):
        return [[i+1,r.get("canonical_name"),hit(r),pct(r.get("nomination_rate")),pct(r.get("top3_rate")),pct(r.get("first_mention_rate")),citation_value(r),r.get("asset_readiness") or "暂不评分"] for i,r in enumerate(rows)]
    VIS_HEAD=["排名","主体","命中/样本","提名率","前三出现率","首提率","引用率","GEO资产基础"]
    VIS_W=[10,32,20,17,20,17,18,25]

    for _ in range(5):d.add_paragraph("")
    p=d.add_paragraph();p.alignment=ALIGN.CENTER;r=p.add_run(model.get("title","") or "公考 GEO 竞争格局报告");set_run(r,28,True)
    p=d.add_paragraph();p.alignment=ALIGN.CENTER;r=p.add_run("AI 可见度 × GEO 资产基础 × 概念占位");set_run(r,13)
    for text in [f"研究地区：{meta.get('normalized_region') or meta.get('requested_region','')}",f"观察日期：{meta.get('observation_date','')}","正式交付：Word / DOCX","说明：GEO 结果不代表教学质量、通过率、招生量、市场份额或一般口碑"]:
        p=d.add_paragraph();p.alignment=ALIGN.CENTER;p.add_run(text)

    from docx.enum.section import WD_SECTION
    section=d.add_section(WD_SECTION.NEW_PAGE);section.page_width=Mm(210);section.page_height=Mm(297);section.top_margin=Mm(18);section.bottom_margin=Mm(18);section.left_margin=Mm(19);section.right_margin=Mm(19);section.header.is_linked_to_previous=False;section.footer.is_linked_to_previous=False
    hp=section.header.paragraphs[0];hp.text=model.get("title","");hp.alignment=ALIGN.CENTER
    fp=section.footer.paragraphs[0];fp.alignment=ALIGN.CENTER;fp.add_run("公开信息研究 · ");fld=OxmlElement("w:fldSimple");fld.set(qn("w:instr"),"PAGE");fp._p.append(fld)
    sec.header.paragraphs[0].clear();sec.footer.paragraphs[0].clear()

    h("核心结论",1)
    k=model.get("kpis",{})
    table(["正式研究主体","全国品牌","本地/区域机构","老师 / IP","观察主体","AI 入口"],[[k.get("included_entities"),k.get("national_benchmarks"),k.get("local_institutions"),k.get("expert_ip"),k.get("observation_entities"),k.get("ai_engines")]],widths=[28,26,30,26,26,24],font=9)
    for x in model.get("executive_summary",[]):bullet(x)
    para("阅读顺序建议：先看前三类 AI 可见度排名，再看“AI 可见度 × GEO 资产基础”矩阵，最后看重点主体诊断与 90 天行动。",9.5)

    page_break();h("一、竞争格局总览",1)
    chart("universe")
    para("上图把 AI 提名率与公开 GEO 资产基础放在同一张图中。虚线为本轮样本中位数，仅用于相对比较：右上代表“资产基础与 AI 可见度都较强”；右下往往意味着公开资产已经具备，但 AI 认知尚未同步，是值得优先诊断的机会区。",9.5)

    page_break();h("二、全国品牌 AI 可见度",1);chart("national_visibility")
    rows=model.get("ai_visibility",{}).get("national_benchmarks",[]);table(VIS_HEAD,vis_rows(rows),widths=VIS_W,font=8.3)
    para("提名率表示主体在对应无品牌问题中被正向推荐或正常列入名单的比例；“命中/样本”给出实际分子与分母。",9)
    if not citation_applicable:para("本轮 AI 回答环境未提供引用来源，因此“引用率”记为“不适用”，不能解释为主体被 AI 零引用。",9)

    page_break();h("三、本地 / 区域机构 AI 可见度",1);chart("local_visibility")
    rows=model.get("ai_visibility",{}).get("local_institutions",[]);table(VIS_HEAD,vis_rows(rows),widths=VIS_W,font=8.3)
    para("本表只比较本次已确认进入正式研究的本地 / 区域机构；观察主体与 AI 回答中新出现的主体在后文单独披露，不混入主榜。",9)

    page_break();h("四、老师 / IP AI 可见度",1);chart("ip_visibility")
    rows=model.get("ai_visibility",{}).get("expert_ip",[]);table(VIS_HEAD,vis_rows(rows),widths=VIS_W,font=8.3)
    para("老师 / IP 与机构使用不同的问题组与样本分母，不把两类对象混在同一排名里。若同一品牌同时具备机构与个人入口，也分别计算。",9)

    page_break();h("五、结果稳定性",1)
    rb=model.get("robustness") or {};hp2=rb.get("hit_pattern_distribution") or {}
    table(["用户可读指标","结果","怎么理解"],[
        ["三种问法持续命中率",pct_smart(rb.get("positive_persistence_3of3_rate")),"至少命中过一次的主体×问题组合中，三种语义等价问法都能继续命中的比例"],
        ["不同问法推荐名单平均重合度",pct_smart(rb.get("pairwise_positive_set_jaccard_mean")),"数值越高，换一种问法后推荐名单越接近"],
        ["推荐名单完全一致率",pct_smart(rb.get("exact_positive_set_match_rate")),"三种问法得到完全相同正向名单的比例"],
    ],widths=[48,28,84],font=9)
    if hp2:
        labels={"0/3":"三种问法都未命中","1/3":"仅一种问法命中","2/3":"两种问法命中","3/3":"三种问法都命中"}
        table(["命中稳定性","主体×问题组合数"],[[labels.get(x,x),hp2[x]] for x in ("0/3","1/3","2/3","3/3") if x in hp2],widths=[70,50],font=9)
    para("这里衡量的是“换一种语义等价问法后，结果是否仍然出现”，不是现实市场份额，也不是跨所有 AI 模型的一致性。",9)

    page_break();h("六、概念占位",1);chart("concept_ownership")
    concepts=sorted(model.get("concept_map",[]),key=lambda x:float(x.get("strength") or 0),reverse=True)[:12]
    table(["主体","已形成的概念绑定","强度","绑定性质"],[[x.get("canonical_name") or x.get("entity_name"),x.get("concept"),x.get("strength"),BINDING_ZH.get(x.get("binding_type"),"可核验公开绑定")] for x in concepts],widths=[36,58,18,48],font=8.5)
    para("概念占位回答“机器在公开信息中更容易把谁和什么概念联系在一起”。单次偶发第三方提及不会被包装成强绑定。",9)

    page_break();h("七、GEO 资产基础",1);chart("asset_readiness")
    assets=model.get("asset_readiness",[]);scored=[];unscored=[]
    for x in assets:
        try:float(x.get("asset_readiness"));scored.append(x)
        except:unscored.append(x)
    scored=scored[:15]
    table(["排名","主体","资产基础得分","等级","可核验证据数","独立域名"],[[i+1,x.get("canonical_name") or x.get("entity_id"),x.get("asset_readiness"),x.get("asset_tier") or "—",x.get("evidence_count") or "—",x.get("independent_domains") or "—"] for i,x in enumerate(scored)],widths=[12,42,26,18,30,28],font=8.5)
    para(f"本轮共有 {len(scored)+len(unscored)} 个报告主体，其中 {len(scored)} 个具备足够公开证据形成资产基础评分，{len(unscored)} 个因公开证据不足暂不评分。暂不评分不等于 0 分，也不代表主体一定没有相关资产。",9)

    page_break();h("八、观察主体与新出现竞争者",1)
    obs=model.get("ai_visible_observation",[])
    if obs:
        h("观察主体中已被 AI 提名的对象",2)
        table(["主体","命中/样本","提名率","前三出现率","范围"],[[x.get("canonical_name"),hit(x),pct(x.get("nomination_rate")),pct(x.get("top3_rate")),SCOPE_ZH.get(x.get("market_scope"),"待核")] for x in obs],widths=[46,26,25,28,30],font=8.5)
    else:para("本轮观察主体没有获得正向提名。",9.5)
    ai_new=model.get("ai_visible_emergent",[])
    if ai_new:
        h("AI 回答中自然出现的新竞争者",2)
        table(["主体","测量对象","命中/样本","提名率","前三出现率"],[[x.get("canonical_name"),TARGET_ZH.get(x.get("measurement_target_for_report") or x.get("measurement_target"),"待核"),hit(x),pct(x.get("nomination_rate")),pct(x.get("top3_rate"))] for x in ai_new],widths=[46,38,26,25,28],font=8.5)
        para("这些对象不是事先塞进主榜的候选，而是在真实 AI 回答中自然出现，因此单独保留，避免污染预先确认的比较范围。",9)
    else:para("本轮没有出现研究主体池之外且已完成解析的新竞争者。",9.5)

    page_break();h("九、重点主体诊断",1)
    for x in model["diagnoses"]:
        h(x.get("name") or x.get("entity") or "主体诊断",2)
        table(["项目","判断"],[
            ["当前角色",ROLE_ZH.get(x.get("market_role"),_customerize(x.get("market_role")))],
            ["AI 可见度",x.get("ai_visibility","")],["已形成优势",x.get("strongest_asset","")],
            ["当前短板",x.get("largest_gap","")],["优先动作",x.get("recommendation","")],
        ],widths=[30,130],font=9)

    page_break();h("十、区域策略与 90 天行动",1)
    h("区域策略",2)
    for x in model["strategy"]:bullet(x)
    h("90 天行动",2)
    for x in model["plan_90_days"]:bullet(x)

    page_break();h("十一、如何理解本报告",1)
    kept=0
    for x in model["risks"]:
        if bullet(x):kept+=1
    if kept==0:bullet("本报告基于本轮记录条件下的 AI 回答与公开网络证据，结论应作为阶段性 GEO 诊断，不应外推为所有模型、所有时间点的固定事实。")
    if not citation_applicable:bullet("本轮回答环境没有提供可核验引用链，因此不评估引用率；报告中的“不适用”不能解释为“AI 从未引用该主体”。")
    bullet("本报告测量的是记录条件下的 AI 回答可见度，不等于真实市场份额、招生规模、教学效果、通过率或一般口碑。")

    page_break();h("附录：研究口径与主体清单",1)
    pr=model.get("measurement_protocol") or {}
    table(["口径","本轮设置"],[
        ["研究地区",meta.get("normalized_region") or meta.get("requested_region","")],
        ["研究方式",PROTOCOL_ZH.get(meta.get("research_mode"),"地区竞争格局研究")],
        ["AI 测量",PROTOCOL_ZH.get(pr.get("sampling_mode"),"按记录条件测量")],
        ["回答环境",PROTOCOL_ZH.get(pr.get("answer_context_mode_expected"),"按实际环境记录")],
        ["上下文隔离",PROTOCOL_ZH.get(pr.get("context_isolation_level"),"按实际环境记录")],
        ["问法设计",PROTOCOL_ZH.get(pr.get("query_variant_mode"),"固定问法")],
        ["回答样本数",pr.get("answer_cells","")],
        ["观察日期",pr.get("observation_date") or meta.get("observation_date","")],
        ["引用链", "可评估" if citation_applicable else "本轮环境不提供，故不评估"],
    ],widths=[48,112],font=9)
    h("正式研究主体",2)
    subject_rows=[]
    group_labels={"national_benchmarks":"全国品牌","local_institutions":"本地 / 区域机构","expert_ip":"老师 / IP","other_included":"其他正式主体"}
    for group,rows in (model.get("market_universe") or {}).items():
        for r in rows:subject_rows.append([r.get("canonical_name"),group_labels.get(group,"正式主体"),TARGET_ZH.get(r.get("measurement_target"),"待核")])
    table(["主体","类别","测量对象"],subject_rows,widths=[66,48,46],font=8.5)
    if unscored:
        h("公开证据不足、暂不评分的主体",2)
        para("、".join(x.get("canonical_name") or x.get("entity_id") for x in unscored),9)
    h("方法说明",2)
    for x in [
        "用户指定主体只保证纳入研究与解析，不会因为被用户指定而获得任何分数加成。",
        "机构与老师 / IP 使用不同问题组和分母，双入口主体也分别计算。",
        "AI 回答测量与公开网页证据分开：前者回答“AI 是否提到”，后者用于解释“为什么更容易被机器认识”。",
        "公开证据不足时保留未知状态，不把“没找到证据”写成 0 分。",
        "完整研究底稿、审计表和可复算数据保留在运行目录中，不在客户版报告正文展开。",
    ]:bullet(x)

    ensure_directory(out.parent);d.save(out);return out


def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);p.add_argument("--output",type=Path);a=p.parse_args();out=a.output or a.run_dir/"deliverables"/"report.docx"
    try:print(render(a.run_dir,out));return 0
    except (OSError,RuntimeError,ValueError) as e:print(f"generate_report_docx：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
