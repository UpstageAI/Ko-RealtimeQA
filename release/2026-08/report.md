# 평가 리포트 — Ko-RealtimeQA 2026-08 (n=242)

- **대상**: `release/2026-08` 공개 QA 242문항 (korea.kr 정책뉴스, 2026년 8월)
- **모델**: 6종 (제공사별 SOTA 1 + 저가 1), 후보 = Timely Router
- **조건**: closed / retrieved / oracle
- **판정**: LLM-as-judge = solar-pro3, Relaxed / Strict + 환각률(=relaxed 1 & strict 0)
- **생성**: solar-pro4 (2026-08 회차부터 생성기 pro3→pro4 전환; 판정은 pro3 유지)

## 1. 결과 (relaxed / strict / 환각률, %)

| 모델 | tier | closed | retrieved | oracle |
|---|---|---|---|---|
| Claude Haiku 4.5 | cheap | 3.7% / 4.1% / 0.0% | 68.2% / 57.0% / 11.2% | 95.9% / 90.9% / 5.0% |
| Claude Opus 5 | sota | 22.3% / 18.6% / 4.1% | 71.9% / 47.9% / 24.0% | 99.2% / 85.5% / 13.6% |
| Gemini 3.1 Pro (Preview) | sota | 16.9% / 12.4% / 5.0% | 71.9% / 64.5% / 7.4% | 99.2% / 93.8% / 5.4% |
| Gemini 3.5 Flash | cheap | 18.9% / 15.1% / 4.2% | 71.5% / 64.0% / 7.9% | 99.2% / 95.0% / 4.1% |
| GPT-5.6 Sol | sota | 38.8% / 30.2% / 9.5% | 83.5% / 75.2% / 8.7% | 100.0% / 96.3% / 3.7% |
| GPT-5.6 Terra | cheap | 39.7% / 32.2% / 9.1% | 81.8% / 74.8% / 7.0% | 100.0% / 96.7% / 3.3% |
| **평균** | | **23.4%** | **74.8%** | **98.9%** |

> 셀 = relaxed / strict / 환각률. 전 모델에서 `closed ≪ retrieved ≪ oracle` 단조 증가가 정상.

## 2. 최신성 격차와 헤드룸

| 모델 | 검색이득 Δ(closed→retrieved) | 헤드룸(oracle−retrieved) |
|---|---:|---:|
| Claude Haiku 4.5 | +64.5% | 27.7% |
| Gemini 3.1 Pro (Preview) | +55.0% | 27.3% |
| Gemini 3.5 Flash | +52.6% | 27.7% |
| Claude Opus 5 | +49.6% | 27.3% |
| GPT-5.6 Sol | +44.6% | 16.5% |
| GPT-5.6 Terra | +42.1% | 18.2% |

> **검색이득 Δ** = 검색 의존도(클수록 폐쇄형에서 모르던 걸 검색으로 메움). **헤드룸** = 완벽 컨텍스트(oracle) 대비 실제 검색이 남기는 손실.

## 3. 도메인별 분석 (전 모델 평균 relaxed %)

| 도메인 | 문항 | closed | retrieved | oracle |
|---|---:|---:|---:|---:|
| economy | 110 | 19.6% | 79.4% | 98.6% |
| society | 97 | 23.5% | 69.8% | 99.5% |
| diplomacy | 19 | 45.6% | 72.8% | 99.1% |
| culture | 16 | 22.1% | 76.0% | 96.9% |

## 4. 카테고리별 분석 (전 모델 평균 relaxed %)

| 카테고리 | 문항 | closed | retrieved | oracle |
|---|---:|---:|---:|---:|
| Factoid | 143 | 22.3% | 78.9% | 99.0% |
| Temporal | 88 | 21.4% | 69.7% | 98.9% |
| Causal | 11 | 53.0% | 62.1% | 98.5% |
