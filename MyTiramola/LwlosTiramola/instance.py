class Instance:
    """
    Represents an instance.
"id", "networks", "flavor", "image", "security_groups", "status", "key_name", "name", "created"

    :ivar id: The unique ID of the Instance.
    :ivar networks: A list of the instance's interfaces ([ipv4, ipv6, floating]).
    :ivar flavor: The ID of the Flavor used to launch this instance.
    :ivar image: The ID of the AMI used to launch this instance.
    :ivar security_groups: List of security Groups associated with the instance.
    :ivar status: The string representation of the instance's current state.
    :ivar key_name: The name of the SSH key associated with the instance.
    :ivar name: The name of the instance.
    :ivar created: The time the instance was launched.
    """

    def __repr__(self):
        
        return 'Instance:%s' % self.name


    def __init__(self, details):
        
        self.id = details['id']
        self.networks = details['networks']
        self.flavor = details['flavor']
        self.image = details['image']
        self.status = details['status']
        self.key_name = details['key_name']
        self.name = details['name']
        self.created = details['created']
