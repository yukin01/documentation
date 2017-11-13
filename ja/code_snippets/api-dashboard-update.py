from datadog import initialize, api

options = {
    'api_key': '9775a026f1ca7d1c6c5af9d94d9595a4',
    'app_key': '87ce4a24b5553d2e482ea8a8500e71b8ad4554ff'
}

initialize(**options)

title = "My Timeboard"
description = "A new and improved timeboard!"
graphs =  [{
    "definition": {
        "events": [],
        "requests": [
            {"q": "avg:system.mem.free{*} by {host}"}
        ],
    "viz": "timeseries"
    },
    "title": "Average Memory Free By Host"
}]
template_variables = [{
	"name": "host1",
	"prefix": "host",
	"default": "host:my-host"
}]
read_only = True

api.Timeboard.update(4952, title=title, description=description, graphs=graphs, template_variables=template_variables, read_only=read_only)
