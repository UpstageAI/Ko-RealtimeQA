# 평가 리포트 — Ko-RealtimeQA 2026-07 (n=272)

- **대상**: `release/2026-07` 공개 QA 272문항 (korea.kr 정책뉴스, 2026년 7월)
- **모델**: 6종 (제공사별 SOTA 1 + 저가 1), 후보 = Timely Router
- **조건**: closed / retrieved / oracle
- **판정**: LLM-as-judge = solar-pro3, Relaxed / Strict + 환각률(=relaxed 1 & strict 0)
- **생성**: solar-pro3

## 1. 결과 (relaxed / strict / 환각률, %)

| 모델 | tier | closed | retrieved | oracle |
|---|---|---|---|---|
| Claude Opus 5 | sota | 19.1% / 12.9% / 6.2% | 62.1% / 37.9% / 24.3% | 93.4% / 66.9% / 26.5% |
| Claude Haiku 4.5 | cheap | 5.9% / 3.3% / 2.6% | 55.5% / 42.6% / 13.2% | 87.5% / 73.2% / 14.3% |
| GPT-5.6 Sol | sota | 44.5% / 35.7% / 9.9% | 76.1% / 66.5% / 9.9% | 94.9% / 86.4% / 8.8% |
| GPT-5.6 Terra | cheap | 40.4% / 33.1% / 7.7% | 71.0% / 62.5% / 8.8% | 94.5% / 85.3% / 9.2% |
| Gemini 3.1 Pro (Preview) | sota | 20.6% / 15.4% / 5.9% | 58.8% / 50.0% / 8.8% | 94.1% / 83.5% / 11.0% |
| Gemini 3.5 Flash | cheap | 26.1% / 21.0% / 5.5% | 59.6% / 50.7% / 8.8% | 93.8% / 82.4% / 11.4% |
| **평균** | | **26.1%** | **63.8%** | **93.0%** |

> 셀 = relaxed / strict / 환각률. 전 모델에서 `closed ≪ retrieved ≪ oracle` 단조 증가가 정상.

## 2. 최신성 격차와 헤드룸

| 모델 | 검색이득 Δ(closed→retrieved) | 헤드룸(oracle−retrieved) |
|---|---:|---:|
| Claude Haiku 4.5 | +49.6% | 32.0% |
| Claude Opus 5 | +43.0% | 31.2% |
| Gemini 3.1 Pro (Preview) | +38.2% | 35.3% |
| Gemini 3.5 Flash | +33.5% | 34.2% |
| GPT-5.6 Sol | +31.6% | 18.8% |
| GPT-5.6 Terra | +30.5% | 23.5% |

> **검색이득 Δ** = 검색 의존도(클수록 폐쇄형에서 모르던 걸 검색으로 메움). **헤드룸** = 완벽 컨텍스트(oracle) 대비 실제 검색이 남기는 손실.

## 3. 도메인별 분석 (전 모델 평균 relaxed %)

| 도메인 | 문항 | closed | retrieved | oracle |
|---|---:|---:|---:|---:|
| economy | 119 | 25.2% | 63.4% | 93.8% |
| society | 99 | 24.6% | 63.5% | 92.1% |
| diplomacy | 32 | 30.2% | 74.0% | 91.7% |
| culture | 22 | 31.8% | 53.0% | 94.7% |

## 4. 카테고리별 분석 (전 모델 평균 relaxed %)

| 카테고리 | 문항 | closed | retrieved | oracle |
|---|---:|---:|---:|---:|
| Factoid | 178 | 24.6% | 65.0% | 96.8% |
| Temporal | 63 | 19.6% | 59.5% | 80.7% |
| Causal | 31 | 47.8% | 66.1% | 96.2% |
