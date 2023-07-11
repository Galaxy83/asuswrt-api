import sys
from asuswrt import AsusWRT

router = AsusWRT()
clients = router.get_online_clients()

for client in clients:
    print(client)
    print()
