import httpx


headers = {"xc-token": "hsiqgFIZhFs3TE2MOhxroemK7Wyx-tn4F82WeMmF"}


async def get_tasks(params: dict = {}):

    url = "https://app.nocodb.com/api/v2/tables/mkvxfjrss5r29e8/records"

    querystring = {
        "offset": "0",
        "limit": "25",
        "where": "",
        "viewId": "vwayk09j4s14bpvr",
    }

    querystring.update(params)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=querystring)
        return response.json()
