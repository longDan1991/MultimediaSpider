import httpx


headers = {"xc-token": "hsiqgFIZhFs3TE2MOhxroemK7Wyx-tn4F82WeMmF"}
tasks_url = "https://app.nocodb.com/api/v2/tables/mkvxfjrss5r29e8/records"


async def get_tasks(params: dict = {}):

    querystring = {
        "offset": "0",
        "limit": "25",
        "where": "",
        "viewId": "vwayk09j4s14bpvr",
    }

    querystring.update(params)

    async with httpx.AsyncClient() as client:
        response = await client.get(tasks_url, headers=headers, params=querystring)
        return response.json()


async def create_task(data: dict):

    async with httpx.AsyncClient() as client:
        response = await client.post(tasks_url, headers=headers, json=data)
        return response.json()
