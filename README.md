# Ko-RealtimeQA

한국어 **최신성(time-sensitive) QA 벤치마크**. `korea.kr`(대한민국 정책브리핑) 정책뉴스를 재료로, 모델의 지식 cutoff 이후에 일어난 사건·사실을 묻는 질문-정답 세트를 매월 발행하는 **dynamic 벤치마크**다. 각 회차는 독립 스냅샷이다.

- 용도: **학술·연구용**
- 회차 단위: 월별 (예: `2026-06` = 2026년 6월 발행 기사 기준)
- 평가 조건: `closed` / `retrieved` / `oracle` 3종

> 이 저장소는 **데이터셋과 평가 도구**를 배포한다. 문항을 생성·검증하는 파이프라인 코드는 포함되지 않는다(§생성 방식 참조).

## 왜 필요한가

LLM은 학습 cutoff 이후의 사건·수치를 스스로 알 수 없다. 정답을 **cutoff 이후 발행 뉴스**로 구성하면 기억으로는 풀 수 없어, "최신 정보를 얼마나 잘 활용하는가"만 남는다. 정보 제공량을 바꿔(`closed` 질문만 / `retrieved` 검색 주입 / `oracle` 원문 주입) 이를 분리 측정하며, 점수는 전형적으로 `closed ≪ retrieved ≪ oracle`로 오른다.

> **예)** Q. 인사혁신처가 2026년 4월 기준으로 발표한 공무원 보수 인상률은? → A. `3.5%`

## 저장소 구조

```
Ko-RealtimeQA/
├── README.md                    데이터셋 소개·사용법 (이 파일)
├── LICENSE.md
├── release/                     회차별 데이터 (월별로 업데이트)
│   ├── 2026-06/                     과거 회차 — 정답 공개
│   │   ├── 202606_qa.jsonl              정답 포함 (채점 기준)
│   │   ├── 202606_qa_public.jsonl       정답 공란 (배포용 질문)
│   │   ├── 202606_source.jsonl          정답 출처 원문 (oracle 조건)
│   │   ├── 202606_retrieve.jsonl        웹검색 동결본 (retrieved 조건)
│   │   ├── manifest.json                메타·SHA256·라이선스
│   │   └── report.md                    운영자 평가 리포트 (주요 모델 성적)
│   ├── 2026-07/ …                   과거 회차 — 정답 공개 (구성 동일)
│   └── 2026-08/ …                   현재 회차 — gold 정답 `_qa`만 보류, 나머지(`_qa_public`·`_source`·`_retrieve`·report) 공개
├── eval/
│   ├── evaluate.py              단독 실행 평가·제출 스크립트 (requests만 필요)
│   ├── sample_submission.jsonl  제출 포맷 예시
│   └── <YYYY-MM>/               evaluate.py 실행 결과 (자동 생성)
└── docs/
    └── SUBMISSION.md            제출·채점 방식
```

## 평가 조건

| 조건 | 주입 자료 | 의미 |
|---|---|---|
| **closed** | 없음(질문만) | 모델 내부 지식만으로 답 |
| **retrieved** | 웹검색 top-10 동결본 | 고정 검색 결과 주입 (전 모델 동일 → 공정·재현) |
| **oracle** | 정답 출처 원문 | 성능 상한선 |

판정은 LLM judge가 **Relaxed / Strict / 환각률**로 매긴다. 상세는 [docs/SUBMISSION.md](docs/SUBMISSION.md).

---

## 리더보드 (주요 모델, relaxed / strict / 환각률 %)

운영자가 회차별로 주요 모델을 직접 평가한 결과. 전 모델에서 `closed ≪ retrieved ≪ oracle`.

