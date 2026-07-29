# 제출·채점 방식

Ko-RealtimeQA는 오염 방지를 위해 **현재(최신) 회차는 정답을 보류**한다. 따라서 현재 회차는 제출형으로, 과거 회차는 자율 채점으로 운영한다.

## 현재 회차 (정답 보류) — 제출형

1. 배포된 질문 `{월}_qa_public.jsonl`(정답 공란)과 검색 동결본 `{월}_retrieve.jsonl`로 자신의 모델 답변을 생성한다.
2. `sample_submission.jsonl` 포맷에 맞춰 답변 파일을 만든다.
3. 운영자에게 제출하면, 보류된 정답으로 채점해 결과를 회신한다.
4. 주요 모델 리더보드는 운영자가 직접 돌려 회차별로 공개한다.

제출 포맷(회차별 `sample_submission.jsonl` 참조):

```json
{"id": "<문항 ID>", "prediction": "<모델 답변>"}
```

각 조건(`closed`/`retrieved`/`oracle`)별로 답변을 제출할 수 있다.

## 과거 회차 (정답 공개) — 자율 채점

평가 창이 닫힌 과거 회차는 정답(`_qa`)·원문(`_source`)이 공개되므로, 배포된 `evaluate.py`로 직접 채점할 수 있다.

```bash
cd release/<과거 회차>
python evaluate.py --help
```

## 채점 지표

- **Relaxed** — 핵심을 맞혔는가 (부연이 붙어도 통과)
- **Strict** — 군더더기 없이 정확히 답했는가
- **환각률** — 맞혔으나 근거 없는 사실을 덧붙였는가 (Relaxed 통과 & Strict 실패)

> `closed` 점수는 모델 지식 순위로 해석하지 않는다. 모르면 거부하는 모델은 낮게, 추측하는 모델은 높게 나오기 때문이다. 능력 비교는 `retrieved`/`oracle`이 적절하다.

## 문의·제출

taehwan.oh@upstage.ai
