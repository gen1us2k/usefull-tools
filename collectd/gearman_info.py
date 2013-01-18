import collectd
import gearman

def getQueue():
    gearadmin = gearman.GearmanAdminClient(['localhost:4730'])
    return gearadmin.get_status()[0]['queued']

def dispatch_value(info, key, type, type_instance=None):
  if not type_instance:
    type_instance = key

  value = int(info)
  val = collectd.Values(plugin='gearman_info')
  val.type = type
  val.interval = 600
  val.type_instance = type_instance
  val.values = [value]
  val.dispatch()

def read():
    data = getQueue()
    dispatch_value(getQueue(), 'queue', 'gearman')

collectd.register_read(read)

