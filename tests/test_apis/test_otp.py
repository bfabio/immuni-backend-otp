#   Copyright (C) 2020 Presidenza del Consiglio dei Ministri.
#   Please refer to the AUTHORS file for more information.
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#   You should have received a copy of the GNU Affero General Public License
#   along with this program. If not, see <https://www.gnu.org/licenses/>.

from datetime import date
from http import HTTPStatus
from unittest.mock import patch

from pytest import mark
from pytest_sanic.utils import TestClient

from immuni_common.core.exceptions import ApiException, SchemaValidationException

_URI = "/v1/otp"
_VALID_JSON = {
    "otp": "KJ23IWY5UJ",
    "symptoms_started_on": date.today().isoformat(),
}

CONTENT_TYPE_HEADER = {"Content-Type": "application/json; charset=utf-8"}


async def test_otp_success(client: TestClient) -> None:
    with patch("immuni_otp.apis.otp.store", autospec=True, spec_set=True) as manager_store:
        response = await client.post(uri=_URI, json=_VALID_JSON, headers=CONTENT_TYPE_HEADER)
        assert response.status == HTTPStatus.NO_CONTENT.value
        assert response.headers.get("Cache-Control") == "no-store"
        assert await response.json() is None
        manager_store.assert_called_once()
        # NOTE: the actual storage in a database is tested in the manager dedicated tests (common.)


@mark.parametrize(
    "method, has_json",
    tuple(
        (method, has_json)
        for method in ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "PUT")
        for has_json in (True, False)
    ),
)
async def test_otp_method_not_allowed(method: str, has_json: bool, client: TestClient) -> None:
    response = await client._request(
        method=method, uri=_URI, json=_VALID_JSON if has_json else None, headers=CONTENT_TYPE_HEADER
    )
    assert response.status == HTTPStatus.METHOD_NOT_ALLOWED.value


async def test_otp_missing_json(client: TestClient) -> None:
    response = await client.post(uri=_URI, headers=CONTENT_TYPE_HEADER)
    assert response.status == HTTPStatus.BAD_REQUEST.value
    assert await response.json() == {
        "error_code": SchemaValidationException.error_code,
        "message": SchemaValidationException.error_message,
    }


async def test_otp_invalid_json(client: TestClient) -> None:
    response = await client.post(uri=_URI, json={"invalid": "json"}, headers=CONTENT_TYPE_HEADER)
    assert response.status == HTTPStatus.BAD_REQUEST.value
    assert await response.json() == {
        "error_code": SchemaValidationException.error_code,
        "message": SchemaValidationException.error_message,
    }


async def test_otp_store_failure(client: TestClient) -> None:
    with patch(
        "immuni_otp.apis.otp.store", side_effect=Exception(), autospec=True, spec_set=True,
    ) as manager_store:
        response = await client.post(uri=_URI, json=_VALID_JSON, headers=CONTENT_TYPE_HEADER)
        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR.value
        assert await response.json() == {
            "error_code": ApiException.error_code,
            "message": ApiException.error_message,
        }
        manager_store.assert_called_once()
