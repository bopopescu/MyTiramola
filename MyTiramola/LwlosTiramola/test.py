
from novaclient import client
from credentials import get_nova_creds

creds = get_nova_creds()
nova = client.Client(1.1, creds.get('username'), creds.get('api_key'),
                     creds.get('project_id'), creds.get('auth_url'))

servers = nova.servers.list()
flavors = nova.flavors.list()

