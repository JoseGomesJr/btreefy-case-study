#include "tracker/tracker_bb.h"

#include <string.h>

struct tracker_bb g_tracker_bb = {
    .gnss_status             = GNSS_BUSY,
    .radio_status            = RADIO_BUSY,
    .tamper                  = false,
    .battery_pct             = 100,
    .new_position_requested  = false,
};

void tracker_bb_update(const struct zbus_channel *chan)
{
    if (chan == &chan_gnss_evt)
    {
        const struct gnss_evt *evt = zbus_chan_const_msg(chan);
        g_tracker_bb.gnss_status   = evt->st;
        if (evt->st == GNSS_FIX)
        {
            memcpy(&g_tracker_bb.last_fix, &evt->fix, sizeof(g_tracker_bb.last_fix));
        }
    }
    else if (chan == &chan_radio_evt)
    {
        const struct radio_evt *evt = zbus_chan_const_msg(chan);
        g_tracker_bb.radio_status   = evt->st;
    }
    else if (chan == &chan_sensor_evt)
    {
        const struct sensor_evt *evt = zbus_chan_const_msg(chan);
        g_tracker_bb.tamper          = evt->tamper;
        g_tracker_bb.battery_pct     = evt->battery_pct;
    }
    else if (chan == &chan_request_evt)
    {
        const struct request_evt *evt   = zbus_chan_const_msg(chan);
        g_tracker_bb.new_position_requested = evt->new_position_requested;
    }
}
