# 제출·채점 방식

Ko-RealtimeQA는 오염 방지를 위해 **현재(최신) 회차는 정답을 보류**한다. 그래서 현재 회차는 제출형, 과거 회차는 자율 채점으로 운영한다.

두 경우 모두 **같은 스크립트**를 쓴다 — `eval/evaluate.py`는 회차에 정답(`{월}_qa.jsonl`)이 있는지로 자동 분기한다. 결과는 `eval/<YYYY-MM>/`에 저장된다.

```bash
python eval/evaluate.py --month <YYYY-MM> \
  --model-base-url https://<host>/v1 --model-name <내-모델-id> --model-key <KEY> \
  [--upstage-key <UPSTAGE_KEY>]   # 채점(과거 회차)에만 필요
```

## 현재 회차 (정답 보류) — 제출형

gold 정답(`_qa.jsonl`)이 없으므로, 스크립트는 **답변만 생성**해 조건별 제출 파일을 만든다(채점 없음 → Upstage 키 불필요). 원문(`_source`)·검색본(`_retrieve`)은 공개되므로 세 조건 모두 생성한다.

1. `python eval/evaluate.py --month <현재월> --model-base-url … --model-name … --model-key …`
2. → `eval/<현재월>/<모델>/submission_{closed,retrieved,oracle}.jsonl` 생성
3. 이 파일을 운영자에게 제출 → 보류된 정답으로 채점해 결과 회신
4. 주요 모델 리더보드는 운영자가 회차별로 공개

제출 파일 포맷(한 줄 1문항, `eval/sample_submission.jsonl` 참조):
```json
{"id": "<문항 ID>", "answer": "<모델이 생성한 한 문장 답>"}
```

## 과거 회차 (정답 공개) — 자율 채점 + 리포트

평가 창이 닫힌 과거 회차는 정답(`_qa`)·원문(`_source`)이 공개되므로, 스크립트가 **생성 + 채점 + 리포트**까지 한다(Upstage 키 필요).

```bash
python eval/evaluate.py --month <과거월> \
  --model-base-url … --model-name … --model-key … --upstage-key <UPSTAGE_KEY>
```
→ `eval/<과거월>/` 에 `summary.json` · `results.jsonl` · `report.md`

## 채점 지표

- **Relaxed** — 핵심을 맞혔는가 (부연이 붙어도 통과)
- **Strict** — 군더더기 없이 정확히 답했는가
- **환각률** — 맞혔으나 근거 없는 사실을 덧붙였는가 (Relaxed 통과 & Strict 실패)

> `closed` 점수는 모델 지식 순위로 해석하지 않는다. 모르면 거부하는 모델은 낮게, 추측하는 모델은 높게 나오기 때문이다. 능력 비교는 `retrieved`/`oracle`이 적절하다.

## 문의·제출

taehwan.oh@upstage.ai
