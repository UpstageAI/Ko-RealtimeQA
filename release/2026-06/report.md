# 평가 리포트 — Ko-RealtimeQA 2026-06 (n=256)

- **대상**: `release/2026-06` 공개 QA 256문항 (korea.kr 정책뉴스, 2026년 6월)
- **모델**: 6종 (제공사별 SOTA 1 + 저가 1), 후보 = OpenRouter
- **조건**: `closed`(질문만) · `retrieved`(Daum 고정검색 top-10 동결본 주입, 동결 2026/07/15 11:27) · `oracle`(정답 출처 원문 주입)
- **판정**: LLM-as-judge = solar-pro3, Relaxed / Strict + 환각률(=relaxed 1 & strict 0)
- **실행**: 18조합 완주, 답변 실패 2/4608(0.04%), 전 문항 채점.

---

## 1. 결과 (relaxed / strict / 환각률, %)

| 모델 | tier | closed | retrieved | oracle |
|---|---|---|---|---|
| Claude Opus 4.8 | sota | 6.6 / 5.5 / 1.6 | 55.5 / 42.6 / 12.9 | 96.5 / 80.1 / 16.4 |
| Claude Haiku 4.5 | cheap | 3.9 / 3.9 / 0.4 | 54.3 / 42.2 / 12.1 | 90.6 / 76.2 / 14.5 |
| GPT-5.5 | sota | 35.2 / 30.9 / 5.9 | 70.3 / 57.8 / 12.9 | 98.0 / 85.9 / 12.1 |
| GPT-5.4 Nano | cheap | 18.8 / 13.3 / 5.5 | 60.2 / 52.0 / 8.2 | 97.7 / 86.7 / 10.9 |
| Gemini 3.1 Pro (preview) | sota | 17.6 / 12.5 / 5.1 | 55.9 / 47.3 / 9.0 | 95.3 / 83.2 / 12.1 |
| Gemini 3.1 Flash Lite | cheap | 21.1 / 18.8 / 2.3 | 55.9 / 48.8 / 7.0 | 93.8 / 80.9 / 12.9 |
| **평균** | | **17.2** | **58.7** | **95.3** |

**패턴은 6모델 전부 단조 증가**: `closed(17.2) ≪ retrieved(58.7) ≪ oracle(95.3)`. 약 40%p씩의 계단 → 최신성 벤치마크로서 의도대로 작동.

---

## 2. 최신성 격차와 헤드룸

| 모델 | 검색이득 Δ(closed→retrieved) | 헤드룸(oracle−retrieved) |
|---|---:|---:|
| Claude Haiku 4.5 | +50.4 | 36.3 |
| Claude Opus 4.8 | +48.9 | 41.0 |
| GPT-5.4 Nano | +41.4 | 37.5 |
| Gemini 3.1 Pro | +38.3 | 39.4 |
| Gemini 3.1 Flash Lite | +34.8 | 37.9 |
| GPT-5.5 | +35.1 | 27.7 |

- **검색이득 Δ** = 검색 의존도. 클수록 폐쇄형에서 모르던 것을 검색으로 메움.
- **헤드룸** = 완벽 컨텍스트(oracle) 대비 실제 검색(top-10)이 남기는 손실. 평균 ~37%p → **검색 품질 개선 여지가 큼**.

---

## 3. oracle 천장 = QA 품질 확인

- oracle relaxed **90.6~98.0%**: 원문만 주면 거의 다 맞힘 → **정답이 원문에 깔끔하게 존재**. 생성 품질 견고.
- oracle **strict < relaxed** 보편적이고 **환각률 11~16%**(Opus 최고 16.4): 원문을 줘도 근거 없는 사실을 덧붙임. strict가 항상 낮은 구조적 이유.

---

## 4. ⚠️ closed 점수 해석 주의 — 지식 아니라 행동

closed 편차 큼(Haiku 3.9 ~ GPT-5.5 35.2). 이는 **모델 지식이 아니라 행동 차이**:
- Anthropic(Opus·Haiku)은 모르면 **거부(abstain)** → closed 매우 낮음.
- GPT-5.5는 **적극 추론·추측** → closed 높음(웹검색 아님).

**closed relaxed를 모델 지식/성능 랭킹으로 읽으면 안 된다.** 공정한 능력 비교는 검색이득(Δ)이나 retrieved/oracle이 적절.

---

## 5. 도메인별 분석 (전 모델 평균 relaxed %)

| 도메인 | 문항 | closed | retrieved | oracle |
|---|---:|---:|---:|---:|
| economy | 102 | 16.5 | 58.7 | 93.3 |
| society | 98 | 18.0 | 61.7 | 95.9 |
| diplomacy | 31 | 15.1 | **43.5** | 96.8 |
| culture | 25 | 19.3 | **65.3** | 99.3 |

- **diplomacy가 retrieved 최저(43.5%)** — 외교·순방 사건은 Daum 웹검색으로 정답 문서를 확보하기 어렵다(국내 웹 커버리지 한계). 반면 **oracle은 96.8%**로 높아, 원문엔 답이 있으나 검색이 못 따라가는 것.
- **culture가 retrieved 최고(65.3%)·oracle 99.3%** — 문화·관광 사건은 국내 웹 노출이 많아 검색으로 잘 풀림.
- closed는 전 도메인 15~19%로 고르게 낮음 = **도메인 무관하게 최신성 유지**.

---

## 6. 카테고리별 분석 (전 모델 평균 relaxed %)

| 카테고리 | 문항 | closed | retrieved | oracle |
|---|---:|---:|---:|---:|
| Factoid | 176 | 16.2 | 59.6 | 97.3 |
| Temporal | 57 | 15.8 | 57.3 | **89.8** |
| Causal | 23 | **28.3** | 55.1 | 94.2 |

- **Causal이 closed 최고(28.3%)** — "왜/영향" 질문은 추론으로 부분 추측이 가능(사건 몰라도 그럴듯한 답 도출). 시의성이 상대적으로 약한 축.
- **Temporal이 oracle 최저(89.8%)** — 원문을 줘도 **정밀 시점(날짜·기간) 추출이 어려움**. Factoid(수치·명칭 97.3%)보다 까다로운 유형.
- retrieved는 세 카테고리 55~60%로 유사.

---

## 부록 — 산출물

- 재현: retrieved는 `202606_retrieve.jsonl` 동결본 로드(동결 2026/07/15 11:27, 재검색 불필요), oracle은 `202606_source.jsonl` 원문 주입.
- 실행: `python -m evaluation.cli run-eval --public-dir release/2026-06 --search all --out runs/eval_v2` (`EVAL_CONCURRENCY=8`)
