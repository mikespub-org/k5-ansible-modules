#!/usr/bin/python

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: k5_update_router_routes
short_description: Replaces the existing routes on a K5 router
version_added: "1.0"
description:
    - K5 call to update the route on a router - option is not available in the Openstack module. 
options:
   router_name:
     description:
        - Name of the router network.
     required: true
     default: None
   state:
     description:
        - State of the network. Can only be 'present'.
     required: true
     default: None
   routes:
     description:
       - routes to be applied to the router.
     required: true
     default: None
   k5_auth:
     description:
       - dict of k5_auth module output.
     required: true
     default: None
requirements:
    - "python >= 2.6"
'''

EXAMPLES = '''
# Set routes on K5 router
- k5_create_inter_project_link:
        state: present
        routes: 
          - "172.16.1.1","10.10.10.0/24"
          - "172.16.1.1","10.10.20.0/24"
        router_name: "nx-test-net-1a"
        k5_auth: "{{ k5_auth_reg.k5_auth_facts }}"
'''

RETURN = '''
- 
'''


import requests
import os
import json
from ansible.module_utils.basic import *


############## Common debug ###############
k5_debug = False
k5_debug_out = []

def k5_debug_get():
    """Return our debug list"""
    return k5_debug_out

def k5_debug_clear():
    """Clear our debug list"""
    k5_debug_out = []

def k5_debug_add(s):
    """Add string to debug list if env K5_DEBUG is defined"""
    if k5_debug:
        k5_debug_out.append(s)


############## route update functions #############

def k5_get_endpoint(e,name):
    """Pull particular endpoint name from dict"""

    return e['endpoints'][name]


def k5_get_router_id_from_name(module, k5_facts):
    """Get an id from a router_name"""

    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    
    router_name = module.params['router_name']

    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/routers'

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))

    try:
        response = session.request('GET', url, headers=headers)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to get data
    if response.status_code not in (200,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

    #k5_debug_add("RESP: " + str(response.json()))

    for n in response.json()['routers']:
        #k5_debug_add("Found router name: " + str(n['name']))
        if str(n['name']) == router_name:
            #k5_debug_add("Found it!")
            return n['id']

    return ''

def k5_get_port_id(module, k5_facts, port_name):
    """Check if a port_name already exists"""

    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    #port_name = module.params['name']

    session = requests.Session()

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

    url = endpoint + '/v2.0/ports'

    k5_debug_add('endpoint: {0}'.format(endpoint))
    k5_debug_add('REQ: {0}'.format(url))
    k5_debug_add('headers: {0}'.format(headers))

    try:
        response = session.request('GET', url, headers=headers)
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=e)

    # we failed to get data
    if response.status_code not in (200,):
        module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

    #k5_debug_add("RESP: " + str(response.json()))

    for n in response.json()['ports']:
        #k5_debug_add("Found port name: " + str(n['name']))
        if str(n['name']) == port_name:
            #k5_debug_add("Found it!")
            return str(n['id'])

    return ""


def k5_update_router_add_ports(module):
    """Replaces the Routes on a K5 router"""

    global k5_debug

    k5_debug_clear()

    if 'K5_DEBUG' in os.environ:
        k5_debug = True

    if 'auth_spec' in module.params['k5_auth']: 
        k5_facts = module.params['k5_auth']
    else:
        module.fail_json(msg="k5_auth_facts not found, have you run k5_auth?") 
        
    endpoint = k5_facts['endpoints']['networking']
    auth_token = k5_facts['auth_token']
    ports = module.params['ports']
    router_name = module.params['router_name']

   
    # we need the router_id not router_name, so grab it
    router_id = k5_get_router_id_from_name(module, k5_facts)
    if router_id == '':
        if k5_debug:
            module.exit_json(changed=False, msg="Router " + router_name + " not found", debug=k5_debug_out)
        else:
            module.exit_json(changed=False, msg="Router " + router_name + " not found")

    # actually the project_id, but stated as tenant_id in the API
    tenant_id = k5_facts['auth_spec']['os_project_id']
    
    k5_debug_add('auth_token: {0}'.format(auth_token))
    k5_debug_add('router_name: {0}'.format(router_name))

    for port in ports:
        # get port_id from name
        port_id=k5_get_port_id(module,k5_facts,port)

        if port_id != "":

            k5_debug_add('port: {0}'.format(port_id))

            session = requests.Session()

            headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': auth_token }

            url = endpoint + '/v2.0/routers/' + router_id + '/add_router_interface'
          
            query_json = {"port_id": port_id }

            k5_debug_add('endpoint: {0}'.format(endpoint))
            k5_debug_add('REQ: {0}'.format(url))
            k5_debug_add('headers: {0}'.format(headers))
            k5_debug_add('json: {0}'.format(query_json))

            try:
                response = session.request('PUT', url, headers=headers, json=query_json)
            except requests.exceptions.RequestException as e:
                module.fail_json(msg=e)

            if response.status_code == 409:
                module.exit_json(changed=False, msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

            # we failed to make a change
            if response.status_code != 200:
                module.fail_json(msg="RESP: HTTP Code:" + str(response.status_code) + " " + str(response.content), debug=k5_debug_out)

            if k5_debug:
                module.exit_json(changed=True, msg="Router ports Update Successful", k5_router_facts=response.json(), debug=k5_debug_out )


    module.exit_json(changed=True, msg="Router ports Update Successful", k5_router_facts=response.json()['router'])


######################################################################################

def main():

    module = AnsibleModule( argument_spec=dict(
        router_name = dict(required=True, default=None, type='str'),
        state = dict(required=True, type='str'), # should be a choice
        ports = dict(required=True, default=None, type='list'),
        k5_auth = dict(required=True, default=None, type='dict')
    ) )

    if module.params['state'] == 'present':
        k5_update_router_add_ports(module)
    else:
       module.fail_json(msg="No 'absent' function in this module, use os_port module instead") 


######################################################################################

if __name__ == '__main__':  
    main()



