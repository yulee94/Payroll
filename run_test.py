"""
run_test.py - 급여 엔진 end-to-end 테스트

실행: python run_test.py
"""

from pathlib import Path

from excel_writer import create_sample_invoice, create_sample_templates, process_payroll

BASE_DIR = Path(__file__).parent


def main() -> None:
    create_sample_templates()
    sample = create_sample_invoice()
    print(f"샘플 청구서: {sample}")

    results, out_dir = process_payroll(sample)
    print(f"처리 인원: {len(results)}명")
    print(f"출력 폴더: {out_dir}")

    for r in results:
        print(
            f"  {r['이름']}: 총지급 {r['총지급액']:,}원 -> "
            f"실수령 {r['실수령액']:,}원"
        )

    print("\n테스트 완료 OK")


if __name__ == "__main__":
    main()
