import sys
from asuswrt import AsusWRT

router = AsusWRT()
clients = router.get_online_clients()

for client in clients:
    for attribute in ['name', 'nickName', 'mac', 'ip', 'interface', 'rssi']:
        print('%s: %s' % (attribute.capitalize(), getattr(client, attribute)))
    print()
