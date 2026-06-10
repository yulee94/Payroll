# Acme Corporation웨어(GW) ↔ Bitween 기능 대응표

> 기준: `gw.example.invalid` (2026-06-01 브라우저·`gw_import/` 스크랩) vs Bitween platform
> 목표: 익숙한 GW UX를 유지하면서 Bitween branding, payroll/HR core, Rust backend, and TypeScript frontend remain cleanly separated.

## 요약

| 구분 | GW 모듈 수(주요) | Bitween 대응 | 이번 세션 |
|------|------------------|--------------|-----------|
| 핵심 결재·메일·홈 | 3 | workflow, workspace, launcher | 탭·공람·메일함·대시보드 위젯 |
| 협업·정보 | 6 | workspace, bulletin, org | 게시판 홈 배치 유지 |
| HR·급여 | 2+ | hr, payroll | 운영 기능 유지 |
| 미구현 GW 전용 | 10+ | — | 문서함·자원예약·설문 등 로드맵 |

---

## 기능 매트릭스

| GW 기능 | Bitween 모듈/화면 | 상태 | 조치 |
|---------|-------------------|------|------|
| **홈 / 미니화면** | Platform launcher + `WorkspaceHub` | 부분 | 결재·메일·공람 카운트 위젯 추가 |
| **전자결재 · 결재할 문서** | `workflow` / `inbox:to_approve` | 있음 | GW 상단 탭(전체/대기/기안/공람) 정렬 |
| **전자결재 · 기안** | `inbox:my_draft`, `inbox:in_progress` | 있음 | 「기안」퀵탭 → `my_draft` |
| **전자결재 · 공람** | `inbox:circulate` | 있음 | CC(참조) 전용 공람함 |
| **전자결재 · 양식함** | `Rust-owned contract` | 부분 | Acme 20+ 양식 내장, GW 전체는 스크립트 동기화 |
| **전자결재 · 진행/완료/반려** | `inbox:in_progress` 등 | 있음 | 좌측 결재함 네비 유지 |
| **메일 · 받은/보낸/안읽음** | `workspace` / mail surface | 부분 | 폴더·목록 컬럼(보낸사람/제목/날짜) |
| **메일 · SMTP/외부연동** | — | 없음 | Phase 2+ (외부 메일 API) |
| **게시판 · 전사공지** | `bulletin` / `BulletinSection` | 부분 | 홈 공지 레이아웃, GW 스크랩 import |
| **일정 · 캘린더** | `workspace` calendar | 부분 | 개인 일정, GW 일정 동기화 미연 |
| **조직도** | `org` + `gw_import/org_tree.json` | 있음 | 667노드 import 완료 |
| **문서함** | — | 없음 | Phase 2: `mail_filing` 또는 archive 모듈 |
| **근태** | `hr` attendance | 부분 | GW 근태결재 양식은 workflow 템플릿으로 일부 |
| **메신저** | `workspace` messenger | 부분 | 사내 DM, GW 메신저 클라이언트 미연 |
| **업무일지 / 유류비** | workflow 양식 | 있음 | 일일업무일지·유류비 지출품의서 필드 정의 |
| **업무보고 / 일감** | workflow 보고 탭 | 부분 | 주간보고 양식, GW 일감 모듈 없음 |
| **자원예약** | — | 없음 | Phase 3 |
| **주소록** | org + 사용자 검색 | 부분 | GW 공용주소록 UI 없음 |
| **설문** | — | 없음 | Phase 3 |
| **문서수발 / 기록물** | — | 없음 | Phase 3 |
| **관리자 · 라이선스** | `tenant` / `permissions` | 부분 | Bitween 테넌트 관리로 대체 |

---

## GW 좌측 메뉴 (전체메뉴 기준)

```
결재 → 결재할 문서 | 기안 | 공람
근태
일감 → 일감 등록 | 전체 일감
자원예약
메일 → 메일 쓰기 | 전체 | 받은 | 안읽은 | 보낸 | 수신확인
문서함 → 문서 등록 | 전체
설문
게시판 → 글쓰기 | 전체 | 전사 공지
주소록
문서수발 / 기록물 / 캘린더 / 업무보고 / 메신저
```

Bitween navigation: Platform, groupware/workflow, org, payroll, HR, KPI, archive, admin, settings.

---

## 데이터 import (`gw_import/`)

| 파일 | 내용 |
|------|------|
| `org_tree.json` | 조직 667노드 |
| `gw_scrape_extended.json` | 결재 샘플·메일 폴더 카운트·양식명 |
| `manifest.json` | workflow 42건·bulletin 스킵 로그 |
| `browser_min_screen.json` | 미니화면 스크랩 |

재실행: `python Rust-owned contract` (브라우저 스크랩 JSON 필요)

---

## 남은 작업

- GW 실메일/IMAP·문서함 API 연동
- 결재 양식함 전체(100+) 자동 수집·카테고리 그리드
- 게시판 GW 동일 3단 레이아웃(목록+본문)
- 자원예약·설문·일감 모듈 신규
- 근태 GW ↔ HR 양방향 동기화
- Rust API + TypeScript frontend parity for GW-like surfaces

---

## 테스트

- `Rust parity test` — 결재함·공람 필터
- `Rust parity test` — GW 공람·메일 폴더
- `Rust parity test` — 양식 검증
