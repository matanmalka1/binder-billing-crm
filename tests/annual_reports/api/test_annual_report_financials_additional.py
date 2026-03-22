from tests.annual_reports.api.test_annual_report_financials import _create_report


def test_update_and_delete_income_and_expense_lines(client, test_db, advisor_headers):
    report = _create_report(test_db)

    income = client.post(
        f"/api/v1/annual-reports/{report.id}/income",
        headers=advisor_headers,
        json={"source_type": "salary", "amount": 1000, "description": "before"},
    )
    assert income.status_code == 201
    income_id = income.json()["id"]

    income_update = client.patch(
        f"/api/v1/annual-reports/{report.id}/income/{income_id}",
        headers=advisor_headers,
        json={"description": "after"},
    )
    assert income_update.status_code == 200
    assert income_update.json()["description"] == "after"

    income_delete = client.delete(
        f"/api/v1/annual-reports/{report.id}/income/{income_id}",
        headers=advisor_headers,
    )
    assert income_delete.status_code == 204

    expense = client.post(
        f"/api/v1/annual-reports/{report.id}/expenses",
        headers=advisor_headers,
        json={"category": "other", "amount": 500, "description": "old"},
    )
    assert expense.status_code == 201
    expense_id = expense.json()["id"]

    expense_update = client.patch(
        f"/api/v1/annual-reports/{report.id}/expenses/{expense_id}",
        headers=advisor_headers,
        json={"description": "new"},
    )
    assert expense_update.status_code == 200
    assert expense_update.json()["description"] == "new"

    expense_delete = client.delete(
        f"/api/v1/annual-reports/{report.id}/expenses/{expense_id}",
        headers=advisor_headers,
    )
    assert expense_delete.status_code == 204


def test_financial_lines_invalid_types_and_not_found(client, test_db, advisor_headers):
    report = _create_report(test_db)

    bad_income_update = client.patch(
        f"/api/v1/annual-reports/{report.id}/income/999999",
        headers=advisor_headers,
        json={"source_type": "invalid_source"},
    )
    assert bad_income_update.status_code == 422

    missing_income_delete = client.delete(
        f"/api/v1/annual-reports/{report.id}/income/999999",
        headers=advisor_headers,
    )
    assert missing_income_delete.status_code == 404

    bad_expense_update = client.patch(
        f"/api/v1/annual-reports/{report.id}/expenses/999999",
        headers=advisor_headers,
        json={"category": "invalid_category"},
    )
    assert bad_expense_update.status_code == 422

    missing_expense_delete = client.delete(
        f"/api/v1/annual-reports/{report.id}/expenses/999999",
        headers=advisor_headers,
    )
    assert missing_expense_delete.status_code == 404
