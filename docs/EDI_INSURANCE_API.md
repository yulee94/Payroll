# 사대보험 EDI 4대보험료 API 연동

## 현실 점검 (API Reality)

한국 **4대보험 EDI**(국민연금·건강보험·고용·산재)는 일반적인 “API 코드만 넣으면 누구나 조회” 형태의 **공개 REST API가 아닙니다**.

| 요건 | 설명 |
|------|------|
| 사업자 등록 | 고용주로 각 공단에 사업장 등록 |
| 인증서 | 공인인증서·공동인증서 또는 EDI 전용 인증서 |
| 이용 계약 | 공단 EDI 클라이언트 설치 또는 **웹서비스/전문(EDI) 이용 신청** |
| 데이터 형식 | 포털 **XML/CSV/고정길이 전문** 보내기·받기가 일반적 |

본 급여 프로그램은 위 제약을 전제로 **Provider 아키텍처**를 두고, 당장은 **CSV·수동(Phase 1)** 을 기본으로 합니다.

---

## 사용자 흐름 (Desired flow)

1. 각 공단 EDI·포털에서 **월 보험료 명세** 조회 또는 파일 수신  
2. **CSV 가져오기** 또는 **수동 등록**으로 프로그램에 적재  
3. **급여 설정**에서 「EDI 보험료로 급여 반영」 활성화  
4. 급여 산출 시 저장된 금액이 **자동 산출보다 우선** (없으면 기존 요율·명부값)  
5. 명세·레코드에 **`EDI 조회` 배지** (`edi_premium_badge`)

Phase 2에서 `EdiWebServiceProvider`가 공인인증서·엔드포인트로 동일 `lookup_premiums`를 구현하면 UI·급여 로직 변경 없이 연동 가능합니다.

---

## Phase 1 vs Phase 2

| 구분 | Phase 1 (현재) | Phase 2 (로드맵) |
|------|----------------|------------------|
| 데이터 소스 | EDI 포털 다운로드 CSV, 수동 입력 | `EdiWebServiceProvider` + 공단 웹서비스 |
| Provider | `LocalStoredEdiProvider` | `EdiWebServiceProvider` (스텁) |
| 저장 | `app_data/edi_insurance/{tenant_id}/{YYYY-MM}.json` | API 조회 후 동일 경로에 저장 |
| 인증 | 불필요 (파일 import) | 인증서 경로·사업자번호·API URL 설정 |

---

## 프로그램 구성

| 항목 | 경로 |
|------|------|
| 코어 모듈 | `core/payroll/edi_insurance.py` |
| 급여 반영 | `core/payroll_calc_rules.resolve_social_insurance` + `use_edi_premiums` |
| 설정 저장 | `services/payroll_settings_store` → `edi_insurance` |
| UI | **급여 설정** → 「EDI 보험료 조회 (사대보험)」 |
| 산재관리번호 | `payroll_settings` `site_settings[사업장].kcomwel_management_no` 등 (만 65세 모듈과 동일) |
| 사업자등록번호 | 테넌트 `edi_insurance.business_registration_no` 또는 사업장 `site_settings` |

### CSV 컬럼 예 (별칭 지원)

`사번`, `성명`, `주민번호`, `급여월`, `국민연금`, `건강보험`, `장기요양`, `고용보험`, `산재보험`, `관리번호`

### Provider 인터페이스

```python
class EdiInsuranceProvider(Protocol):
    def lookup_premiums(
        self, employee_id: str, rrn: str, management_no: str, period: str
    ) -> InsurancePremiumRecord: ...

    def is_live(self) -> bool: ...
```

### Phase 2 스텁

```python
from core.payroll.edi_insurance import EdiWebServiceProvider, set_provider

provider = EdiWebServiceProvider(
    endpoint_url="https://...",  # 공단 제휴 URL
    certificate_path="/path/to/cert.pfx",
    business_registration_no="123-45-67890",
)
# set_provider(provider)  # is_live() True 구현·제휴 완료 후
```

---

## 공단 포털 참고

| 공단 | 용도 | URL |
|------|------|-----|
| 국민연금공단 (NPS) | 국민연금 EDI | https://www.nps.or.kr |
| 국민건강보험 (NHIS) | 건강·장기요양 EDI | https://www.nhis.or.kr |
| 근로복지공단 (KCOMWEL) | 고용·산재 EDI | https://total.kcomwel.or.kr |

만 65세 **고용보험 부과고지**는 별도 모듈: `core/payroll/employment_insurance_65.py`, `docs/KCOMWEL_EI_65_API.md`

---

## 테스트

```bash
cd 급여프로그램
python -m pytest tests/test_edi_insurance.py -q
```
