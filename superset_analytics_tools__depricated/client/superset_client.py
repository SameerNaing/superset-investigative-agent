import json
import os

import requests

from ..environments import SUPERSET_BASEURL, SUPERSET_PASSWORD, SUPERSET_USERNAME

API_BASE_URL = os.path.join(SUPERSET_BASEURL, "api", "v1")


def login(*, return_session: bool = False, refresh: bool = True):
    payload = {
        "password": SUPERSET_PASSWORD,
        "provider": "db",
        "refresh": refresh,
        "username": SUPERSET_USERNAME,
    }

    url = os.path.join(API_BASE_URL, "security", "login")

    session = requests.Session()
    login_res = session.post(url, json=payload, headers={"Accept": "application/json"})
    login_res.raise_for_status()
    token = login_res.json()["access_token"]

    session.headers.update(
        {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )

    if return_session:
        csrf_url = os.path.join(API_BASE_URL, "security", "csrf_token/")
        csrf_res = session.get(csrf_url, headers={"Accept": "application/json"})
        csrf_res.raise_for_status()
        csrf_token = csrf_res.json()["result"]
        session.headers.update(
            {
                "X-CSRFToken": csrf_token,
            }
        )

    if return_session:
        return session
    return token


def get_chart_detail(chart_id):
    token = login()

    headers = {"Authorization": "Bearer " + token}

    url = os.path.join(API_BASE_URL, "explore/")

    res = requests.request("GET", url, params={"slice_id": chart_id}, headers=headers)
    res = res.json()

    return res


def get_filter_values(data_source_id, col_name):
    token = login()
    url = os.path.join(
        API_BASE_URL,
        "datasource",
        "table",
        str(data_source_id),
        "column",
        col_name,
        "values/",
    )
    headers = {"Accept": "application/json", "Authorization": "Bearer " + token}

    res = requests.request("GET", url, headers=headers)

    return res.json().get("result", [])


def get_chart_info(chart_id):
    token = login()
    url = os.path.join(API_BASE_URL, "chart", str(chart_id))
    headers = {"Accept": "application/json", "Authorization": "Bearer " + token}

    response = requests.request("GET", url, headers=headers)
    response = response.json()
    result = response.get("result", {})

    result["params"] = json.loads(result["params"])

    return result


def get_chart_data_table(payload, result_type="results"):
    token = login()
    url = os.path.join(API_BASE_URL, "chart", "data")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
    }

    payload = json.dumps({**payload, "result_type": result_type})

    res = requests.request("POST", url, headers=headers, data=payload)
    return res.json().get("result", [])


def get_chart_list(page=0, page_size=10, datasource_id=None):
    token = login()
    url = os.path.join(API_BASE_URL, "chart/")

    headers = {"Authorization": "Bearer " + token}

    q_parts = [
        f"page:{page}",
        f"page_size:{page_size}",
    ]

    if datasource_id:
        q_parts.append(f"filters:!((col:datasource_id,opr:eq,value:{datasource_id}))")

    params = {"q": f"({','.join(q_parts)})"}

    res = requests.request("GET", url, headers=headers, params=params)

    return res.json().get("result", [])


def get_chart(chart_id):
    token = login()
    url = os.path.join(API_BASE_URL, "chart", str(chart_id))
    headers = {"Accept": "application/json", "Authorization": "Bearer " + token}

    res = requests.request("GET", url, headers=headers)
    return res.json().get("result", {})


def get_dataset_list(page=0, page_size=10):
    token = login()
    url = os.path.join(API_BASE_URL, "dataset/")
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    q_parts = [
        f"page:{page}",
        f"page_size:{page_size}",
        # TODO: just for superset only list the replica db datasets
        "filters:!((col:database,opr:rel_o_m,value:1))",
    ]

    params = {"q": f"({','.join(q_parts)})"}

    res = requests.request("GET", url, headers=headers, params=params)

    return res.json().get("result", [])


def get_dataset_detail(data_source_id):
    token = login()
    url = os.path.join(API_BASE_URL, "dataset", str(data_source_id))
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    res = requests.request("GET", url, headers=headers)
    return res.json().get("result", {})


def execute_sql(database_id, sql, query_limit=1000):
    session = login(return_session=True)

    url = os.path.join(API_BASE_URL, "sqllab", "execute/")

    payload = {"database_id": database_id, "sql": sql, "queryLimit": query_limit}

    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )

    response = session.post(url, json=payload)
    response.raise_for_status()

    return response.json()
