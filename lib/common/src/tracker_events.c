#include "tracker/tracker_events.h"

#include <zephyr/zbus/zbus.h>

ZBUS_SUBSCRIBER_DEFINE(sub_policy, 8);

extern void lis_cmd_actuator_cb(const struct zbus_channel *chan);
ZBUS_LISTENER_DEFINE(lis_cmd_actuator, lis_cmd_actuator_cb);

ZBUS_CHAN_DEFINE(chan_gnss_evt, struct gnss_evt, NULL, NULL, ZBUS_OBSERVERS(sub_policy),
                  ZBUS_MSG_INIT(.st = GNSS_BUSY));

ZBUS_CHAN_DEFINE(chan_radio_evt, struct radio_evt, NULL, NULL, ZBUS_OBSERVERS(sub_policy),
                  ZBUS_MSG_INIT(.st = RADIO_BUSY));

ZBUS_CHAN_DEFINE(chan_sensor_evt, struct sensor_evt, NULL, NULL, ZBUS_OBSERVERS(sub_policy),
                  ZBUS_MSG_INIT(0));

ZBUS_CHAN_DEFINE(chan_request_evt, struct request_evt, NULL, NULL, ZBUS_OBSERVERS(sub_policy),
                  ZBUS_MSG_INIT(0));

ZBUS_CHAN_DEFINE(chan_tracker_cmd, struct tracker_cmd, NULL, NULL,
                  ZBUS_OBSERVERS(lis_cmd_actuator), ZBUS_MSG_INIT(.op = CMD_SLEEP));
