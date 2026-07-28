#include "tracker/drivers_fake.h"

#include <zephyr/kernel.h>
#include <zephyr/zbus/zbus.h>

#include "tracker/tracker_bb.h"
#include "tracker/tracker_events.h"

static uint8_t g_battery_pct = 100;
static bool    g_tamper      = false;

void fake_gnss_finish(enum gnss_evt_status st, struct gnss_fix fix)
{
    struct gnss_evt evt = {.st = st, .fix = fix};
    zbus_chan_pub(&chan_gnss_evt, &evt, K_NO_WAIT);
}

void fake_radio_finish(enum radio_evt_status st)
{
    struct radio_evt evt = {.st = st};
    zbus_chan_pub(&chan_radio_evt, &evt, K_NO_WAIT);
}

void fake_sensor_set_tamper(bool tamper)
{
    g_tamper              = tamper;
    struct sensor_evt evt = {.tamper = g_tamper, .battery_pct = g_battery_pct};
    zbus_chan_pub(&chan_sensor_evt, &evt, K_NO_WAIT);
}

void fake_sensor_set_battery(uint8_t battery_pct)
{
    g_battery_pct         = battery_pct;
    struct sensor_evt evt = {.tamper = g_tamper, .battery_pct = g_battery_pct};
    zbus_chan_pub(&chan_sensor_evt, &evt, K_NO_WAIT);
}

void fake_request_new_position(bool active)
{
    if (active)
    {
        g_tracker_bb.gnss_status  = GNSS_BUSY;
        g_tracker_bb.radio_status = RADIO_BUSY;
    }

    struct request_evt evt = {.new_position_requested = active};
    zbus_chan_pub(&chan_request_evt, &evt, K_NO_WAIT);
}

void lis_cmd_actuator_cb(const struct zbus_channel *chan)
{
    if (chan != &chan_tracker_cmd)
    {
        return;
    }

    const struct tracker_cmd *cmd = zbus_chan_const_msg(chan);

    if (cmd->op == CMD_LOG_FAIL)
    {
        g_tracker_bb.gnss_status  = GNSS_BUSY;
        g_tracker_bb.radio_status = RADIO_BUSY;
    }
}
