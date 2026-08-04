#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ko-RealtimeQA — 자체 완결형 평가 스크립트 (레포 불필요, requests만 필요).

회차(월)를 지정하면 그 회차의 정답 공개 여부에 따라 자동 분기한다.

  · 정답 미공개 회차(현재 회차 = `{YYYYMM}_qa.jsonl` 없음)
      → 후보 모델로 **답변만 생성**해 조건별 제출 파일(`submission_<조건>.jsonl`)을 만든다.
        (채점 없음. 운영자에게 제출 → 운영자가 보류된 정답으로 채점)

  · 정답 공개 회차(과거 회차 = `{YYYYMM}_qa.jsonl` 있음)
      → 답변 생성 + solar-pro3 심판 채점 + **리포트(report.md/html)** 까지 생성한다.

산출물은 `eval/{YYYY-MM}/` 아래에 저장된다.

의존성:  pip install requests

빠른 시작:
  # 과거 회차 자율 채점 + 리포트 (채점 키 필요)
  python evaluate.py --month 2026-06 \
      --model-base-url https://<your-host>/v1 --model-name <your-model-id> \
      --model-key <YOUR_MODEL_KEY> --upstage-key <UPSTAGE_KEY>

  # 현재 회차 제출 파일 생성 (정답 미공개 → 채점 키 불필요)
  python evaluate.py --month 2026-08 \
      --model-base-url https://<your-host>/v1 --model-name <your-model-id> --model-key <KEY>

후보 모델이 OpenAI 호환 엔드포인트가 아니면 아래 `call_candidate()` 한 함수만
자신의 추론 코드로 바꾸면 된다(입력=프롬프트 문자열, 출력=답변 문자열).

라이선스/이용: ../README.md 참조 (학술·연구용).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    sys.exit("requests가 필요합니다:  pip install requests")

# ─────────────────────────────────────────────────────────────────────────────
# 프롬프트 (배포 원본과 100% 동일 — 우리 리더보드 수치와 비교 가능하게 유지할 것)
# ─────────────────────────────────────────────────────────────────────────────
CLOSED_PROMPT = "<QUESTION>{question}</QUESTION>\n한 문장으로 답하세요."
CONTEXT_PROMPT = (
    "<참고자료>\n{context}\n</참고자료>\n\n"
    "<QUESTION>{question}</QUESTION>\n위 참고자료를 근거로 한 문장으로 답하세요."
)
RETRIEVED_MAX_CHARS_PER_DOC = 2000  # retrieved 문서당 본문 절단 길이


def format_context(docs):
    """retrieved 검색문서 리스트 → 주입 컨텍스트 (배포 원본 format_context와 동일)."""
    parts = []
    for i, d in enumerate(docs, 1):
        text = d.get("text", "") or ""
        if RETRIEVED_MAX_CHARS_PER_DOC and len(text) > RETRIEVED_MAX_CHARS_PER_DOC:
            text = text[:RETRIEVED_MAX_CHARS_PER_DOC] + " …"
        parts.append(f"[{i}] {d.get('title', '')}\n{text}\n(출처: {d.get('url', '')})")
    return "\n\n".join(parts)


def build_prompt(mode, question, context):
    if mode == "closed":
        return CLOSED_PROMPT.format(question=question)
    return CONTEXT_PROMPT.format(context=context, question=question)


