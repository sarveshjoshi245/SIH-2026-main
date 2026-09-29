def test_get_existing_connection_200(client, interop_headers):
    response = client.get("/api/electricity/connections/CONS-778899", headers=interop_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["cons_no"] == "CONS-778899"
    assert data["cust_name"] == "ABC Industries Pvt Ltd"
    assert data["cust_pan"] == "ABCDE1234F"
    assert data["cat_code"] == "HT-IND"
    assert data["conn_stat"] == "ENERGIZED"
    assert data["meter_stat"] == "INSTALLED"
    assert data["dues_flag"] is False


def test_get_non_existing_connection_404(client, interop_headers):
    response = client.get("/api/electricity/connections/CONS-999999", headers=interop_headers)
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "NOT_FOUND"
    assert data["consumer_number"] == "CONS-999999"
