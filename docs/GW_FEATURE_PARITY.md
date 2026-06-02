# COSS 그룹웨어(GW) ↔ Bitween 기능 대응표

> 기준: `gw.cossok.com` (2026-06-01 브라우저·`gw_import/` 스크랩) vs Bitween `급여프로그램`
> 목표: 익숙한 GW UX를 유지하면서 Bitween 브랜딩·급여/HR 코어는 분리 유지

## 요약

| 구분 | GW 모듈 수(주요) | Bitween 대응 | 이번 세션 |
|------|------------------|--------------|-----------|
| 핵심 결재·메일·홈 | 3 | workflow, workspace, launcher | 탭·공람·메일함·대시보드 위젯 |
| 협업·정보 | 6 | workspace, bulletin, org | 게시판 홈 배치 유지 |
| HR·급여 | 2+ | hr, payroll | 변경 없음(운영 중) |
| 미구현 GW 전용 | 10+ | — | 문서함·자원예약·설문 등 로드맵 |

---

## 기능 매트릭스

| GW 기능 | Bitween 모듈/화면 | 상태 | 조치 |
|---------|-------------------|------|------|
| **홈 / 미니화면** | `ui/platform_launcher.py` + `WorkspaceHub` | 부분 | 결재·메일·공람 카운트 위젯 추가 |
| **전자결재 · 결재할 문서** | `workflow` / `inbox:to_approve` | 있음 | GW 상단 탭(전체/대기/기안/공람) 정렬 |
| **전자결재 · 기안** | `inbox:my_draft`, `inbox:in_progress` | 있음 | 「기안」퀵탭 → `my_draft` |
| **전자결재 · 공람** | `inbox:circulate` (신규) | 이번 추가 | CC(참조) 전용 공람함 |
| **전자결재 · 양식함** | `core/workflow/form_templates.py` | 부분 | COSS 20+ 양식 내장, GW 전체는 스크립트 동기화 |
| **전자결재 · 진행/완료/반려** | `inbox:in_progress` 등 | 있음 | 좌측 결재함 네비 유지 |
| **메일 · 받은/보낸/안읽음** | `workspace` / `MailDialog` | 부분 | 폴더·목록 컬럼(보낸사람/제목/날짜) |
| **메일 · SMTP/외부연동** | — | 없음 | Phase 2+ (외부 메일 API) |
| **게시판 · 전사공지** | `bulletin` / `BulletinSection` | 부분 | 홈 공지 레이아웃, GW 스크랩 import |
| **일정 · 캘린더** | `workspace` 캘린더 | 부분 | 개인 일정, GW 일정 동기화 미연 |
| **조직도** | `org` + `gw_import/org_tree.json` | 있음 | 667노드 import 완료 |
| **문서함** | — | 없음 | Phase 2: `mail_filing` 또는 archive 모듈 |
| **근태** | `hr` 근태 탭 | 부분 | GW 근태결재 양식은 workflow 템플릿으로 일부 |
| **메신저** | `workspace` 메신저 | 부분 | 사내 DM, GW 메신저 클라이언트 미연 |
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

Bitween 사이드바: **플랫폼** · **그룹웨어**(전자결재·조직·업무홈) · **급여** · 기타 플랫폼(HR, KPI, …)

---

## 데이터 import (`gw_import/`)

| 파일 | 내용 |
|------|------|
| `org_tree.json` | 조직 667노드 |
| `gw_scrape_extended.json` | 결재 샘플·메일 폴더 카운트·양식명 |
| `manifest.json` | workflow 42건·bulletin 스킵 로그 |
| `browser_min_screen.json` | 미니화면 스크랩 |

재실행: `python tools/gw_import/apply_browser_import.py` (브라우저 스크랩 JSON 필요)

---

## 1회 세션에서 남은 작업 (다음 패스)

- GW 실메일/IMAP·문서함 API 연동
- 결재 양식함 전체(100+) 자동 수집·카테고리 그리드
- 게시판 GW 동일 3단 레이아웃(목록+본문)
- 자원예약·설문·일감 모듈 신규
- 근태 GW ↔ HR 양방향 동기화

---

## 테스트

- `tests/test_workflow.py` — 결재함·공람 필터
- `tests/test_workflow_inbox_gw.py` — GW 공람·메일 폴더
- `tests/test_workflow_forms.py` — 양식 검증