# ─────────────────────────────────────────────────────────────────────────────
# Judge (solar-pro3) — 배포 원본과 동일 프롬프트
# ─────────────────────────────────────────────────────────────────────────────
JUDGE_SYSTEM = """\
당신은 한국어 실시간 QA 채점 심판(judge)입니다. 참가자의 답안이 정답인지
주어진 기준 정답(gold)에 근거하여 판정합니다.

규칙:
- reference(gold) 정답에만 근거하고, 당신의 자체 지식으로 정답을 바꾸지 마십시오.
- 길이·확신표현·문체는 무시하고 사실 정합만 봅니다(verbosity bias 차단).
- 먼저 근거(comment)를 적고, 그 다음 판정합니다(reason-first).

두 모드로 판정합니다:
- Relaxed: 주(primary) 답의 정답성만 봅니다. 부수적 오류가 주 답에 영향이 없으면
  허용 → relaxed_correct ∈ {0,1}.
  · 수치 답은 gold 수치와 **값이 같아야** 정답입니다. 표기·단위 차이(476만=4,760,000명)는
    같은 값이라 정답이지만, **다른 값(475만≠476만)은 근사·반올림으로 봐주지 말고 오답**.
- Strict: 답이 정답이면서, 주 답 외에 **뒷받침 없이 덧붙인 구체적 사실 주장이 없어야** 1.
  주 답은 맞아도 gold로 뒷받침되지 않는 구체 사실(지어낸 통계·수치·날짜·인물·사건)을
  덧붙였으면 0. (검증 불가여도 근거 없이 새로 주장한 구체 사실은 감점 — '거짓임이
  입증돼야 감점'이 아니라 '뒷받침 없이 덧붙였으면 감점'.)
  · 감점하지 말 것(사실 주장이 아님): 출처 표현('~에 따르면'), 헤지('약','~일 수 있음'),
    시점 단서('현재 기준','이후 갱신될 수 있음'), 일반 프레이밍/부연.
  ※ 최신성(지금도 유효한가)은 판정하지 마세요 — 실험 조건이 따로 측정합니다.

환각: relaxed_correct=1 이고 strict_correct=0 이면 is_hallucinated=true.

출력은 순수 JSON:
{"comment": "...", "relaxed_correct": 0|1, "strict_correct": 0|1, "is_hallucinated": true|false}
"""

JUDGE_USER = """\
<QUESTION>
{question}
</QUESTION>

<GOLD>
- {gold}
</GOLD>

<RESPONSE>
{response}
</RESPONSE>

위 규칙대로 코멘트를 먼저 쓰고 Relaxed/Strict를 판정해 JSON으로 출력하세요. (참가자 답이 <GOLD> 항목 중 하나와 의미가 일치하면 정답)
"""


