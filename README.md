# TaxDataValidator 1.0

Python-based Withholding Tax Data Validation System

## 프로젝트 소개

기업의 원천세 신고 과정에서 발생할 수 있는 세액 계산 오류,
데이터 누락 및 중복, 신고자료 불일치를 탐지하기 위한
규칙 기반 세무 데이터 검증 프로젝트입니다.

## 개발 목적

- 원천징수세액 계산 및 검증 자동화
- 신고 기초자료의 정합성 확보
- 지급 원장과 신고자료 간 대사 자동화
- 세무 담당자의 추가 검토 대상 식별
- 검증 결과의 Excel 보고서 생성

## 주요 기능

| 기능 | 구현 내용 |
|---|---|
| Synthetic Data | 재현 가능한 가상 지급자료 200행 생성 |
| Tax Calculation | 이자·사업·기타소득 원천징수세액 재계산 |
| Tax Validation | 과세최저한 및 소액부징수 예외 검증 |
| Data Validation | 필수값 누락, 중복, 금액 및 날짜 오류 탐지 |
| Reconciliation | 지급 원장과 신고 상세·집계자료 대사 |
| Exception Handling | 오류 및 추가 검토 대상 분류 |
| Reporting | 9개 시트로 구성된 Excel 보고서 생성 |
| Unit Testing | 정상·오류·경계값·예외 테스트 |
| Benchmark | 반복 실행 성능 및 재현성 측정 |

## 기술 스택

- Python
- Pandas
- NumPy
- Openpyxl
- Pytest
- JupyterLab
- Git / GitHub

## 프로젝트 구조

    TaxDataValidator/
    ├── data/
    │   ├── payments.csv
    │   ├── filing_details.csv
    │   ├── filing_summary.csv
    │   └── ground_truth.csv
    ├── src/
    │   ├── __init__.py
    │   ├── generate_data.py
    │   ├── tax_rules.py
    │   ├── validator.py
    │   ├── reconciliation.py
    │   └── report.py
    ├── tests/
    │   ├── test_tax_rules.py
    │   └── test_validation.py
    ├── docs/
    │   └── tax_rules.md
    ├── outputs/
    │   ├── validation_report.xlsx
    │   └── benchmark.csv
    ├── notebooks/
    ├── main.py
    ├── requirements.txt
    └── README.md

## 실행 방법

    pip install -r requirements.txt
    python main.py

기존 가상 데이터 재사용:

    python main.py --reuse-data

단위 테스트:

    python -m pytest tests -q

## 검증 상태

- PASS: 구현된 검증 규칙상 이상 없음
- ERROR: 데이터 또는 계산상 오류
- REVIEW: 추가 세무 검토 필요
- BLOCKED: 정합성 오류로 대사 보류

## 검증 규칙

- DATA-01~04: 데이터 정합성 검증
- TAX-01~07: 원천징수세액 및 세무 판단 검증
- REC-01~04: 신고자료 대사

## 결과물

- [Excel 검증 보고서](outputs/validation_report.xlsx)
- [반복 실행 결과](outputs/benchmark.csv)
- [세법 근거 및 적용 범위](docs/tax_rules.md)

## 정확성 평가

사전에 수기로 계산한 세액 사례와 독립적으로 지정한
오류 정답표를 기준으로 Precision과 Recall을 측정합니다.

해당 지표는 가상 데이터에 삽입한 오류에 대한 탐지 성능이며,
실제 기업의 세무 업무 정확도를 의미하지 않습니다.

## 적용 범위 및 한계

본 프로젝트는 국내 거주자인 개인의 일반 과세 예금이자,
특정 인적용역 사업소득 및 일시적 강연료를 대상으로 합니다.

실제 세무 신고 프로그램이 아닌 학습용 검증 시뮬레이션이며,
비거주자 과세, 근로소득, 조세특례, 실제 전자신고 등은
지원 범위에 포함되지 않습니다.

## Disclaimer

All datasets are synthetic.
This project is intended for educational and portfolio purposes.
It is not a production tax filing system.


## 실행 및 검증 결과

| 평가 항목 | 결과 |
|---|---:|
| 가상 지급자료 | 200행 |
| 검증 규칙 | 15개 |
| 단위 테스트 통과 | 66개 |
| 반복 실행 | 5회 |
| 평균 실행시간 | 1.0166초 |
| 중앙값 실행시간 | 0.7434초 |
| 평균 Precision | 100.00% |
| 평균 Recall | 100.00% |
| 오탐 합계 | 0건 |
| 미탐 합계 | 0건 |

실행환경: MacBook Pro 2017 Intel, JupyterLab

측정 시간에는 가상 데이터 생성, CSV 입출력,
세액 검증, 신고자료 대사 및 Excel 보고서 생성이 포함됩니다.
