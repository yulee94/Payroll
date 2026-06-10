# KCOMWEL 만 65세 고용보험 API 연동 (Phase 2)

## 개요

만 65세 이상 근로자의 **고용보험(실업급여) 공제 여부**는 근로복지공단(KCOMWEL)에서 조회한 **개인별 부과고지보험료**에 따라 달라집니다.

| 부과고지보험료 | 실업급여 자격 | 급여 공제 |
|----------------|---------------|-----------|
| **0원** | 비대상 | 고용보험 **납부 없음** (공제 0) |
| **0원 초과** | 대상 | 고용보험 **공제 적용** (일반 요율) |

Phase 1(현재)은 HR이 포털에서 조회한 결과를 **수동 등록** 또는 **CSV import**합니다.  
Phase 2는 아래 워크플로를 `KcomwelEmploymentInsuranceProvider`로 자동화합니다.

---

## KCOMWEL 포털 조회 절차 (수동 · API 대상 동일)

**[근로복지공단]** 공인인증서 로그인 → 정보조회 → 보험가입정보조회 → **개인별 부과고지보험료조회**

1. 사업장 **관리번호**(산재관리번호) 확인
2. **성명**으로 검색
3. **부과고지보험료** 확인
   - `0` → 실업급여 비대상 → 급여에서 고용보험 공제 **하지 않음**
   - `0` 초과 → 실업급여 대상 → 급여에서 고용보험 **공제**

포털: https://total.kcomwel.or.kr

---

## 프로그램 연동 (Phase 1 — 현재)

- 모듈: `Rust-owned contract`
- UI: **급여 설정** → **「만 65세 고용보험」**
- CSV 컬럼 예: `관리번호`, `성명`, `부과고지보험료`, `조회일` (별칭 지원)
- 사업장 **산재관리번호**: `payroll_settings`의 `site_settings[사업장].kcomwel_management_no` (선택)

### 미확인(unknown) 기본 동작

KCOMWEL 조회 이력이 없으면 **경고**를 표시하고 설정값을 적용합니다.

| 설정 | 동작 |
|------|------|
| `skip` (기본) | 고용보험 공제 **생략** |
| `deduct` | 일반 요율로 **공제** (보수적 과납 방지용) |

---

## Phase 2 — Production provider contract

공인인증서 로그인 및 공식 API·EDI 제휴가 필요합니다. 자동 조회는 Rust 서비스가 구현될 때까지 명시적으로 비활성 상태로
추가하지 않고 Rust `bitween-payroll-api` provider boundary에서 구현합니다.

Provider readiness must expose whether the integration is live, the source of the
premium record, and a failure mode that keeps payroll execution blocked or
requires manual CSV evidence rather than silently calculating from missing data.

### 연동 시 처리 흐름

1. `resolve_site_kcomwel_management_no(workplace)` 로 사업장 관리번호 조회
2. `provider.lookup_premium(management_no, employee_name)` 호출
3. 결과를 `VerificationRecord`로 저장 (`source="api"`)
4. `resolve_ei_65_for_payroll()` 이 premium 기준으로 `exempt` / `liable` 판정

---

## 급여 산출 규칙 요약

- **만 65세 미만**: 고용보험 일반 계산
- **만 65세 이상**:
  - 국민·건강·장기요양: 기존과 동일 **면제 (0원)**
  - 고용보험: KCOMWEL 확인 결과에 따름
    - premium = 0 → 공제 0
    - premium > 0 → `보수총액 × 0.9%` (10원 단위)
    - 미확인 → 경고 + `unknown_default` 설정 적용

---

## 테스트

```bash
buck2 test //crates/payroll-api:payroll_api_test
buck2 test //crates/payroll-api:payroll_api_test
```
