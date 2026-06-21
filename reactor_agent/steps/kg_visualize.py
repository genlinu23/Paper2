#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG 可视化生成器 —— 读 KG 的 nodes/edges.json，自动生成本地可看的 HTML 网络图。

特点：
  - 纯本地：生成的 HTML 内联 vis-network 库（首次运行联网下载一次库文件缓存到本地），
    之后生成的 HTML 断网也能打开。若已有本地库文件则完全离线。
  - 自动布局：vis-network 物理引擎自动摆节点，不用手工调坐标。
  - 13 类按类上色；边按关系类型上色 + 标签。
  - 三种视图：①每个失效模式一张子图 ②R1-R7（Reactor）演化子图 ③全图总览。
  - KG 更新后直接重跑本脚本即可，无需改代码。

用法：
  python kg_visualize.py --kg_dir <KG目录(含kg_nodes.json/kg_edges.json)> --out <输出目录>
  例：python kg_visualize.py --kg_dir outputs/step2_kg_clean_v1 --out outputs/step2_kg_clean_v1/viz

依赖：仅标准库（json/os/argparse/urllib）。不需要 pip 装任何东西。
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import urllib.request
from pathlib import Path

# ---- 13 类节点配色（对应 Agent 文档 B 节本体；新增类型时在此加色即可）----
TYPE_COLOR = {
    "Failure Mode": "#e74c3c",      # 红
    "Cathode": "#3498db",           # 蓝
    "Anode": "#2980b9",             # 深蓝
    "Separator": "#9b59b6",         # 紫
    "Electrolyte": "#16a085",       # 青
    "Gas Feed": "#27ae60",          # 绿
    "Operating Condition": "#f39c12",  # 橙
    "Performance": "#7f8c8d",       # 灰
    "Reactor": "#e67e22",           # 深橙
    "Diagnosis": "#c0392b",         # 暗红
    "Next Hypothesis": "#8e44ad",   # 深紫
    "Claim": "#bdc3c7",             # 浅灰
    "Paper": "#34495e",             # 墨蓝
}
REL_COLOR = {
    "caused_by": "#c0392b", "causes_risk": "#e67e22", "improves": "#27ae60",
    "has_component": "#2980b9", "evidenced_by": "#8e44ad",
    "supports": "#95a5a6", "replaces": "#d35400",
}
VIS_CDN = "https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.js"


def load_kg(kg_dir):
    nodes = json.load(open(os.path.join(kg_dir, "kg_nodes.json"), encoding="utf-8"))
    edges = json.load(open(os.path.join(kg_dir, "kg_edges.json"), encoding="utf-8"))
    nmap = {n["node_id"]: n for n in nodes}
    return nodes, edges, nmap


def get_vis_lib(out_dir, cache_lib=True):
    """把 vis-network 库缓存到输出目录，生成的 HTML 内联引用本地副本 → 断网可看。"""
    if not cache_lib:
        return None
    libpath = os.path.join(out_dir, "vis-network.min.js")
    if not os.path.exists(libpath):
        try:
            print("下载 vis-network 库（仅首次，之后离线）...")
            urllib.request.urlretrieve(VIS_CDN, libpath)
        except Exception as e:
            print(f"WARNING: download failed ({e}); HTML will use CDN. You can place {VIS_CDN} at {libpath}.")
            return None
    return libpath


def neighbors_subgraph(center_id, edges, nmap, max_hop=1):
    """取以 center_id 为中心的 1 跳子图（含进出边）。"""
    keep_nodes, keep_edges = {center_id}, []
    for e in edges:
        if e["src"] == center_id or e["dst"] == center_id:
            keep_nodes.add(e["src"]); keep_nodes.add(e["dst"]); keep_edges.append(e)
    return keep_nodes, keep_edges


