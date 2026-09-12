#!/usr/bin/env python3
"""最终 DOCX QA：实际打开、逐章节内容核验、占位/重复/空表扫描、关键数字与 report_model 对账。"""
from __future__ import annotations
import argparse,json,re,sys,zipfile
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("run_dir",type=Path);a=ap.parse_args();run=a.run_dir
    from docx import Document
    from docx.oxml.ns import qn
    import importlib.util
    spec=importlib.util.spec_from_file_location("vr",HERE/"validation_report.py");vr=importlib.util.module_from_spec(spec)
    sys.modules["vr"]=vr;spec.loader.exec_module(vr)
    docx=run/"deliverables"/"report.docx";model=json.loads((run/"report_model.json").read_text(encoding="utf-8"))
    report={"file":str(docx),"size":docx.stat().st_size,"checks":[],"sections":[],"warnings":[]}
    def chk(name,ok,detail=""):
        report["checks"].append({"check":name,"ok":bool(ok),"detail":detail});return ok
    # 1) 可正常打开
    d=Document(str(docx));chk("DOCX 可被 python-docx 正常打开",True,f"paragraphs={len(d.paragraphs)}, tables={len(d.tables)}")
    with zipfile.ZipFile(docx) as z:
        bad=z.testzip();chk("ZIP 结构无损坏",bad is None,str(bad))
        names=z.namelist()
        imgs=[n for n in names if n.startswith("word/media/")];chk("内嵌图片数量 == 6",len(imgs)==6,f"{len(imgs)} 张：{[Path(x).name for x in imgs]}")
        chk("页眉页脚已写入",any(n.startswith("word/header") for n in names) and any(n.startswith("word/footer") for n in names),
            ",".join(n for n in names if n.startswith(("word/header","word/footer"))))
        xml=z.read("word/document.xml").decode("utf-8",errors="ignore")
    # 2) 占位文案 / 调试文字
    ph=[x for x in ("待归纳","TODO","TBD","由 score_details","本次已执行 IP Measurement。","应由 Agent 基于","placeholder","占位文案","占位符","待补充","lorem") if x in xml]
    chk("无占位/调试文案",not ph,",".join(ph) or "none")
    # 3) 章节结构与内容量
    sections=vr.docx_sections(docx);rep={s["heading"]:s["content"] for s in sections}
    for h in vr.REQUIRED_DOCX_SECTIONS:
        ok=h in rep and rep[h]>0
        report["sections"].append({"heading":h,"content_elements":rep.get(h,0),"present":h in rep})
        chk(f"章节「{h}」存在且非空",ok,f"content={rep.get(h,0)}")
    dup=[k for k,v in Counter(s["heading"] for s in sections).items() if v>1]
    chk("无重复一级章节",not dup,",".join(dup) or "none")
    # 4) 空表扫描（只有表头、没有数据行）
    empty_tables=0;tbl_rows=[]
    for t in d.tables:
        tbl_rows.append(len(t.rows))
        if len(t.rows)<2:empty_tables+=1
    chk("无只有表头的数据表",empty_tables==0,f"empty={empty_tables} / tables={len(d.tables)}")
    # 5) 关键数字与 report_model 对账
    text="\n".join(p.text for p in d.paragraphs)
    for t in d.tables:
        for r in t.rows:
            text+="\n"+" | ".join(c.text for c in r.cells)
    probes=[]
    nat=next((r for r in model["ai_visibility"]["national_benchmarks"] if r["entity_id"]=="E012"),None)
    if nat:probes.append(("华图命中/样本",f"{nat.get('mentioned_answers')}/{nat.get('answer_cells')}"))
    probes.append(("robustness 3of3",str(model["robustness"].get("positive_persistence_3of3_rate"))))
    probes.append(("asset 行数",str(len(model["asset_readiness"]))))
    probes.append(("intent listed",str(model["measurement_qa"]["annotation_intent_distribution"].get("listed"))))
    for name,v in probes:
        chk(f"关键数字出现在正文：{name}",v in text,f"value={v}")
    # 6) 表格宽度与内容抽查
    chk("存在数据表且行数合理",len(d.tables)>=10 and sum(tbl_rows)>150,f"tables={len(d.tables)}, rows_total={sum(tbl_rows)}")
    # 7) 关键结论带来源
    chk("报告层数据来源章节存在","报告层数据来源" in text)
    chk("方法边界章节存在","研究方法边界" in text)
    fails=[c for c in report["checks"] if not c["ok"]]
    report["verdict"]="PASS" if not fails else "FAIL"
    report["failed"]=fails
    (run.parent.parent/"evidence"/"docx_qa.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"verdict":report["verdict"],"checks":len(report["checks"]),"failed":len(fails),"sections":len(report["sections"]),"images":len(imgs),"tables":len(d.tables)},ensure_ascii=False))
    for f in fails:print("  FAIL:",f["check"],"|",f["detail"])
    return 0 if not fails else 1

if __name__=="__main__":raise SystemExit(main())