# ─────────────────────────────────────────────────────────────────────────────
# HTTP (OpenAI 호환 chat/completions) — 후보 모델·judge 공통, 일시 오류 재시도
# ─────────────────────────────────────────────────────────────────────────────
def _chat(base_url, api_key, model, messages, temperature=0.0, max_retries=4, timeout=120):
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages, "temperature": temperature}
    last = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
            # 일부 추론 모델은 temperature 커스텀값을 거부한다("Only the default (1) value is
            # supported"). 이 경우 temperature를 빼고 한 번 즉시 재호출한다.
            if (r.status_code == 400 and "temperature" in body
                    and "temperature" in (r.text or "").lower()):
                body.pop("temperature", None)
                r = requests.post(url, headers=headers, json=body, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                if attempt < max_retries:
                    time.sleep(min(2.0 * (2 ** attempt), 30.0))
                    continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last = str(e)
            if attempt < max_retries:
                time.sleep(2.0 * (2 ** attempt))
                continue
            raise
    raise RuntimeError(f"chat 호출 실패(재시도 소진): {last}")


# ★ 후보 모델 호출 지점 — OpenAI 호환이 아니면 이 함수만 자신의 추론으로 교체하세요.
#   입력: 프롬프트 문자열 / 출력: 모델 답변 문자열.
def call_candidate(prompt, cfg):
    return _chat(cfg["model_base_url"], cfg["model_key"], cfg["model_name"],
                 [{"role": "user", "content": prompt}], temperature=0.0).strip()


def _extract_json(text):
    """judge 응답에서 첫 JSON 객체 robust 추출."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    s, e = t.find("{"), t.rfind("}")
    if s >= 0 and e > s:
        return json.loads(t[s:e + 1])
    return json.loads(t)


def judge_once(question, gold, response, cfg):
    """solar-pro3 채점 → dict(relaxed, strict). 실패 시 None."""
    messages = [{"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": JUDGE_USER.format(
                    question=question, gold=gold, response=response or "(빈 답안)")}]
    for _ in range(3):  # JSON 깨짐 대비 재시도
        try:
            out = _chat(cfg["upstage_base_url"], cfg["upstage_key"], cfg["judge_model"], messages)
            o = _extract_json(out)
            return {"relaxed": int(o.get("relaxed_correct", 0)),
                    "strict": int(o.get("strict_correct", 0)),
                    "comment": o.get("comment", "")}
        except Exception:  # noqa: BLE001
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────────────────────────────────────
def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def find_file(data_dir, suffix):
    for name in sorted(os.listdir(data_dir)):
        if name.endswith(suffix):
            return os.path.join(data_dir, name)
    return None


def _context_for(mode, qid, source_by_id, retrieve_by_id):
    if mode == "closed":
        return None
    if mode == "oracle":
        return (source_by_id.get(qid) or {}).get("text", "")
    return format_context((retrieve_by_id.get(qid) or {}).get("search_result", []))


# ─────────────────────────────────────────────────────────────────────────────
# 생성 / 채점
# ─────────────────────────────────────────────────────────────────────────────
def _generate(mode, rec, source_by_id, retrieve_by_id, cfg):
    qid, question = rec["id"], rec["question"]
    context = _context_for(mode, qid, source_by_id, retrieve_by_id)
    try:
        answer = call_candidate(build_prompt(mode, question, context), cfg)
        return answer, None
    except Exception as e:  # noqa: BLE001
        return "", str(e)[:200]


def predict_condition(mode, qa, source_by_id, retrieve_by_id, cfg):
    """답변만 생성 → 제출 레코드 [{id, answer}]."""
    def one(rec):
        answer, _ = _generate(mode, rec, source_by_id, retrieve_by_id, cfg)
        return {"id": rec["id"], "answer": answer}
    with ThreadPoolExecutor(max_workers=cfg["workers"]) as ex:
        return list(ex.map(one, qa))


def score_condition(mode, qa, source_by_id, retrieve_by_id, cfg):
    """생성 → solar-pro3 채점 → 문항별 결과."""
    def one(rec):
        qid, question, gold = rec["id"], rec["question"], rec["answer"]
        answer, gen_err = _generate(mode, rec, source_by_id, retrieve_by_id, cfg)
        v = judge_once(question, gold, answer, cfg)
        relaxed = v["relaxed"] if v else 0
        strict = v["strict"] if v else 0
        return {"id": qid, "mode": mode, "question": question, "gold": gold,
                "answer": answer, "relaxed": relaxed, "strict": strict,
                "hallucination": int(relaxed == 1 and strict == 0),
                "scorable": v is not None, "gen_error": gen_err,
                "comment": (v or {}).get("comment", "")}
    with ThreadPoolExecutor(max_workers=cfg["workers"]) as ex:
        return list(ex.map(one, qa))


def summarize(rows):
    scored = [r for r in rows if r["scorable"]]
    n = len(scored) or 1
    return {"n": len(rows), "n_scored": len(scored),
            "relaxed": round(sum(r["relaxed"] for r in scored) / n, 4),
            "strict": round(sum(r["strict"] for r in scored) / n, 4),
            "hallucination_rate": round(sum(r["hallucination"] for r in scored) / n, 4)}


# ─────────────────────────────────────────────────────────────────────────────
# 리포트 (Ko-RealtimeQA 표준 형식: 개요·결과·최신성격차/헤드룸·도메인·카테고리)
# ─────────────────────────────────────────────────────────────────────────────
def _pct(x):
    return f"{x * 100:.1f}%" if isinstance(x, (int, float)) else "-"


def _mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else None


def _breakdown(rows, key_of, modes):
    """key(도메인/카테고리)별 · 조건별 평균 relaxed + 문항수(distinct id). 문항수 내림차순."""
    qids = collections.defaultdict(set)
    acc = collections.defaultdict(lambda: [0.0, 0])
    for r in rows:
        k = key_of(r)
        if not k:
            continue
        qids[k].add(r["id"])
        acc[(k, r["mode"])][0] += r["relaxed"]
        acc[(k, r["mode"])][1] += 1
    out = []
    for k in qids:
        cells = {m: (acc[(k, m)][0] / acc[(k, m)][1] if acc[(k, m)][1] else None) for m in modes}
        out.append((k, len(qids[k]), cells))
    return sorted(out, key=lambda t: -t[1])


def build_report(month, model_name, rows, qa_by_id, modes):
    for r in rows:  # 도메인·카테고리 주입(리포트용)
        q = qa_by_id.get(r["id"], {})
        r["_domain"] = q.get("domain")
        r["_category"] = q.get("category")

    def stat(mode, key):
        return _mean([r[key] for r in rows if r["mode"] == mode])

    n_q = len({r["id"] for r in rows})
    L = []
    L.append(f"# 평가 리포트 — {month} · {model_name}")
    L.append("")
    L.append(f"- **문항**: n={n_q} · **조건**: {' / '.join(modes)}")
    L.append("- **판정**: LLM-as-judge = solar-pro3, Relaxed / Strict + 환각률(=relaxed 1 & strict 0)")
    L.append("")

    # 1. 결과
    L.append("## 1. 결과 (relaxed / strict / 환각률, %)")
    L.append("")
    L.append("| 모델 | " + " | ".join(modes) + " |")
    L.append("|---|" + "|".join(["---"] * len(modes)) + "|")
    cells = []
    for m in modes:
        cells.append(f"{_pct(stat(m, 'relaxed'))} / {_pct(stat(m, 'strict'))} / {_pct(stat(m, 'hallucination'))}")
    L.append(f"| {model_name} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("> 셀 = relaxed / strict / 환각률. `closed ≪ retrieved ≪ oracle` 단조 증가가 정상.")
    L.append("")

    # 2. 최신성 격차와 헤드룸
    if {"closed", "retrieved", "oracle"} <= set(modes):
        c, rt, o = stat("closed", "relaxed"), stat("retrieved", "relaxed"), stat("oracle", "relaxed")
        if None not in (c, rt, o):
            L.append("## 2. 최신성 격차와 헤드룸")
            L.append("")
            L.append("| 모델 | 검색이득 Δ(closed→retrieved) | 헤드룸(oracle−retrieved) |")
            L.append("|---|---:|---:|")
            L.append(f"| {model_name} | +{_pct(rt - c)} | {_pct(o - rt)} |")
            L.append("")

    # 3. 도메인별
    dom = _breakdown(rows, lambda r: r.get("_domain"), modes)
    if dom:
        L.append("## 3. 도메인별 분석 (relaxed %)")
        L.append("")
        L.append("| 도메인 | 문항 | " + " | ".join(modes) + " |")
        L.append("|---|---:|" + "|".join(["---:"] * len(modes)) + "|")
        for k, n, cs in dom:
            L.append(f"| {k} | {n} | " + " | ".join(_pct(cs[m]) if cs[m] is not None else "-" for m in modes) + " |")
        L.append("")

    # 4. 카테고리별
    cat = _breakdown(rows, lambda r: r.get("_category"), modes)
    if cat:
        L.append("## 4. 카테고리별 분석 (relaxed %)")
        L.append("")
        L.append("| 카테고리 | 문항 | " + " | ".join(modes) + " |")
        L.append("|---|---:|" + "|".join(["---:"] * len(modes)) + "|")
        for k, n, cs in cat:
            L.append(f"| {k} | {n} | " + " | ".join(_pct(cs[m]) if cs[m] is not None else "-" for m in modes) + " |")
        L.append("")

    return "\n".join(L)


def md_to_html(md):
    import html as _h
    out = ["<!doctype html><meta charset='utf-8'><title>평가 리포트</title>",
           "<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
           "table{border-collapse:collapse;margin:1rem 0}th,td{border:1px solid #ccc;padding:4px 10px;text-align:left}"
           "th{background:#f5f5f5}blockquote{color:#555;border-left:3px solid #ccc;padding-left:1rem;margin-left:0}</style>"]

    def inline(s):
        s = _h.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        return s

    lines = md.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("> "):
            out.append(f"<blockquote>{inline(ln[2:])}</blockquote>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            header = [c.strip() for c in rows[0].strip("|").split("|")]
            body = rows[2:] if len(rows) > 2 else []
            thtml = "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr>"
            bhtml = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in
                            [x.strip() for x in br.strip('|').split('|')]) + "</tr>" for br in body)
            out.append(f"<table>{thtml}{bhtml}</table>")
            continue
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    here = os.path.dirname(os.path.abspath(__file__))         # eval/
    repo_root = os.path.dirname(here)                          # 저장소 루트
    p = argparse.ArgumentParser(description="Ko-RealtimeQA 회차 평가(정답 유무 자동 분기)")
    p.add_argument("--month", required=True, help="회차 YYYY-MM (예: 2026-06)")
    p.add_argument("--release-root", default=os.path.join(repo_root, "release"),
                   help="release 폴더(기본 ../release)")
    p.add_argument("--out-root", default=here, help="출력 루트(기본 eval/)")
    p.add_argument("--conditions", default=None,
                   help="closed,retrieved,oracle 중 콤마구분(미지정 시 데이터로 자동)")
    p.add_argument("--model-base-url", required=True, help="후보 모델 OpenAI 호환 base_url(…/v1)")
    p.add_argument("--model-name", required=True, help="후보 모델 id")
    p.add_argument("--model-key", default=os.getenv("MODEL_API_KEY", ""), help="후보 모델 API 키")
    p.add_argument("--upstage-key", default=os.getenv("UPSTAGE_API_KEY", ""),
                   help="채점(judge=solar-pro3)용 Upstage 키. 정답 공개 회차에서만 필요.")
    p.add_argument("--upstage-base-url", default="https://api.upstage.ai/v1")
    p.add_argument("--judge-model", default="solar-pro3")
    p.add_argument("--workers", type=int, default=8, help="문항 병렬 수")
    p.add_argument("--limit", type=int, default=None, help="앞 N문항만(스모크)")
    args = p.parse_args()

    release_dir = os.path.join(args.release_root, args.month)
    if not os.path.isdir(release_dir):
        sys.exit(f"회차 폴더 없음: {release_dir}")

    gold_path = find_file(release_dir, "_qa.jsonl")            # 정답 포함본(과거 회차)
    public_path = find_file(release_dir, "_qa_public.jsonl")   # 정답 공란본(항상)
    src_path = find_file(release_dir, "_source.jsonl")
    ret_path = find_file(release_dir, "_retrieve.jsonl")

    score_mode = gold_path is not None
    qa_path = gold_path if score_mode else public_path
    if not qa_path:
        sys.exit(f"{release_dir} 에서 *_qa.jsonl 또는 *_qa_public.jsonl 을 찾지 못했습니다.")
    qa = load_jsonl(qa_path)
    if args.limit:
        qa = qa[:args.limit]

    source_by_id = {r["id"]: r for r in load_jsonl(src_path)} if src_path else {}
    retrieve_by_id = {r["id"]: r for r in load_jsonl(ret_path)} if ret_path else {}

    # 사용 가능한 조건(데이터로 결정)
    avail = ["closed"] + (["retrieved"] if retrieve_by_id else []) + (["oracle"] if source_by_id else [])
    conditions = ([c.strip() for c in args.conditions.split(",") if c.strip()]
                  if args.conditions else avail)
    conditions = [c for c in conditions if c in avail]

    out_dir = os.path.join(args.out_root, args.month)
    os.makedirs(out_dir, exist_ok=True)

    cfg = {"model_base_url": args.model_base_url, "model_key": args.model_key,
           "model_name": args.model_name, "upstage_base_url": args.upstage_base_url,
           "upstage_key": args.upstage_key, "judge_model": args.judge_model, "workers": args.workers}

    if not score_mode:
        # ── 정답 미공개 회차: 제출 파일만 생성 ──
        print(f"[{args.month}] 정답 미공개 회차 → 제출 파일 생성(채점 없음) · 조건 {conditions}")
        for mode in conditions:
            preds = predict_condition(mode, qa, source_by_id, retrieve_by_id, cfg)
            outp = os.path.join(out_dir, f"submission_{mode}.jsonl")
            with open(outp, "w", encoding="utf-8") as f:
                for r in preds:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  [{mode}] {len(preds)}건 → {outp}")
        print(f"\n→ {out_dir}/submission_<조건>.jsonl · 운영자에게 제출하세요.")
        return

    # ── 정답 공개 회차: 채점 + 리포트 ──
    if not args.upstage_key:
        sys.exit("채점에 Upstage 키가 필요합니다: --upstage-key 또는 env UPSTAGE_API_KEY")
    all_rows, summary = [], {}
    for mode in conditions:
        print(f"[{mode}] {len(qa)}문항 생성+채점 (병렬 {args.workers}) …", flush=True)
        rows = score_condition(mode, qa, source_by_id, retrieve_by_id, cfg)
        all_rows.extend(rows)
        summary[mode] = summarize(rows)
        s = summary[mode]
        print(f"[{mode}] relaxed={s['relaxed']} strict={s['strict']} "
              f"환각률={s['hallucination_rate']} (채점 {s['n_scored']}/{s['n']})")

    with open(os.path.join(out_dir, "results.jsonl"), "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"month": args.month, "model": args.model_name, "conditions": summary},
                  f, ensure_ascii=False, indent=2)

    qa_by_id = {r["id"]: r for r in qa}   # 정답본엔 domain·category 있음(리포트용)
    md = build_report(args.month, args.model_name, all_rows, qa_by_id, conditions)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as f:
        f.write(md_to_html(md))
    print(f"\n→ {out_dir}/summary.json · results.jsonl · report.md · report.html")


if __name__ == "__main__":
    main()
