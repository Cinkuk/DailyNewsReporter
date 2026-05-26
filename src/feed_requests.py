import requests

"""
wrapped requests.get with header
@param url
@return (response, status_code)

if status_code == 200: return (response, 200)
else: return (None, None). including timeout and access forbidden
"""
def request_url(url: str):
    header = {
            'Accept-Language' : 'zh-HK,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6',
            'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }
    # handle timeout
    try:
        response = requests.get(url=url, headers=header)
    except:
        return (None, None)
    
    if hasattr(response, "status_code") and response.status_code == 200:
        return (response, response.status_code)
    else:
        return (None, None)