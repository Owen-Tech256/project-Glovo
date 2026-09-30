from tests.support_fixtures import SupportFixtures


class _F(SupportFixtures):
    def _delivered_order(self, client, vheaders, cheaders, rheaders, aheaders):
        branch, zone, product = self.setup_branch_with_zone(client, vheaders)
        return self.deliver_full_order(client, vheaders, cheaders, rheaders, aheaders, branch, zone, product)


class TestReportAccess(_F):
    def test_customer_cannot_request_reports(self, client, customer, login_as):
        headers = login_as(client, "customer@example.com")
        resp = client.post("/api/v1/reports/exports", headers=headers, json={"report_type": "ORDERS"})
        assert resp.status_code == 403

    def test_analyst_can_request_and_download_orders_report(self, client, vendor, customer, rider, admin, analyst, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        anheaders = login_as(client, "analyst@example.com")
        self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        create = client.post("/api/v1/reports/exports", headers=anheaders, json={"report_type": "ORDERS"})
        assert create.status_code == 201
        export = create.get_json()["data"]["export"]
        assert export["status"] == "COMPLETED"
        assert export["row_count"] == 1
        assert export["downloadable"] is True

        download = client.get(f"/api/v1/reports/exports/{export['id']}/download", headers=anheaders)
        assert download.status_code == 200
        assert download.content_type.startswith("text/csv")
        body = download.get_data(as_text=True)
        assert "order_number" in body.splitlines()[0]
        assert len(body.splitlines()) == 2

    def test_finance_report_export(self, client, vendor, customer, rider, admin, finance_admin, login_as):
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        fheaders = login_as(client, "financeadmin@example.com")
        self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        create = client.post("/api/v1/reports/exports", headers=fheaders, json={"report_type": "FINANCE"})
        assert create.status_code == 201
        assert create.get_json()["data"]["export"]["status"] == "COMPLETED"

    def test_saved_report_definition_can_be_run(self, client, super_admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        define = client.post(
            "/api/v1/reports", headers=headers,
            json={"name": "Weekly delivery health", "report_type": "DELIVERY", "access_level": "analytics.view"},
        )
        assert define.status_code == 201
        definition = define.get_json()["data"]["report_definition"]

        run = client.post(
            "/api/v1/reports/exports", headers=headers, json={"report_definition_id": definition["id"]},
        )
        assert run.status_code == 201
        assert run.get_json()["data"]["export"]["report_definition_id"] == definition["id"]

    def test_missing_report_type_and_definition_is_rejected(self, client, super_admin, login_as):
        headers = login_as(client, "superadmin@example.com")
        resp = client.post("/api/v1/reports/exports", headers=headers, json={})
        assert resp.status_code == 422
        assert resp.get_json()["error"]["code"] == "REPORT_TYPE_REQUIRED"

    def test_downloading_someone_elses_org_export_still_works_for_any_staff_with_permission(
        self, client, vendor, customer, rider, admin, analyst, finance_admin, login_as,
    ):
        """Reports are organizational, not personal - any staff holding
        reports.manage can download an export another staff member
        requested."""
        vheaders = login_as(client, "vendor@example.com")
        cheaders = login_as(client, "customer@example.com")
        rheaders = login_as(client, "rider@example.com")
        aheaders = login_as(client, "admin@example.com")
        anheaders = login_as(client, "analyst@example.com")
        fheaders = login_as(client, "financeadmin@example.com")
        self._delivered_order(client, vheaders, cheaders, rheaders, aheaders)

        export = client.post("/api/v1/reports/exports", headers=anheaders, json={"report_type": "ORDERS"}).get_json()["data"]["export"]
        resp = client.get(f"/api/v1/reports/exports/{export['id']}/download", headers=fheaders)
        assert resp.status_code == 200