### 2026-08 (n=242)
| 모델 | closed | retrieved | oracle |
|---|---|---|---|
| GPT-5.6 Terra | 39.7 / 32.2 / 9.1 | 81.8 / 74.8 / 7.0 | 100.0 / 96.7 / 3.3 |
| GPT-5.6 Sol | 38.8 / 30.2 / 9.5 | 83.5 / 75.2 / 8.7 | 100.0 / 96.3 / 3.7 |
| Claude Opus 5 | 22.3 / 18.6 / 4.1 | 71.9 / 47.9 / 24.0 | 99.2 / 85.5 / 13.6 |
| Gemini 3.5 Flash | 18.9 / 15.1 / 4.2 | 71.5 / 64.0 / 7.9 | 99.2 / 95.0 / 4.1 |
| Gemini 3.1 Pro | 16.9 / 12.4 / 5.0 | 71.9 / 64.5 / 7.4 | 99.2 / 93.8 / 5.4 |
| Claude Haiku 4.5 | 3.7 / 4.1 / 0.0 | 68.2 / 57.0 / 11.2 | 95.9 / 90.9 / 5.0 |
| **평균** | **23.4** | **74.8** | **98.9** |

> `closed`는 지식 순위가 아니다(모르면 거부 vs 추측하는 행동 차이). 능력 비교는 `retrieved`/`oracle` 기준.
> 이전 회차 성적은 각 `release/<월>/report.md` 참조.

## 빠른 시작 — 내 모델 평가

`eval/evaluate.py` 하나로 실행된다(저장소 불필요, `requests`만 필요). **회차(월)만 지정**하면 그 회차에 정답이 있는지로 자동 분기한다.

```bash
# 과거 회차(정답 공개) → 답변 생성 + 채점 + 리포트
python eval/evaluate.py --month 2026-06 \
  --model-base-url https://<host>/v1 --model-name <내-모델-id> --model-key <KEY> \
  --upstage-key <UPSTAGE_KEY>

# 현재 회차(정답 미공개) → 답변만 생성해 제출 파일 (채점 키 불필요)
python eval/evaluate.py --month 2026-08 \
  --model-base-url https://<host>/v1 --model-name <내-모델-id> --model-key <KEY>
```

- 정답(`_qa.jsonl`)이 있으면 **채점 + 리포트**(`report.md`), 없으면 **제출 파일**(`submission_<조건>.jsonl`)만 생성한다.
- 결과는 **`eval/<YYYY-MM>/`** 에 저장된다.
- 후보 모델이 OpenAI 호환 엔드포인트가 아니면 스크립트의 `call_candidate` 한 곳만 자신의 추론으로 교체하면 된다.

## 운영 방식

- **매월**: 새 회차의 **질문(`_qa_public`)·원문(`_source`)·검색 동결본(`_retrieve`)**과 주요 모델 리더보드를 공개한다. 오염 방지를 위해 **우리가 생성한 gold 정답(`_qa`)만 보류**한다(원문 기사는 이미 공개된 korea.kr 웹 문서라 보류 대상이 아니다).
- **창 종료(익월)**: 평가 창이 닫히면 보류했던 **gold 정답(`_qa`)까지 공개**하며, 그 회차는 재현·연구용 과거 회차가 된다.
- **채점**: 현재 회차는 **제출형**으로 운영한다(모델 답변 제출 → 운영자가 보류된 정답으로 채점). 과거 회차는 정답이 공개되어 자율 채점이 가능하다. 상세는 [docs/SUBMISSION.md](docs/SUBMISSION.md).

## 생성 방식

문항은 뉴스 원문에서 자동 생성·검증된다. 요지는 **정답을 먼저 확정한 뒤 그 답을 묻는 질문을 만드는 역방향 생성** + **다지표·왕복 재풀이 자동 검증**으로, 최신성 없는 문항과 정답 누설을 앞단에서 차단한다. **생성·검증 파이프라인의 실행 코드·프롬프트는 공개하지 않는다**(벤치마크 무결성 보호).

## 라이선스

- QA·원문 (`_qa` / `_qa_public` / `_source`): **CC BY 4.0** (korea.kr 정책뉴스, 공공누리 제1유형)
- 검색 스냅샷 (`_retrieve`): **연구용(research use only)** — 제3자 웹 콘텐츠, 상업적 이용 불가

회차별 상세·체크섬은 각 `release/<월>/manifest.json` 참조. 자세한 내용은 [LICENSE.md](LICENSE.md).

문의: taehwan.oh@upstage.ai