def render_html(title, node_ids, edges_sub, nmap, lib_ref, subtitle=""):
    vis_nodes, vis_edges = [], []
    for nid in node_ids:
        n = nmap.get(nid)
        if not n: continue
        t = n.get("type", "?")
        vis_nodes.append({
            "id": nid, "label": n.get("label", nid)[:40],
            "color": TYPE_COLOR.get(t, "#999"),
            "shape": "dot", "size": 26 if t in ("Failure Mode", "Reactor") else 14,
            "font": {"size": 16 if t in ("Failure Mode", "Reactor") else 12},
            "title": f"{t}: {html.escape(n.get('label',''))}",
        })
    for e in edges_sub:
        rel = e.get("relation", "")
        vis_edges.append({
            "from": e["src"], "to": e["dst"], "label": rel, "arrows": "to",
            "color": {"color": REL_COLOR.get(rel, "#888")},
            "font": {"size": 10, "color": REL_COLOR.get(rel, "#888"), "align": "middle"},
            "title": "doc: " + str(e.get("source_doc_id") or e.get("experiment_ref") or "-"),
            "smooth": {"type": "dynamic"},
        })
    legend = " ".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px">'
        f'<span style="width:12px;height:12px;border-radius:50%;background:{c};display:inline-block"></span>{t}</span>'
        for t, c in TYPE_COLOR.items())
    script_tag = (f'<script src="vis-network.min.js"></script>' if lib_ref
                  else f'<script src="{VIS_CDN}"></script>')
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
:root{{color-scheme:light}} body{{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:#fafafa;color:#1a1a1a}}
header{{padding:14px 22px;background:#fff;border-bottom:1px solid #e5e5e5}} h1{{font-size:16px;margin:0 0 4px}}
.sub{{font-size:12px;color:#666}} #legend{{padding:9px 22px;background:#fff;border-bottom:1px solid #e5e5e5;font-size:12px}}
#net{{width:100%;height:660px;background:#fff}}</style></head><body>
<header><h1>{html.escape(title)}</h1><div class="sub">{html.escape(subtitle)} · 节点 {len(vis_nodes)} 边 {len(vis_edges)} · 可拖拽缩放</div></header>
<div id="legend">{legend}</div><div id="net"></div>
{script_tag}<script>
var nodes=new vis.DataSet({json.dumps(vis_nodes, ensure_ascii=False)});
var edges=new vis.DataSet({json.dumps(vis_edges, ensure_ascii=False)});
new vis.Network(document.getElementById("net"),{{nodes:nodes,edges:edges}},
{{physics:{{stabilization:true,barnesHut:{{gravitationalConstant:-9000,springLength:150}}}},
interaction:{{hover:true,tooltipDelay:120}},edges:{{width:1.5}},nodes:{{borderWidth:0}}}});
</script></body></html>"""


def _safe_graph_filename(prefix, label, identifier=None):
    safe_label = "".join(c if c.isalnum() else "_" for c in str(label))[:40]
    digest_source = str(identifier or label)
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{safe_label or 'unnamed'}_{digest}.html"


def build_visualizations(kg_dir, out=None, max_full=400, cache_lib=True):
    """Generate local HTML KG visualizations and return output metadata."""
    kg_path = Path(kg_dir)
    out_path = Path(out) if out is not None else kg_path / "viz"
    out_path.mkdir(parents=True, exist_ok=True)

    nodes, edges, nmap = load_kg(str(kg_path))
    lib = get_vis_lib(str(out_path), cache_lib=cache_lib)
    index = []

    # ① 每个 Failure Mode 一张子图
    fm_nodes = [n for n in nodes if n.get("type") == "Failure Mode"]
    for n in fm_nodes:
        nid = n["node_id"]
        nset, esub = neighbors_subgraph(nid, edges, nmap)
        if len(esub) < 2:  # 太小的失效模式跳过
            continue
        fn = _safe_graph_filename("fm", n["label"], n["node_id"])
        (out_path / fn).write_text(
            render_html(f"失效模式子图：{n['label']}", nset, esub, nmap, lib, "按失效模式取1跳因果子图"),
            encoding="utf-8",
        )
        index.append((f"失效模式：{n['label']}", fn, len(nset), len(esub)))

    # ② 每个 Reactor 一张子图（R1-R7 结构演化）
    for n in [x for x in nodes if x.get("type") == "Reactor"]:
        nid = n["node_id"]
        nset, esub = neighbors_subgraph(nid, edges, nmap)
        if len(esub) < 2:
            continue
        fn = _safe_graph_filename("reactor", n["label"], n["node_id"])
        (out_path / fn).write_text(
            render_html(f"反应器子图：{n['label']}", nset, esub, nmap, lib, "按反应器取构成/性能/风险子图"),
            encoding="utf-8",
        )
        index.append((f"反应器：{n['label']}", fn, len(nset), len(esub)))

    # ③ 全图总览（节点过多时取连接度最高的前 max_full 个）
    deg = {}
    for e in edges:
        deg[e["src"]] = deg.get(e["src"], 0) + 1
        deg[e["dst"]] = deg.get(e["dst"], 0) + 1
    top = set(sorted(deg, key=lambda k: -deg[k])[:max_full])
    esub = [e for e in edges if e["src"] in top and e["dst"] in top]
    (out_path / "overview.html").write_text(
        render_html(
            "KG 全图总览（高连接度核心）",
            top,
            esub,
            nmap,
            lib,
            f"全 {len(nodes)} 节点中取连接度前 {max_full}",
        ),
        encoding="utf-8",
    )
    index.append(("★全图总览", "overview.html", len(top), len(esub)))

    # 索引页
    rows = "".join(f'<li><a href="{fn}">{html.escape(t)}</a> （节点{nn} 边{ne}）</li>' for t, fn, nn, ne in index)
    (out_path / "index.html").write_text(
        f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>KG 可视化索引</title>
<style>body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;max-width:760px;margin:30px auto;padding:0 20px;color:#1a1a1a}}
h1{{font-size:20px}} li{{margin:6px 0;font-size:14px}} a{{color:#2563eb;text-decoration:none}}</style></head>
<body><h1>知识图谱可视化索引</h1><p>KG: {html.escape(str(kg_path))} · 共 {len(index)} 张图。点击查看。</p>
<ul>{rows}</ul></body></html>""",
        encoding="utf-8",
    )
    return {
        "out_dir": str(out_path),
        "index_html": str(out_path / "index.html"),
        "overview_html": str(out_path / "overview.html"),
        "graphs": len(index),
        "nodes": len(nodes),
        "edges": len(edges),
        "cached_vis_lib": bool(lib),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg_dir", required=True, help="含 kg_nodes.json / kg_edges.json 的目录")
    ap.add_argument("--out", required=True, help="HTML 输出目录")
    ap.add_argument("--max_full", type=int, default=400, help="全图总览最多画多少节点(防糊)")
    ap.add_argument("--no_cache_lib", action="store_true", help="不下载/缓存 vis-network，本次 HTML 回退到 CDN")
    args = ap.parse_args()
    result = build_visualizations(args.kg_dir, args.out, max_full=args.max_full, cache_lib=not args.no_cache_lib)
    print(f"OK: generated {result['graphs']} graphs + index.html at {result['out_dir']}")
    print(f"Open {result['index_html']} to view all graphs.")


if __name__ == "__main__":
    main()
