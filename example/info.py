import sys

from asuswrt import AsusWRT

sys.path.append('../')

router = AsusWRT()
sys = router.get_sys_info()

print('Model: %s' % sys['model'])
print('Firmware: %s' % sys['firmware'])
