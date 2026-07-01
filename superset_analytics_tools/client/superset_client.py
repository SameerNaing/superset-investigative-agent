import os 
import json
import requests

from ..environments import SUPERSET_BASEURL, SUPERSET_PASSWORD, SUPERSET_USERNAME

API_BASE_URL = os.path.join(SUPERSET_BASEURL, "api", "v1")


def login():
    payload = json.dumps({
        "password": SUPERSET_PASSWORD, 
        "provider": "db", 
        "refresh": False, 
        "username": SUPERSET_USERNAME
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    url = os.path.join(API_BASE_URL, "security", "login")
    
    res = requests.request("POST", url, headers=headers, data=payload)
    
    res = res.json()
    return res["access_token"]


def get_chart_detail(chart_id):
   token = login() 
   
   headers = {
    'Authorization': 'Bearer ' + token
   }
   
   url = os.path.join(API_BASE_URL, "explore/")
   
   res = requests.request("GET", url, params={"slice_id": chart_id}, headers=headers)
   res = res.json()
   
   
   return res 
   
   
def get_filter_values(data_source_id, col_name):
    token = login()
    url = os.path.join(API_BASE_URL, "datasource", "table", str(data_source_id), "column", col_name, "values/")
    headers = {
        'Accept': 'application/json',
        "Authorization": "Bearer "  + token
    }
    
    
    res = requests.request("GET", url, headers=headers)
    
    return  res.json().get("result", [])

def get_chart_info(chart_id): 
    token = login()
    url = os.path.join(API_BASE_URL, "chart", str(chart_id))
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + token
    }
    
    response = requests.request("GET", url, headers=headers) 
    response = response.json() 
    result = response.get("result", {})

    result["params"] = json.loads(result['params'])
    
    return result

def get_chart_data_table(payload):
    token = login()
    url = os.path.join(API_BASE_URL, "chart", "data")
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + token
    }
    
    payload = json.dumps({
            **payload, 
            "result_type": "results"
        })
    
    
    res = requests.request("POST", url, headers=headers, data=payload)
    return res.json().get("result", []) 


def get_chart_list(page=0, page_size=10):
    token = login()
    url = os.path.join(API_BASE_URL, "chart/")
    
    headers = {
        'Authorization': 'Bearer ' + token
    }
    
    q_parts = [
        f"page:{page}",
        f"page_size:{page_size}",
    ]
    
    params = {"q": f"({','.join(q_parts)})"}
    
    res = requests.request("GET", url, headers=headers, params=params)
        
    return res.json().get("result", [])


def get_chart(chart_id):
    token = login() 
    url = os.path.join(API_BASE_URL, "chart", str(chart_id))
    headers ={
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + token
    }
    
    res = requests.request("GET", url, headers=headers)
    return res.json().get("result", {})

