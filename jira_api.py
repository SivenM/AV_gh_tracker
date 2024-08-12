import sys
import requests
from requests.auth import HTTPBasicAuth
import json


class JiraMaster:

    def __init__(self, domain:str, email:str, token:str) -> None:
        self.domain = domain
        self.email = email
        self.token = token
        self.auth = HTTPBasicAuth(f"{email}", token)
        self.headers = {
        	"Accept": "application/json"
        }

    def get_response(self, url):
        response = requests.request(
        "GET",
        url,
        headers=self.headers,
        auth=self.auth
        )
        return json.loads(response.text)

    def get_date(self, str_date:str) -> dict:
        splitted_str_date = str_date.split('T')
        date = splitted_str_date[0].replace('-', ':')
        splitted_time_gmt = splitted_str_date[-1].split('.')
        time = splitted_time_gmt[0]
        gmt = splitted_time_gmt[1]
        return {'date': date, 'time': time, 'gmt': gmt}

    def extract_issue(self, response:dict) -> dict:
        data = {}
        try:
            data["name"] = response["key"]
        except KeyError:
            print(f"{response['errorMessages'][0]}")
            return None
        fields = response["fields"]
        data["type"] = fields["issuetype"]['name']
        if "created" in list(fields.keys()):
            data["created"] = self.get_date(fields["created"])
        #data["updated"] = self.get_date(fields["updated"])
        data["priority"] = fields["priority"]['name']
        return data

    def get_issue_type(self, issue_key:str) -> str:
        if issue_key:
            url = f"https://{self.domain}.atlassian.net/rest/api/3/issue/{issue_key}"
            response = self.get_response(url)
            issue_type = response['fields']['issuetype']['name']
            return issue_type    
        else:
            return None

    def get_issue_data(self, issue_key) -> dict:
        url = f"https://{self.domain}.atlassian.net/rest/api/3/issue/{issue_key}"
        response = self.get_response(url)
        data = self.extract_issue(response)
        return data
    

